#!/usr/bin/env python
# -*- coding: utf-8 -*-


from abc import abstractmethod
import json
import datetime
import logging
import hashlib
import uuid
import re
from dateutil.relativedelta import relativedelta
from optparse import OptionParser
from http.server import HTTPServer, BaseHTTPRequestHandler
from scoring import get_interests, get_score

SALT = "Otus"
ADMIN_LOGIN = "admin"
ADMIN_SALT = "42"
OK = 200
BAD_REQUEST = 400
FORBIDDEN = 403
NOT_FOUND = 404
INVALID_REQUEST = 422
INTERNAL_ERROR = 500
ERRORS = {
    BAD_REQUEST: "Bad Request",
    FORBIDDEN: "Forbidden",
    NOT_FOUND: "Not Found",
    INVALID_REQUEST: "Invalid Request",
    INTERNAL_ERROR: "Internal Server Error",
}
UNKNOWN = 0
MALE = 1
FEMALE = 2
GENDERS = {
    UNKNOWN: "unknown",
    MALE: "male",
    FEMALE: "female",
}

EMAIL_PATTERN = re.compile("^[^@]+@[^@]+\.[^@]+$")
PHONE_PATTERN = re.compile("^7[\d]{10}$")


# ------- Define exception to handle errors and give hints to user ------- #

class UserRequestError(Exception):
    pass


# ------- Create abstract class for fields which must be validated ------- #

class AbstractField:

    def __init__(self, required=False, nullable=False):
        self.required = required
        self.nullable = nullable

    @abstractmethod
    def validate(self, value):
        """Validate field value, is it correct or not"""


# ------------ Inherit all fields classes from AbstractField -------------- #

class CharField(AbstractField):

    def validate(self, value):
        if not isinstance(value, str):
            raise UserRequestError("The field must be a string")
        return value


class ArgumentsField(AbstractField):

    def validate(self, value):
        if not isinstance(value, dict):
            raise UserRequestError("Arguments must be a dictionary type")
        return value


class EmailField(CharField):

    def validate(self, value):
        if not re.match(EMAIL_PATTERN, value):
            raise UserRequestError("The email field is not valid")
        return value


class PhoneField(AbstractField):

    def validate(self, value):
        if not re.match(PHONE_PATTERN, value):
            raise UserRequestError("The phone field is not valid")
        return value


class DateField(AbstractField):

    def validate(self, value):
        try:
            value = datetime.datetime.strptime(value, "%Y.%m.%d")
        except UserRequestError:
            raise UserRequestError("Wrong format of data")
        return value


class BirthDayField(DateField):

    def validate(self, value):
        value = super(BirthDayField, self).validate(value)
        today = datetime.datetime.now()
        if today - relativedelta(years=70) > value:
            raise UserRequestError("Client can't be older than 70 years")
        return value


class GenderField(AbstractField):

    def validate(self, value):
        if value not in [MALE, FEMALE, UNKNOWN]:
            raise UserRequestError("Gender field must be {}, {} or {}".format(
                MALE, FEMALE, UNKNOWN
            ))
        return value


class ClientIDsField(AbstractField):

    def validate(self, value):
        if not isinstance(value, list):
            raise UserRequestError("Client IDs field must be a list")
        if not all(isinstance(val, int) for val in value):
            raise UserRequestError("All clients IDs must be an integer")
        return value


# ------- Create classes to handle different methods in request ------- #

class BasicRequest:
    """Basic class of handlers"""

    def __init__(self, cls, store, arguments):
        self.store = store
        self.errors = []
        self.blanks = 0
        self.storage = {}

        for key, value in cls.__dict__.items():
            if isinstance(value, AbstractField):
                _stored_value = arguments.get(key)
                self.blanks += _stored_value is None

                # Add all errors during processing to self.errors
                if value.required and _stored_value is None:
                    self.errors.append("%s is required" % key)
                if key in arguments and _stored_value is None:
                    self.errors.append("%s cannot be null" % key)
                try:
                    _stored_value = value.validate(_stored_value) \
                        if key in arguments else None
                except UserRequestError as ure:
                    self.errors.append(ure.args[0])
                except ValueError:
                    self.errors.append("Wrong format of %s" % key)

                self.storage[key] = _stored_value

        if self.errors:
            raise UserRequestError(", ".join(self.errors))


class ClientsInterestsRequest(BasicRequest):
    """Class to handle request with clients interests method."""
    client_ids = ClientIDsField(required=True)
    date = DateField(required=False, nullable=True)

    def __init__(self, store, ctx, arguments):
        super(ClientsInterestsRequest, self).__init__(ClientsInterestsRequest,
                                                      store,
                                                      arguments)
        ctx["nclients"] = 0
        if not self.storage["client_ids"]:
            raise UserRequestError("There are no clients ids to get their interests")
        ctx["nclients"] = len(self.storage["client_ids"])

    def process(self):
        """Function returns clients interests and http code OK"""
        clients_interests = {}
        for id_value in self.storage["client_ids"]:
            clients_interests.update({
                id_value: get_interests(self.store, id_value)
            })
        return clients_interests, OK


