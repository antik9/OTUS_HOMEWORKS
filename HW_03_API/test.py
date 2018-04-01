__author__ = "Illarionov Anton"

import unittest
import random
from api import *
from store import NoSuchElementError
from scoring import create_key_part
from unittest import mock
from functools import partial

# --------------------------- Constants ---------------------------- #

ALPHABET = [chr(ch) for ch in range(ord('!'), ord('z'))]
SOME_INTERESTS = ["football", "soccer", "music", "religion", "books", "relax", "leisure",
                  "nothing", "studying", "online-games", "joking"]

"""
Valid for
----test_right_authorization,
----test_bad_authorization,
----test_forbidden_access,
----test_no_method_in_request,
----test_no_arguments_in_request,
----test_admin_score_is_42,
"""
NUM_OF_AUTO_GENERATED_TEST_CASES = 10
TIME_OF_STORE = 100


# ----------------------- Preload functions ------------------------ #

def cases(cases_):
    """Decorator to make tests in time of initialization"""

    def wrapper(func):
        def inner(*args):
            for case in cases_:
                new_args = args + (case if (isinstance(case, tuple)) else (case,))
                func(*new_args)

        return inner

    return wrapper


def add_method_to_request(func, score_rate=.5):
    """Decorator to add method to request. Thx, cap!"""

    def wrapper(*args, **kwargs):
        request = func(*args, **kwargs)
        request.storage["method"] = "online_score" if random.random() < score_rate \
            else "clients_interests"
        return request

    return wrapper


def add_arguments_to_request(func, is_score=True):
    """Decorator to add method to request. Thx, cap!"""

    def wrapper(*args, **kwargs):
        request = func(*args, **kwargs)
        if is_score:
            request.storage["arguments"] = {
                "first_name": "".join(random.choices(ALPHABET,
                                                     k=random.randint(5, 20))),
                "last_name": "".join(random.choices(ALPHABET,
                                                    k=random.randint(5, 20))),
                "birthday": datetime.date(
                    random.randint(2018 - 60, 2018 - 18),
                    random.randint(1, 12),
                    random.randint(1, 28),
                ).strftime("%d.%m.%Y"),
                "gender": random.randint(1, 3),
            }
        else:
            request.storage["arguments"] = {
                "client_ids": list(range(1, 11)),
            }

        return {"body": request.storage}

    return wrapper


score_prefix = "~test~get~score~:"
interest_prefix = "~test~get~interests~:"
func_test_scoring = partial(get_score, prefix=score_prefix, time_of_store=TIME_OF_STORE)
func_test_interests = partial(get_interests, prefix=interest_prefix)


class AuthRequest:
    """Class to make request with dict"""

    def __init__(self):
        self.storage = {}


def create_auth_request(valid=True, admin_rate=.3):
    """Function to create valid/invalid request"""

    is_admin = random.random() < admin_rate
    request = AuthRequest()
    if is_admin:
        request.storage["login"] = ADMIN_LOGIN
        request.storage["token"] = hashlib.sha512(
            (datetime.datetime.now().strftime("%Y%m%d%H") +
             ADMIN_SALT).encode("utf-8")).hexdigest()
    else:
        request.storage["login"] = "".join(
            random.choices(ALPHABET, k=random.randint(5, 20)))
        request.storage["account"] = "".join(
            random.choices(ALPHABET, k=random.randint(5, 20)))
        request.storage["token"] = hashlib.sha512(
            (request.storage["account"] +
             request.storage["login"] +
             SALT).encode("utf-8")).hexdigest()
    if not valid:
        request.storage["token"] = request.storage["token"][:-1]
    return request


# -------------------- Test class for all fields --------------------- #

