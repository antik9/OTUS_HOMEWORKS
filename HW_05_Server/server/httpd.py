import datetime
import logging
import os
import re
import socket

from optparse import OptionParser
from socket import SO_REUSEADDR, SOL_SOCKET
from threading import Thread

# -------------------------- Constants --------------------------- #

OK = 200
BAD_REQUEST = 400
FORBIDDEN = 403
NOT_FOUND = 404
METHOD_NOT_ALLOWED = 405

CODE_SPECIFICATION = {
    BAD_REQUEST: "Bad Request",
    FORBIDDEN: "Forbidden",
    OK: "OK",
    NOT_FOUND: "Not Found",
    METHOD_NOT_ALLOWED: "Method Not Allowed",
}

HTTP_VERSION = "HTTP/1.1"
CHUNK_SIZE = 4096

PATTERN_END_OF_REQUEST = b'(.|\s)*(\r\n\r\n|\n\n)'
END_OF_REQUEST = '\r\n\r\n'

DOCUMENT_ROOT = "/httptest"

MIME_TYPES = {
    ".html": "text/html",
    ".css": "text/css",
    ".js": "application/javascript",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".swf": "application/x-shockwave-flash",
    ".txt": "text/plain",
}

ESCAPED_CHARACTERS = {
    '%20': ' ',
    '%09': '\t',
    '%0A': '\n',
    '%0D': '\r',
    '%08': '\b',
}

ESCAPE_PATTERN = r'%\w{2}'


# ------------ Function to update ESCAPED_CHARACTERS ------------- #


def update_escaped_chars(filename):
    try:
        with open(filename, "r") as url_chars_file:
            for line in url_chars_file:
                character, chr_code = line.split()
                ESCAPED_CHARACTERS.update({chr_code: character})
    except IOError:
        pass


# ------------------------ Server class -------------------------- #

class GetAndHeadServer:

    def __init__(self, sock_, basedir_=None):

        # initialize inner parameters
        self.valid_requests = {
            "GET": self.do_GET,
            "HEAD": self.do_HEAD
        }
        self.socket_ = sock_
        self.basedir = basedir_
        self.serve_forever()

    def do_method(self, address, method, repeated=False):
        """
        :param address: real_address of file
        :param method: GET or HEAD
        :param repeated: if request target is a directory, try to
        find index.html in it with parameter repeated=True
        :return: return response with headers and file
        """
        try:
            with open(address, 'rb') as content:
                return self.return_response(OK, content.read(),
                                            self.parse_type(address),
                                            method)
        except FileNotFoundError:
            if repeated:
                raise FileNotFoundError
            return self.return_response(NOT_FOUND)
        except IsADirectoryError:
            try:
                return self.do_method(address + "/index.html", method,
                                      repeated=True)
            except FileNotFoundError:
                return self.return_response(FORBIDDEN)

        except NotADirectoryError:
            return self.return_response(NOT_FOUND)

    def do_GET(self, address):
        return self.do_method(address, "GET")

    def do_HEAD(self, address):
        return self.do_method(address, "HEAD")

    def handle_request(self, data):
        """
        :param data: request in bytes format
        :return: response in bytes format
        """

        logging.info(" - ".join(data.decode("utf-8").split("\r\n")))

        try:
            req_type, address, *_ = data.decode("utf-8").split()
        except ValueError:
            return self.return_response(BAD_REQUEST)

        real_address = self.validate_address(address.lstrip("/"))
        if not real_address:
            return self.return_response(FORBIDDEN)

        method = self.valid_requests.get(req_type.strip())

        if not method:
            return self.return_response(METHOD_NOT_ALLOWED)

        return method(real_address)

    @staticmethod
    def get_current_date():
        """
        :return: formatted date for response
        """
        now = datetime.datetime.utcnow()
        return now.strftime("%a, %d %b %Y %X GMT")

    @staticmethod
    def parse_type(address):
        """
        :param address: http address
        :return: mime type of required file
        """
        for mime_type in MIME_TYPES:
            if address.endswith(mime_type):
                return MIME_TYPES[mime_type]
        return "text/html"

    def return_response(self, code, content=None,
                        content_type=None,
                        type_of_request="GET"):
        """
        :param code: HTTP code
        :param content_type: content type of page or file
        :param content: page or file to return
        :param type_of_request: GET or HEAD
        :return: byte array with valid response
        """
        response = "{} {} {}\r\n".format(HTTP_VERSION, code,
                                         CODE_SPECIFICATION[code])
        response += "Date: {}\r\n".format(self.get_current_date())
        response += "Server: {}\r\n".format(self.__class__.__name__)
        response += "Connection: Close\r\n"

        if code == OK:
            response += "Content-Length: {}\r\n".format(len(content))
            response += "Content-Type: {}{}".format(content_type,
                                                    END_OF_REQUEST)
        logging.info(" - ".join(response.split("\r\n")))
        response = response.encode("utf-8")

        if code == OK and type_of_request == "GET":
            response += content

        return response

    def validate_address(self, address):
        """
        Method to prevent path traversal
        :param address: address in request
        :return: valid address if there is one
        """
        real_address = os.path.realpath(address)
        if real_address.startswith(self.basedir):
            if '?' in address:
                return address[:address.find('?')]

            # Replace escaped characters
            percent_chars = re.findall(ESCAPE_PATTERN, address)
            for percent_char in percent_chars:
                address = address.replace(percent_char,
                                          ESCAPED_CHARACTERS[percent_char.upper()])

            return address

    def serve_forever(self):
        """Function to start server until it will be manually closed"""
        while True:
            try:
                conn, address = self.socket_.accept()

                data = b""
                while True:
                    new_data = conn.recv(CHUNK_SIZE)
                    data += new_data
                    if not new_data \
                            or re.match(PATTERN_END_OF_REQUEST, new_data):
                        break

                response = self.handle_request(data)

                conn.send(response)
                conn.close()

            except Exception as e:
                raise e


# ---------------------------- Main ----------------------------- #

if __name__ == "__main__":
    # Start socket and configure its options

    # Options from command line
    op = OptionParser()
    op.add_option("-l", "--log", action="store", default=None)
    op.add_option("-p", "--port", action="store", type=int, default=8000)
    op.add_option("-w", "--workers", action="store", type=int, default=2)
    op.add_option("-r", "--root_dir", action="store", default=DOCUMENT_ROOT)
    (opts, args) = op.parse_args()

    # Logging
    logging.basicConfig(filename=opts.log, level=logging.INFO,
                        format='[%(asctime)s] %(levelname).1s %(message)s',
                        datefmt='%Y.%m.%d %H:%M:%S')

    # Socket
    sock = socket.socket()
    sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    basedir = os.path.realpath(".") + opts.root_dir
    sock.bind(('', opts.port))
    sock.listen(1024)

    # Add escaped characters fom file url_encode_characters
    update_escaped_chars("url_encode_characters")

    # Threads
    for i in range(opts.workers):
        thread = Thread(target=GetAndHeadServer, args=(sock, basedir))
        thread.start()
