import unittest
import random
import json
import datetime
import hashlib
from unittest import mock
from functools import partial
from api import \
    ADMIN_SALT, OK, FORBIDDEN, \
    get_score, get_interests, method_handler, check_auth, \
    AbstractField, DateField, ArgumentsField, GenderField, BirthDayField, \
    ClientIDsField, CharField, PhoneField, EmailField, \
    DataFieldError, TooMuchErrors, NoMethodError, NoArgumentsError, TooLessInformationError, \
    MethodRequest, ClientsInterestsRequest, OnlineScoreRequest
from store import Storage, NoSuchElementError
from scoring import create_key_part

# --------------------------- Constants ---------------------------- #

SOME_INTERESTS = ["football", "soccer", "music", "religion", "books", "relax", "leisure",
                  "nothing", "studying", "online-games", "joking"]
POPULAR_INTERESTS = [
    ["web", "net"],
    ["spiders", "tv"],
    ["ball", "china"],
    ["hack", "sleep"]
]
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


score_prefix = "~test~get~score~:"
interest_prefix = "~test~get~interests~:"
func_test_scoring = partial(get_score, prefix=score_prefix, time_of_store=TIME_OF_STORE)
func_test_interests = partial(get_interests, prefix=interest_prefix)


class AuthRequest:
    """Class to make request with dict"""

    def __init__(self):
        self.storage = {}


def create_request(storage):
    """
    Create format of user's request with class AuthRequest
    in place of user's json for tests' cases
    """

    auth_request = AuthRequest()
    auth_request.storage = storage
    return {"body": auth_request}


def get_current_admin_token():
    """Create right admin token to auth admin"""
    return hashlib.sha512(
        (datetime.datetime.now().strftime("%Y%m%d%H") +
         ADMIN_SALT).encode("utf-8")).hexdigest()


# ------------------- Test classes for all fields -------------------- #

class TestAbstractField(unittest.TestCase):
    """Test defined fields of correct interpretation of data pass to them"""

    def test_cannot_instantiate_abstract_field(self):
        with self.assertRaises(TypeError):
            AbstractField()


class TestCharField(unittest.TestCase):
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


class TestArgumentsField(unittest.TestCase):
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


class TestEmailField(unittest.TestCase):
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


class TestPhoneField(unittest.TestCase):
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


class TestDateField(unittest.TestCase):
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


class TestBirthdayField(unittest.TestCase):
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


class TestGenderField(unittest.TestCase):
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


class TestClientIDsField(unittest.TestCase):
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


# ------------------- Test class for all handlers -------------------- #

