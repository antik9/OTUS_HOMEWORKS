#!/usr/bin/env python
# -*- coding: utf-8 -*-

from abc import abstractmethod, ABCMeta
import json
import datetime
import logging
import hashlib
import uuid
import re
from optparse import OptionParser
from http.server import HTTPServer, BaseHTTPRequestHandler
from scoring import get_interests, get_score
from store import Storage, StorageError, StorageIsDeadError

# -------------------------- Constants --------------------------- #

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
MALE = 1
FEMALE = 2
UNKNOWN = 3
GENDERS = {
    UNKNOWN: "unknown",
    MALE: "male",
    FEMALE: "female",
}

EMAIL_PATTERN = re.compile("^[^@]+@[^@]+\.[^@]+$")
PHONE_PATTERN = re.compile("^7[\d]{10}$")


# ------- Define exception to handle errors and give hints to user ------- #

class UserRequestError(Exception):
    """Basic class of wrong Exceptions"""
    pass


class DataFieldError(UserRequestError):
    pass


class TooMuchErrors(UserRequestError):
    pass


class TooLessInformationError(UserRequestError):
    pass


class NoArgumentsError(UserRequestError):
    pass


class NoMethodError(UserRequestError):
    pass


# ------- Create abstract class for fields which must be validated ------- #

class AbstractField(metaclass=ABCMeta):

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
            raise DataFieldError("The field must be a string")
        return value


class ArgumentsField(AbstractField):

    def validate(self, value):
        if not isinstance(value, dict):
            raise DataFieldError("Arguments must be a dictionary type")
        return value


class EmailField(CharField):

    def validate(self, value):
        if not isinstance(value, str) or \
                not re.match(EMAIL_PATTERN, value):
            raise DataFieldError("The email field is not valid")
        return value


class PhoneField(AbstractField):

    def validate(self, value):
        if not isinstance(value, str) or \
                not re.match(PHONE_PATTERN, value):
            raise DataFieldError("The phone field is not valid")
        return value


class DateField(AbstractField):

    def validate(self, value):
        try:
            value = datetime.datetime.strptime(value, "%d.%m.%Y")
        except (ValueError, TypeError):
            raise DataFieldError("Wrong format of data")
        return value


class BirthDayField(DateField):

    def validate(self, value):
        value = super(BirthDayField, self).validate(value)
        today = datetime.datetime.now()
        if today > datetime.datetime(value.year + 70, value.month, value.day):
            raise DataFieldError("Client can't be older than 70 years")
        return value


class GenderField(AbstractField):

    def validate(self, value):
        if value not in [MALE, FEMALE, UNKNOWN]:
            raise DataFieldError("Gender field must be {}, {} or {}".format(
                MALE, FEMALE, UNKNOWN
            ))
        return value


class ClientIDsField(AbstractField):

    def validate(self, value):
        if not isinstance(value, list):
            raise DataFieldError("Client IDs field must be a list")
        if not all(isinstance(val, int) for val in value):
            raise DataFieldError("All clients IDs must be an integer")
        return value


# ------- Create classes to handle different methods in request ------- #

class BasicRequest(metaclass=ABCMeta):
    """Basic class of handlers"""

    def __init__(self, store, arguments):
        self.store = store
        self.errors = []
        self.not_blanks = []
        self.storage = {}

        for key, obj in self.__class__.__dict__.items():
            if isinstance(obj, AbstractField):
                _stored_value = arguments.get(key)
                if _stored_value:
                    self.not_blanks.append(key)

                # Add all errors during processing to self.errors
                if obj.required and _stored_value is None:
                    self.errors.append("%s is required" % key)

                if key in arguments and not obj.nullable \
                        and not _stored_value:
                    self.errors.append("%s cannot be null" % key)

                _stored_value = self.validate_cls(_stored_value,
                                                  obj, key, arguments)
                self.storage[key] = _stored_value

        self.raise_error_if_there_are_some()

    def raise_error_if_there_are_some(self):
        """Raise errors in case of errors in parsing fields"""
        if self.errors:
            raise TooMuchErrors(", ".join(self.errors))

    def validate_cls(self, _stored_value, obj, key, arguments):
        try:
            _stored_value = obj.validate(_stored_value) \
                if key in arguments else None
        except DataFieldError as ure:
            self.errors.append(ure.args[0])
        except ValueError:
            self.errors.append("Wrong format of %s" % key)
        return _stored_value


