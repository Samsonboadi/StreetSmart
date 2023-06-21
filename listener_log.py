""" Listener process """
import json
import logging
import logging.config
import logging.handlers
import os
import pickle
import select
import socket
import socketserver
import struct
import sys
import tempfile
import traceback

tempdir = tempfile.gettempdir()
log_file = os.path.join(tempdir, 'streetsmart.log')
debug_log_file = os.path.join(tempdir, 'streetsmart_debug.log')
listener_log = os.path.join(tempdir, r"listener_error.log")


class LogRecordStreamHandler(socketserver.StreamRequestHandler):
    """Handles streaming logging requests"""

    def handle(self):
        """Handles"""
        while True:
            chunck = self.connection.recv(4)
            if len(chunck) < 4:
                break

            slen = struct.unpack('>L', chunck)[0]
            chunck = self.connection.recv(slen)
            while len(chunck) < slen:
                chunck = chunck + self.connection.recv(slen - len(chunck))
            obj = self.unpickle(chunck)
            record = logging.makeLogRecord(obj)
            self.handle_log_record(record)

    @staticmethod
    def unpickle(data):
        """ unpickle """
        return pickle.loads(data)

    def handle_log_record(self, record):
        """ log """
        if self.server.logname is not None:
            name = self.server.logname
        else:
            name = record.name
        logger = logging.getLogger(name)
        logger.handle(record)


class LogRecordSocketReceiver(socketserver.ThreadingTCPServer):
    """ Simple TCP receiver """

    def __init__(self, host='localhost',
                 port=logging.handlers.DEFAULT_TCP_LOGGING_PORT,
                 handler=LogRecordStreamHandler):
        socketserver.ThreadingTCPServer.__init__(self, (host, port), handler)
        self.abort = 0
        self.timeout = 1
        self.logname = None

    def serve_until_stopped(self):
        """ Serve """
        abort = 0
        while not abort:
            rd, wr, ex = select.select([self.socket.fileno()],
                                       [], [], self.timeout)
            if rd:
                self.handle_request()
            abort = self.abort


def send_message(message, server_port):
    """ send a message """
    host = 'localhost'
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((host, server_port))
        sock.sendall(bytes(message + "\n", " utf-8"))


def send_numbers(server_port=0, logger_port=9357, pid=0, send=send_message):
    """ Sends pid and receiver port number to controller """
    msg = {"pid": pid, "port": logger_port}
    msg = json.dumps(msg)
    send(msg, server_port)


def main(sender_port=9357,
         logger_port=logging.handlers.DEFAULT_TCP_LOGGING_PORT):
    """ Main entry point """
#    logging.basicConfig(
#        format=('%(relativeCreated)5d %(process)6d %(filename)s %(funcName)s'
#                ' %(module)s %(name)-15s %(levelname)-8s %(message)s')
#    )
    log_config_dict = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'default': {
                'format': '%(asctime)s %(process)6d %(levelname)-8s %(name)-15s %(message)s'
            },
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': 'DEBUG',
                'formatter': 'default',
                'stream': 'ext://sys.stdout',
            },
            'file': {
                'class': 'logging.FileHandler',
                'level': 'DEBUG',
                'formatter': 'default',
                'filename': debug_log_file,
                'mode': 'w',
                'encoding': 'utf-8',
            },
            'flow': {
                'class': 'logging.FileHandler',
                'level': 'INFO',
                'formatter': 'default',
                'filename': log_file,
                'mode': 'w',
                'encoding': 'utf-8',
            },
        },
        'root': {
            'handlers': ['file', 'flow'],
            # 'handlers': ['flow'],
            'level': 'DEBUG',
        },
    }
    logging.config.dictConfig(log_config_dict)
    tcpserver = LogRecordSocketReceiver(port=logger_port)
    pid = os.getpid()
    send_numbers(server_port=sender_port,
                 logger_port=tcpserver.server_address[1], pid=pid)

    print('About to start TCP server...')
    tcpserver.serve_until_stopped()


if __name__ == '__main__':
    try:
        SERVER_PORT = int(sys.argv[1])
        main(sender_port=SERVER_PORT, logger_port=0)
    except Exception as e:
        tb = traceback.format_exc()
        print("Probleem")
        print(e)
        print(tb)

        with open(listener_log) as flog:
            flog.write("problem with log\n")
            flog.write(str(e) + "\n")
            flog.write(tb)
        print("Logged it")