class TestHandlers(unittest.TestCase):
    """Test class for testing work of handlers"""

    def setUp(self):
        self.context = {}
        self.store = Storage()
        self.backup = {}
        self.fulfill()
        self.key_hash = set()

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

    def fulfill(self):
        for i in range(1, 11):
            interests = random.sample(SOME_INTERESTS, 2)
            key, value = "%s%d" % (interest_prefix, i), json.dumps(interests)
            self.backup.update({i: value})
            self.store._Storage__setkey(key, value, TIME_OF_STORE)

    def tearDown(self):
        self.store.connection.delete_multi(self.key_hash)
        self.store.connection.delete_multi(
            map(lambda key: interest_prefix + str(key), self.backup.keys()))
        self.store.connection.disconnect_all()

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
        self.assertSetEqual(set(method_request.errors), set(errors))

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
        # Right cases
        {'login': 'Peter Parker', 'account': 'Spiderman',
         'token': '4de1853f30330c85fb3dc5fc5b1fb2239981e5e0fe1bcfb7137feee75eb9beeef21a63c4652ba576461d7fb60ec9083a7c3cb35345cdf3c798748bd287d975b2'},

        {'login': 'Mary Jane', 'account': 'TV actress',
         'token': 'dce3e3f520c9294c4ac7fd6e3434be2ed5de97423350f7c509f6321dc6c8a38fa386b1d8a9cbd2f27c6f9c8164e3e11fd369547d988123f31132a69c6e986de7'},

        {'login': 'Yao Ming', 'account': 'Houston Rockets',
         'token': 'f203215d025be91486e287252ff3895ebecd76f1f280faf7d2fee20610fad104dd60975cceadd4b30e40afeea70c0d66cbe5581edc7802674c07bad21c39bb5e'},

        {'login': 'admin', 'account': 'admin',
         'token': get_current_admin_token()},
    ])
    def test_right_authorization(self, storage):
        auth_request = create_request(storage)["body"]
        self.assertTrue(check_auth(auth_request))

    @cases([
        {'login': 'Peter Parker', 'account': 'Hulk',
         'token': '4de1853f30330c85fb3dc5fc5b1fb2239981e5e0fe1bcfb7137feee75eb9beeef21a63c4652ba576461d7fb60ec9083a7c3cb35345cdf3c798748bd287d975b2'},

        {'login': 'Aunt May', 'account': 'TV actress',
         'token': 'dce3e3f520c9294c4ac7fd6e3434be2ed5de97423350f7c509f6321dc6c8a38fa386b1d8a9cbd2f27c6f9c8164e3e11fd369547d988123f31132a69c6e986de7'},

        {'login': 'Yao Ming', 'account': 'Houston Rockets',
         'token': 'YaoMingFromChinaWhoIsVeryTallButCantBeAuthorizedThisTime'},

        {'login': 'admin', 'account': 'admin',
         'token': 'IDontNeedTokenToAuthenticateIHackIt!!'},
    ])
    def test_bad_authorization(self, storage):
        auth_request = create_request(storage)["body"]
        self.assertFalse(check_auth(auth_request))

    """Test method_handler function which routes handlers"""

    @cases([
        {'login': 'Peter Parker', 'account': 'Hulk',
         'token': '4de1853f30330c85fb3dc5fc5b1fb2239981e5e0fe1bcfb7137feee75eb9beeef21a63c4652ba576461d7fb60ec9083a7c3cb35345cdf3c798748bd287d975b2'},

        {'login': 'Aunt May', 'account': 'TV actress',
         'token': 'dce3e3f520c9294c4ac7fd6e3434be2ed5de97423350f7c509f6321dc6c8a38fa386b1d8a9cbd2f27c6f9c8164e3e11fd369547d988123f31132a69c6e986de7'},

        {'login': 'Yao Ming', 'account': 'Houston Rockets',
         'token': 'YaoMingFromChinaWhoIsVeryTallButCantBeAuthorizedThisTime'},

        {'login': 'admin', 'account': 'admin',
         'token': 'IDontNeedTokenToAuthenticateIHackIt!!'},
    ])
    @mock.patch("api.MethodRequest", lambda _x, _y, body: body)
    def test_forbidden_access(self, storage):
        request = create_request(storage)
        self.assertEqual(method_handler(request, self.context, []),
                         (None, FORBIDDEN))

    @cases([
        {'login': 'Peter Parker', 'account': 'Spiderman',
         'token': '4de1853f30330c85fb3dc5fc5b1fb2239981e5e0fe1bcfb7137feee75eb9beeef21a63c4652ba576461d7fb60ec9083a7c3cb35345cdf3c798748bd287d975b2'},

        {'login': 'Mary Jane', 'account': 'TV actress',
         'token': 'dce3e3f520c9294c4ac7fd6e3434be2ed5de97423350f7c509f6321dc6c8a38fa386b1d8a9cbd2f27c6f9c8164e3e11fd369547d988123f31132a69c6e986de7'},

        {'login': 'Yao Ming', 'account': 'Houston Rockets',
         'token': 'f203215d025be91486e287252ff3895ebecd76f1f280faf7d2fee20610fad104dd60975cceadd4b30e40afeea70c0d66cbe5581edc7802674c07bad21c39bb5e'},

        {'login': 'admin', 'account': 'admin',
         'token': get_current_admin_token()},
    ])
    @mock.patch("api.MethodRequest", lambda _x, _y, body: body)
    def test_no_method_in_request(self, storage):
        request = create_request(storage)
        with self.assertRaises(NoMethodError):
            method_handler(request, self.context, [])

    @cases([
        {'login': 'Peter Parker', 'account': 'Spiderman', 'method': 'online_score',
         'token': '4de1853f30330c85fb3dc5fc5b1fb2239981e5e0fe1bcfb7137feee75eb9beeef21a63c4652ba576461d7fb60ec9083a7c3cb35345cdf3c798748bd287d975b2'},

        {'login': 'Mary Jane', 'account': 'TV actress', 'method': 'clients_interests',
         'token': 'dce3e3f520c9294c4ac7fd6e3434be2ed5de97423350f7c509f6321dc6c8a38fa386b1d8a9cbd2f27c6f9c8164e3e11fd369547d988123f31132a69c6e986de7'},

        {'login': 'Yao Ming', 'account': 'Houston Rockets', 'method': 'online_score',
         'token': 'f203215d025be91486e287252ff3895ebecd76f1f280faf7d2fee20610fad104dd60975cceadd4b30e40afeea70c0d66cbe5581edc7802674c07bad21c39bb5e'},

        {'login': 'admin', 'account': 'admin', 'method': 'clients_interests',
         'token': get_current_admin_token()},
    ])
    @mock.patch("api.MethodRequest", lambda _x, _y, body: body)
    def test_no_arguments_in_request(self, storage):
        request = create_request(storage)
        with self.assertRaises(NoArgumentsError):
            method_handler(request, self.context, [])

    """Test partial filled requests, which should cause errors"""

    @cases([
        {"body": {}},
        {"body": {"login": "login"}},
        {"body": {"login": "login", "token": "123"}},
        {"body": {"login": "login", "token": "123", "method": "method"}},
    ])
    def test_empty_or_partial_filled_request(self, request):
        with self.assertRaises(TooMuchErrors):
            method_handler(request, self.context, self.store)

    """END"""