class TestFields(unittest.TestCase):
    """Test defined fields of correct interpretation of data pass to them"""

    def test_cannot_instantiate_abstract_field(self):
        try:
            AbstractField()
        except TypeError:
            pass

    """Test CharField class"""

    @cases([
        "this is good",
        "and this is better",
    ])
    def test_right_char_field(self, value):
        self.assertEqual(CharField().validate(value), value)

    @cases([
        90,
        {},
        [],
    ])
    def test_wrong_char_field(self, value):
        with self.assertRaises(DataFieldError):
            CharField().validate(value)

    """Test ArgumentsField class"""

    @cases([
        {"a": "b"},
        {1: 2},
    ])
    def test_right_arguments_field(self, value):
        self.assertEqual(ArgumentsField().validate(value), value)

    @cases([
        90,
        "this is good",
        [],
    ])
    def test_wrong_arguments_field(self, value):
        with self.assertRaises(DataFieldError):
            ArgumentsField().validate(value)

    """Test EmailField class"""

    @cases([
        "imvalid@email.yeah",
        "imveryvalid190.89_123ui@noosdnlwern.fkjsfkjds_jdsnf.ooo",
    ])
    def test_right_email_field(self, value):
        self.assertEqual(EmailField().validate(value), value)

    @cases([
        "too@much@at.oops",
        "really??..hohoho",
        "try-that@bool=true"
    ])
    def test_wrong_email_field(self, value):
        with self.assertRaises(DataFieldError):
            EmailField().validate(value)

    """Test PhoneField class"""

    @cases([
        "71090231092",
        "77777777777",
    ])
    def test_right_phone_field(self, value):
        self.assertEqual(PhoneField().validate(value), value)

    @cases([
        "+78923492389",
        "7849329423",
        "1",
        "abc",
        12
    ])
    def test_wrong_phone_field(self, value):
        with self.assertRaises(DataFieldError):
            PhoneField().validate(value)

    """Test DateField class"""

    @cases([
        "12.11.1000",
        "1.1.2018",
        "9.12.9000"
    ])
    def test_right_date_field(self, value):
        self.assertEqual(DateField().validate(value),
                         datetime.datetime.strptime(value, "%d.%m.%Y"))

    @cases([
        "2000.11.14",
        "11.14.2000",
        "11/05/2000",
        "11072000",
        11072000
    ])
    def test_wrong_date_field(self, value):
        with self.assertRaises(DataFieldError):
            DateField().validate(value)

    """Test BirthDayField class"""

    @cases([
        "12.11.1950",
        "1.1.2017",
        "9.12.1988"
    ])
    def test_right_birthday_field(self, value):
        self.assertEqual(BirthDayField().validate(value),
                         datetime.datetime.strptime(value, "%d.%m.%Y"))

    @cases([
        "2000.11.14",
        "11.14.2000",
        "10.09.1930",
        "10.10.1000",
    ])
    def test_wrong_birthday_field(self, value):
        with self.assertRaises(DataFieldError):
            BirthDayField().validate(value)

    """Test GenderField class"""

    @cases([
        1,
        2,
        3,
    ])
    def test_right_gender_field(self, value):
        self.assertEqual(GenderField().validate(value), value)

    @cases([
        4,
        5,
        -1,
        "a",
    ])
    def test_wrong_gender_field(self, value):
        with self.assertRaises(DataFieldError):
            GenderField().validate(value)

    """Test ClientIDsField class"""

    @cases([
        [1, 2, 3],
        list(range(100)),
    ])
    def test_right_client_ids_field(self, value):
        self.assertEqual(ClientIDsField().validate(value), value)

    @cases([
        3,
        {1: 2},
        ["1", "2", "3"],
        [9, 3, "5"],
    ])
    def test_wrong_client_ids_field(self, value):
        with self.assertRaises(DataFieldError):
            ClientIDsField().validate(value)

    """THE END"""


# ------------------- Test class for all handlers -------------------- #