class MethodRequest(BasicRequest):
    """Class to validate api request"""

    account = CharField(required=False, nullable=True)
    login = CharField(required=True, nullable=True)
    token = CharField(required=True, nullable=True)
    arguments = ArgumentsField(required=True, nullable=True)
    method = CharField(required=True, nullable=False)

    def __init__(self, store, _, arguments):
        super(MethodRequest, self).__init__(store, arguments)

    @property
    def is_admin(self):
        return self.login == ADMIN_LOGIN


class ClientsInterestsRequest(BasicRequest):
    """Class to handle request with clients interests method."""
    client_ids = ClientIDsField(required=True)
    date = DateField(required=False, nullable=True)

    def __init__(self, store, ctx, arguments):
        super(ClientsInterestsRequest, self).__init__(store, arguments)
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
        super(OnlineScoreRequest, self).__init__(store, arguments)

        ctx["has"] = self.not_blanks

        # Necessary fields. One of pair should be fulfilled with data
        necessary_data = [
            ("phone", "email"),
            ("first_name", "last_name"),
            ("birthday", "gender"),
        ]

        for field_one, field_two in necessary_data:
            if self.storage[field_one] and self.storage[field_two]:
                break
        else:
            raise TooLessInformationError("In request should be phone and email or "
                                          "first name and last name or "
                                          "birthday date and gender")

    def process(self):
        return {"score": get_score(self.store, **self.storage)}, OK


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
    arguments = request_handled.storage.get("arguments")
    handler = handlers.get(request_handled.storage.get("method"))
    if not check_auth(request_handled):
        return None, FORBIDDEN

    if handler is OnlineScoreRequest and \
            request_handled.storage["login"] == "admin":
        return {"score": 42}, OK

    if handler:
        if not arguments:
            raise NoArgumentsError("There are no arguments in request")
        return handler(store, ctx, arguments).process()
    else:
        raise NoMethodError("There is no method in request")


# Create class to handle HTTP requests and pass it to high-order handlers #

class MainHTTPHandler(BaseHTTPRequestHandler):
    router = {
        "method": method_handler
    }
    store = Storage()

    def get_request_id(self, headers):
        return headers.get('HTTP_X_REQUEST_ID', uuid.uuid4().hex)

    def process_request_(self, request, response, data_string, context):
        """Process user's request, return response and code of response"""

        path = self.path.strip("/")
        logging.info("%s: %s %s" % (self.path, data_string, context["request_id"]))

        if path in self.router:
            try:
                response, code = self.router[path]({"body": request, "headers": self.headers},
                                                   context, self.store)
            except (UserRequestError, StorageError) as e:
                if isinstance(e, StorageIsDeadError):
                    response, code = e.args[0], INTERNAL_ERROR
                else:
                    response, code = e.args[0], INVALID_REQUEST
            except Exception as e:
                logging.exception("Unexpected error: %s" % e)
                code = INTERNAL_ERROR
        else:
            code = NOT_FOUND

        return response, code

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
            response, code = self.process_request_(request, response,
                                                   data_string, context)

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
    op.add_option("-m", "--memcached", action="store", type=int, default=11211)
    op.add_option("-l", "--log", action="store", default=None)
    (opts, args) = op.parse_args()
    logging.basicConfig(filename=opts.log, level=logging.INFO,
                        format='[%(asctime)s] %(levelname).1s %(message)s',
                        datefmt='%Y.%m.%d %H:%M:%S')
    setattr(MainHTTPHandler, "store", Storage(port=opts.memcached))
    server = HTTPServer(("localhost", opts.port), MainHTTPHandler)
    logging.info("Starting server at %s" % opts.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()
