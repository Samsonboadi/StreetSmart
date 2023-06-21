""" A simple HTTP server """
import os
import http.server
import socketserver
import argparse

import logging
from logger import Logger  # pylint: disable=import-error
from logger import log  # pylint: disable=import-error

BASE_DIRECTORY = os.path.dirname(os.path.abspath(__file__))

# log_with uses __name__ to fecth a logger, log_with is called when the module
# with the call is imported. Therefore the __name__ must be changed is soon as
# possible.
standalone = False
if __name__ == "__main__":
    # Hack to remove __main__ from logs
    __name__ = os.path.splitext(os.path.basename(__file__))[0]
    standalone = True


class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """ HTTP Request Handler """
    __logger = Logger(__name__).get()

    def do_GET(self):
        if not self.path.startswith(r"/undefined"):
            self.__logger.info("HTTP server asked for: %s", self.path)
            self.__logger.info("Local path: %s", self.translate_path(self.path))
        super(CustomHTTPRequestHandler, self).do_GET()


class local_httpd():
    ''' Runs a http server in a separate thread '''
    __logger = Logger(__name__).get()

    def __init__(self, port=0):
        self.server_port = 0

        self.__logger.info("Start HTTP Server at port %s", port)
        os.chdir(BASE_DIRECTORY)
        handler = CustomHTTPRequestHandler
        try:
            self.httpd = socketserver.TCPServer(("", 0), handler)
        except OSError as e:
            self.__logger.error("Error starting http server %s", e)
            return

        self.server_port = self.httpd.server_address[1]
        self.__logger.info("HTTP Server started at %d", self.server_port)

    @log(message="Serving from current working directory: " + os.getcwd())
    def run(self):
        """ Start the http server """
        if self.server_port != 0:
            self.__logger.info("Serving from current working directory: %s",
                               os.getcwd())
            self.httpd.serve_forever()
        else:
            self.__logger.error("Cannot start HTTP server")

    @log(logging.DEBUG)
    def shutdown(self):
        ''' Shutdown the http server '''
        self.__logger.info("Shutdown the HTTP server")
        self.httpd.shutdown()


def create_argument_parser():
    """ Creates the command line parser """
    parser = argparse.ArgumentParser(description="Start a simple HTTP server")
    parser.add_argument('port_number', type=int,
                        help='port number, is obsolete')
    parser.add_argument('filename',
                        help='file where pid and port number are written to')
    parser.add_argument('log_port_number', type=int,
                        help='port number in use for logging')
    return parser


def parse_arguments():
    """ Returns the command line arguments """
    parser = create_argument_parser()
    return parser.parse_args()


def write_to_file(filename, number, append):
    """ Writes a number to a files """
    mode = "a" if append else "w"
    with open(filename, mode) as f:
        f.write("{}\n".format(number))


@log()
def write_current_process_id(filename):
    """ Writes PID to file """
    write_to_file(filename, os.getpid(), False)


@log()
def write_http_port_number(filename, server):
    """ Writes port number to file """
    write_to_file(filename, server.server_port, True)


if __name__ == "__main__" or standalone:
    args = parse_arguments()

    Logger(__name__, args.log_port_number).get()
    write_current_process_id(args.filename)

    # Start server
    s = local_httpd(args.port_number)

    write_http_port_number(args.filename, s)

    # Run server
    s.run()