# -------------------- Functional testing class ------------------------ #

class TestFunctionalOfApi(unittest.TestCase):

    def setUp(self):
        self.context = {}
        self.store = Storage()
        self.backup = {}
        self.fulfill()
        self.key_hash = set()

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

    def fulfill(self):
        for i, interests in enumerate(POPULAR_INTERESTS):
            key, value = "%s%d" % (interest_prefix, i), json.dumps(interests)
            self.backup.update({i: value})
            self.store._Storage__setkey(key, value, TIME_OF_STORE)

    def tearDown(self):
        self.store.connection.delete_multi(self.key_hash)
        self.store.connection.delete_multi(
            map(lambda key: interest_prefix + str(key), self.backup.keys()))
        self.store.connection.disconnect_all()

    """Functional test to test correctness of interests method request"""

    @cases([
        (
                {'login': 'Peter Parker', 'account': 'Spiderman', 'method': 'clients_interests',
                 "arguments": {"client_ids": [0, 1, 2, 3]},
                 'token': '4de1853f30330c85fb3dc5fc5b1fb2239981e5e0fe1bcfb7137feee75eb9beeef21a63c4652ba576461d7fb60ec9083a7c3cb35345cdf3c798748bd287d975b2'},
                dict(zip([0, 1, 2, 3], POPULAR_INTERESTS[0:4])),
        ),
        (
                {'login': 'admin', 'account': 'admin', 'method': 'clients_interests',
                 "arguments": {"client_ids": [0, 1, 2]},
                 'token': get_current_admin_token()},
                dict(zip([0, 1, 2], POPULAR_INTERESTS[0:3])),
        ),
    ])
    @mock.patch("api.get_interests", func_test_interests)
    def test_interest_handler_is_correct(self, storage, answers):
        request = {"body": storage}
        response, code = method_handler(request, self.context, self.store)
        self.assertEqual(code, OK)
        for key, value in response.items():
            self.assertEqual(answers[key], value)

    """Functional test to test correctness of online score method request"""

    @cases([
        (
                {'login': 'Peter Parker', 'account': 'Spiderman', 'method': 'online_score',
                 'arguments': {'first_name': 'Peter', 'last_name': 'Parker'},
                 'token': '4de1853f30330c85fb3dc5fc5b1fb2239981e5e0fe1bcfb7137feee75eb9beeef21a63c4652ba576461d7fb60ec9083a7c3cb35345cdf3c798748bd287d975b2'},
                .5,
        ),
        (
                {'login': 'Mary Jane', 'account': 'TV actress', 'method': 'online_score',
                 'arguments': {'first_name': 'Mary', 'last_name': 'Jane', 'gender': 2, 'birthday': '11.10.1965'},
                 'token': 'dce3e3f520c9294c4ac7fd6e3434be2ed5de97423350f7c509f6321dc6c8a38fa386b1d8a9cbd2f27c6f9c8164e3e11fd369547d988123f31132a69c6e986de7'},
                2.,
        ),
        (
                {'login': 'Yao Ming', 'account': 'Houston Rockets', 'method': 'online_score',
                 'arguments': {'height': 225, 'weight': '140', 'email': 'yao@ming.ch', 'phone': '77777777777'},
                 'token': 'f203215d025be91486e287252ff3895ebecd76f1f280faf7d2fee20610fad104dd60975cceadd4b30e40afeea70c0d66cbe5581edc7802674c07bad21c39bb5e'},
                3.,
        ),
        (
                {'login': 'admin', 'account': 'admin', 'method': 'online_score',
                 'arguments': {},
                 'token': get_current_admin_token()},
                42,
        )
    ])
    @mock.patch("api.get_score", func_test_scoring)
    def test_score_handler_is_correct(self, storage, score):
        request = {"body": storage}
        self.add_key_to_hash_key(request["body"])
        response, code = method_handler(request, self.context, self.store)
        self.assertEqual(code, OK)
        self.assertEqual(response, {"score": score})


# --------------------------- Main --------------------------- #

if __name__ == "__main__":
    loader = unittest.TestLoader()
    unittest.main()