class OnlineScoreRequest(BasicRequest):
    """Class to handle request with clients score method"""
    first_name = CharField(required=False, nullable=True)
    last_name = CharField(required=False, nullable=True)
    email = EmailField(required=False, nullable=True)
    phone = PhoneField(required=False, nullable=True)
    birthday = BirthDayField(required=False, nullable=True)
    gender = GenderField(required=False, nullable=True)

    def __init__(self, store, ctx, arguments):
        super(OnlineScoreRequest, self).__init__(OnlineScoreRequest,
                                                 store,
                                                 arguments)

        ctx["has"] = 6 - self.blanks
        if not (self.storage["phone"] is not None and
                self.storage["email"] is not None or
                self.storage["first_name"] is not None and
                self.storage["last_name"] is not None or
                self.storage["birthday"] is not None and
                self.storage["gender"] is not None):
            raise UserRequestError("In request should be phone and email or "
                                   "first name and last name or "
                                   "birthday date and gender")

    def process(self):
        return {"score": get_score(self.store, **self.storage)}, OK


class MethodRequest(BasicRequest):
    """Class to validate api request"""

    account = CharField(required=False, nullable=True)
    login = CharField(required=True, nullable=True)
    token = CharField(required=True, nullable=True)
    arguments = ArgumentsField(required=True, nullable=True)
    method = CharField(required=True, nullable=False)

    def __init__(self, store, _, arguments):
        super(MethodRequest, self).__init__(MethodRequest,
                                            store,
                                            arguments)

    @property
    def is_admin(self):
        return self.login == ADMIN_LOGIN


# ------- Functions of api (authorization and handling) ------- #

def check_auth(request):
    """Authorization function"""

    if request.storage["login"] == ADMIN_LOGIN:
        digest = hashlib.sha512((datetime.datetime.now().strftime("%Y%m%d%H") +
                                 ADMIN_SALT).encode("utf-8")).hexdigest()
    else:
        digest = hashlib.sha512((request.storage["account"] +
                                 request.storage["login"] +
                                 SALT).encode("utf-8")).hexdigest()

    if digest == request.storage["token"]:
        return True
    return False


def method_handler(request, ctx, store):
    """Function to handle request and pass it arguments to appropriate Class"""

    handlers = {
        "clients_interests": ClientsInterestsRequest,
        "online_score": OnlineScoreRequest
    }

    request_handled = MethodRequest(store, ctx, request.get("body"))
    arguments = request_handled.storage["arguments"]
    handler = handlers.get(request_handled.storage["method"])
    if not check_auth(request_handled):
        return None, FORBIDDEN

    if handler is OnlineScoreRequest and \
            request_handled.storage["login"] == "admin":
        return {"score": 42}, OK

    if handler:
        if not arguments:
            raise UserRequestError("There are no arguments in request")
        return handler(store, ctx, arguments).process()
    else:
        raise UserRequestError("There is no method in request")


# Create class to handle HTTP requests and pass it to high-order handlers #

class MainHTTPHandler(BaseHTTPRequestHandler):
    router = {
        "method": method_handler
    }
    store = None

    def get_request_id(self, headers):
        return headers.get('HTTP_X_REQUEST_ID', uuid.uuid4().hex)

    def do_POST(self):
        """Only posts requests allowed"""

        response, code = {}, OK
        context = {"request_id": self.get_request_id(self.headers)}
        request = None
        try:
            data_string = self.rfile.read(int(self.headers['Content-Length']))
            request = json.loads(data_string)
        except Exception as e:
            code = BAD_REQUEST

        if request:
            path = self.path.strip("/")
            logging.info("%s: %s %s" % (self.path, data_string, context["request_id"]))
            if path in self.router:
                try:
                    response, code = self.router[path]({"body": request, "headers": self.headers},
                                                       context, self.store)
                except UserRequestError as e:
                    response, code = e.args[0], INVALID_REQUEST
                except Exception as e:
                    logging.exception("Unexpected error: %s" % e)
                    code = INTERNAL_ERROR
            else:
                code = NOT_FOUND

        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        if code not in ERRORS:
            r = {"response": response, "code": code}
        else:
            r = {"error": response or ERRORS.get(code, "Unknown Error"), "code": code}
        context.update(r)
        logging.info(context)
        self.wfile.write(json.dumps(r).encode("utf-8"))
        return


# -------------------------- main ------------------------- #

if __name__ == "__main__":
    op = OptionParser()
    op.add_option("-p", "--port", action="store", type=int, default=8080)
    op.add_option("-l", "--log", action="store", default=None)
    (opts, args) = op.parse_args()
    logging.basicConfig(filename=opts.log, level=logging.INFO,
                        format='[%(asctime)s] %(levelname).1s %(message)s', datefmt='%Y.%m.%d %H:%M:%S')
    server = HTTPServer(("localhost", opts.port), MainHTTPHandler)
    logging.info("Starting server at %s" % opts.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()
