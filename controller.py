""" Start logging machinery """
import json
import socketserver
import time
import threading

from .utils import start_python_script

DETACHED_PROCESS = 0x00000008
SERVER_RETRY_COUNT = 10
SERVER_TIMEOUT = 2
HOST = 'localhost'


class ThreadedTCPServer(socketserver.ThreadingTCPServer):
    ''' Multi-threaded TCP server '''
    def __init__(self, server_address, RequestHandlerClass,
                 bind_and_activate=True):
        socketserver.ThreadingTCPServer.__init__(self, server_address,
                                                 RequestHandlerClass,
                                                 bind_and_activate)
        self.child_process_id = None
        self.child_port_number = None
        self._request_handler_class = RequestHandlerClass


class RequestHandler(socketserver.StreamRequestHandler):
    ''' Handles command '''

    def __init__(self, request, client_address, tcp_server):
        super().__init__(request, client_address, tcp_server)
        self.server = tcp_server

    def handle(self):
        """ Saves the log port and the server pid

        """
        data = self.rfile.readline().strip().decode()
        data = json.loads(data)
        self.server.child_port_number = data["port"]
        self.server.child_process_id = data["pid"]


def bind_info_server():
    """Starts info server

    A port is requested at the OS
    """
    return ThreadedTCPServer((HOST, 0), RequestHandler)


class WaitFor(threading.Thread):
    def __init__(self, log_server):
        super().__init__()
        self.log_server = log_server
        self.return_value = None

    def run(self):
        self.log_server.timeout = SERVER_TIMEOUT
        child_process_id = None
        child_port_number = None

        for _ in range(SERVER_RETRY_COUNT):
            print("Wait for log server to start")
            self.log_server.handle_request()
            if (self.log_server.child_process_id is not None
                    and self.log_server.child_port_number is not None):
                child_process_id = self.log_server.child_process_id
                child_port_number = self.log_server.child_port_number
                print("Found numbers")
                break

        self.return_value = (child_process_id, child_port_number)
        return (child_process_id, child_port_number)


def wait_for_log_server(log_server):
    """ Wait for server to return port and process

    Server runs in a new process
    """
    log_server.timeout = SERVER_TIMEOUT
    child_process_id = None
    child_port_number = None

    for _ in range(SERVER_RETRY_COUNT):
        print("Wait for log server to start")
        log_server.handle_request()
        if (log_server.child_process_id is not None
                and log_server.child_port_number is not None):
            child_process_id = log_server.child_process_id
            child_port_number = log_server.child_port_number
            print("Found numbers")
            break

    return (child_process_id, child_port_number)


def start_process(filename, args=None):
    """ start a process """
    return start_python_script(filename, args, True, False)


def start_log_server(info_port):
    """ Start the log server """
    print("Start log server with info port ", info_port)
    proc = start_process("listener_log.py", [str(info_port)])
    print("Log server started", proc)


def start_children(log_port, count):
    """ Start a number of child processes which will log to the server """
    return_value = []
    for _ in range(count):
        return_value.append(start_process("sender.py", [str(log_port)]))
    return return_value


def initialize_servers():
    """ Init"""
    print("Bind server")
    info_server = bind_info_server()
    print(info_server.server_address)
    info_server_port = info_server.server_address[1]
    start_log_server(info_server_port)
    log_pid, server_log_port = wait_for_log_server(info_server)
    return (log_pid, server_log_port)


if __name__ == '__main__':
    LOG_PID, SERVER_LOG_PORT = initialize_servers()

    # Start several child loggers
    CHILD_LOGGERS = start_children(SERVER_LOG_PORT, 3)

    # Wait till child loggers are closed
    while len(CHILD_LOGGERS) > 0:
        for child in CHILD_LOGGERS[:]:
            if child.poll() is not None:
                CHILD_LOGGERS.remove(child)
        time.sleep(1)