class TestHandlers(unittest.TestCase):
    """Test class for testing work of handlers"""

    def setUp(self):
        self.context = {}
        self.headers = {}
        self.store = Storage()
        self.backup = {}
        self.fulfill()
        self.key_hash = set()

    def fulfill(self):

        for i in range(1, 11):
            interests = random.sample(SOME_INTERESTS, 2)
            key, value = "%s%d" % (interest_prefix, i), json.dumps(interests)
            self.backup.update({i: value})
            self.store._Storage__setkey(key, value, TIME_OF_STORE)

    def add_key_to_hash_key(self, arguments):
        self.key_hash.add(create_key_part(
            arguments["arguments"].get("first_name"),
            arguments["arguments"].get("last_name"),
            (
                datetime.datetime.strptime(arguments["arguments"].get("birthday"), "%d.%m.%Y")
                if arguments["arguments"].get("birthday")
                else None
            ),
            score_prefix,
        ))

    def test_cannot_instantiate_abstract_class(self):
        try:
            BasicRequest(store=[], arguments=[])
        except TypeError:
            pass

    """Test handler MethodRequest"""

    @cases([
        {"account": "account", "login": "login", "token": "token", "arguments": {}, "method": "method"},
        {"login": "login", "token": "token", "arguments": {}, "method": "method"},
        {"login": "", "token": "", "arguments": {}, "method": "method"},
    ])
    def test_init_method_request(self, arguments):
        MethodRequest([], self.context, arguments)

    @cases([
        (
                # Test that method cannot be null
                {"account": "account", "login": "login", "token": "token", "arguments": {}, "method": ""},
                ['method cannot be null']
        ),
        (
                # Test that request should contain login field
                {"token": "token", "arguments": {}, "method": "method"},
                ["login is required"]
        ),
        (
                # Test that request should contain arguments field and method is not null
                {"login": "", "token": "", "method": ""},
                ["arguments is required", "method cannot be null"]
        ),
    ])
    @mock.patch("api.MethodRequest.raise_error_if_there_are_some")
    def test_bad_init_method_request(self, arguments, errors, _):
        method_request = MethodRequest([], self.context, arguments)
        self.assertListEqual(method_request.errors, errors)

    """Test handler ClientsInterestsRequest"""

    @cases([
        (
                # Test there are no problem with initialization and
                # right number in context["nclients"]
                {"arguments": {"client_ids": [1, 2, 3]}, "method": "method"},
                3,
        ),
        (
                {"arguments": {"client_ids": list(range(1000)), "date": "09.11.2017"}},
                1000,
        ),
        (
                {"login": "", "token": "", "arguments": {"client_ids": [10000]}},
                1,
        )
    ])
    def test_init_clients_interests_request(self, arguments, nclients):
        ClientsInterestsRequest([], self.context, arguments["arguments"])
        self.assertEqual(self.context["nclients"], nclients)

    # Test exception cases (empty list, wrong format)
    @cases([
        {"arguments": {"client_ids": []}, "method": "method"},
        {"arguments": {"client_ids": 10}, "method": "method"},
        {"arguments": {"data": "11.11.2111"}, "method": "method"},
    ])
    def test_exception_init_clients_interests_request(self, arguments):
        with self.assertRaises(TooMuchErrors):
            ClientsInterestsRequest([], self.context, arguments["arguments"])

    @mock.patch("api.get_interests", func_test_interests)
    def test_process_clients_interests_request(self):
        cli_request = ClientsInterestsRequest(self.store, self.context,
                                              {"client_ids": list(range(1, 11))})
        result, code = cli_request.process()
        self.assertEqual(code, OK)
        for key, value in result.items():
            self.assertEqual(self.backup[key], json.dumps(value))

    @mock.patch("api.get_interests", func_test_interests)
    def test_process_clients_interests_request_no_keys(self):
        cli_request = ClientsInterestsRequest(self.store, self.context,
                                              {"client_ids": list(range(12, 21))})

        with self.assertRaises(NoSuchElementError):
            result, _ = cli_request.process()

    """Test handler OnlineScoreRequest"""

    @cases([
        (
                # Test there are no problem with initialization and
                # field case is correct
                {"arguments": {"first_name": "first_name", "last_name": "last_name"}},
                ["first_name", "last_name"],
        ),
        (
                {"arguments": {"first_name": "first_name", "last_name": "last_name", "phone": "79178761213"}},
                ["first_name", "last_name", "phone"],
        ),
        (
                {"arguments": {"email": "a@a.a", "phone": "79178761213"}},
                ["email", "phone"]
        ),
        (
                {"arguments": {"gender": 1, "birthday": "11.09.1987", "email": "a@a.a"}},
                ["gender", "birthday", "email"]
        ),
    ])
    def test_init_online_score_request(self, arguments, has):
        OnlineScoreRequest(self.store, self.context, arguments["arguments"])
        self.assertSetEqual(set(self.context["has"]), set(has))

    @cases([
        (
                # Test there are no sufficient fields to apply score method
                {"arguments": {"first_name": "first_name", "phone": "78923429421"}},
        ),
        (
                {"arguments": {"last_name": "last_name", "phone": "79178761213"}},
        ),
        (
                {"arguments": {"email": "a@a.a", "gender": 2}},
        ),
        (
                {"arguments": {"birthday": "11.09.1987", "email": "a@a.a"}},
        ),
    ])
    def test_bad_init_online_score_request(self, arguments):
        with self.assertRaises(TooLessInformationError):
            OnlineScoreRequest(self.store, self.context, arguments["arguments"])

    @cases([
        (
                # Test correctness of score function
                {"arguments": {"first_name": "first_name", "last_name": "last_name"}},
                .5,
        ),
        (
                {"arguments": {"first_name": "N", "last_name": "A", "phone": "79178761213"}},
                2.,
        ),
        (
                {"arguments": {"email": "a@a.a", "phone": "79178761213"}},
                3.,
        ),
        (
                {"arguments": {"gender": 1, "birthday": "11.09.1987", "email": "a@a.a"}},
                3.,
        ),
    ])
    @mock.patch("api.get_score", func_test_scoring)
    def test_calculate_score_request(self, arguments, score):
        self.add_key_to_hash_key(arguments)
        online_request = OnlineScoreRequest(self.store, self.context, arguments["arguments"])
        self.assertEqual(online_request.process(), ({"score": score}, OK))

    """Test authorization function"""

    @cases([
        create_auth_request() for _ in range(NUM_OF_AUTO_GENERATED_TEST_CASES)
    ])
    def test_right_authorization(self, request):
        self.assertTrue(check_auth(request))

    @cases([
        create_auth_request(valid=False) for _ in range(NUM_OF_AUTO_GENERATED_TEST_CASES)
    ])
    def test_bad_authorization(self, request):
        self.assertFalse(check_auth(request))

    """Test method_handler function which routes handlers"""

    @cases([
        {"body": create_auth_request(valid=False)} for _ in range(NUM_OF_AUTO_GENERATED_TEST_CASES)
    ])
    @mock.patch("api.MethodRequest", lambda _x, _y, body: body)
    def test_forbidden_access(self, request):
        self.assertEqual(method_handler(request, self.context, []),
                         (None, FORBIDDEN))

    @cases([
        {"body": create_auth_request()} for _ in range(NUM_OF_AUTO_GENERATED_TEST_CASES)
    ])
    @mock.patch("api.MethodRequest", lambda _x, _y, body: body)
    def test_no_method_in_request(self, request):
        with self.assertRaises(NoMethodError):
            method_handler(request, self.context, [])

    @cases([
        {"body": add_method_to_request(create_auth_request)(admin_rate=0)}
        for _ in range(NUM_OF_AUTO_GENERATED_TEST_CASES)
    ])
    @mock.patch("api.MethodRequest", lambda _x, _y, body: body)
    def test_no_arguments_in_request(self, request):
        with self.assertRaises(NoArgumentsError):
            method_handler(request, self.context, [])

    @cases([
        {"body": add_method_to_request(create_auth_request, score_rate=1)(admin_rate=1)}
        for _ in range(NUM_OF_AUTO_GENERATED_TEST_CASES)
    ])
    @mock.patch("api.MethodRequest", lambda _x, _y, body: body)
    def test_admin_score_is_42(self, request):
        self.assertEqual(method_handler(request, self.context, []),
                         ({"score": 42}, OK))

    """Functional test to test correctness of interests method request"""

    @mock.patch("api.get_interests", func_test_interests)
    def test_interest_handler_is_correct(self):
        request = add_arguments_to_request(
            add_method_to_request(
                create_auth_request, score_rate=0
            ),
            is_score=False
        )
        response, code = method_handler(request(), self.context, self.store)
        self.assertEqual(code, OK)
        for key, value in response.items():
            self.assertEqual(self.backup[key], json.dumps(value))

    """Functional test to test correctness of online score method request"""

    @mock.patch("api.get_score", func_test_scoring)
    def test_score_handler_is_correct(self):
        request = add_arguments_to_request(
            add_method_to_request(
                create_auth_request, score_rate=1
            ),
            is_score=True
        )(admin_rate=0)

        self.add_key_to_hash_key(request["body"])
        response, code = method_handler(request, self.context, self.store)
        self.assertEqual(code, OK)
        self.assertEqual(response, {"score": 2})

    @cases([
        {"body": {}},
        {"body": {"login": "login"}},
        {"body": {"login": "login", "token": "123"}},
        {"body": {"login": "login", "token": "123", "method": "method"}},
    ])
    def test_empty_or_partial_filled_request(self, request):
        with self.assertRaises(TooMuchErrors):
            method_handler(request, self.context, self.store)

    def tearDown(self):
        self.store.connection.delete_multi(self.key_hash)
        self.store.connection.delete_multi(
            map(lambda key: interest_prefix + str(key), self.backup.keys()))
        self.store.connection.disconnect_all()


# --------------------------- Main --------------------------- #

if __name__ == "__main__":
    loader = unittest.TestLoader()
    unittest.main()
