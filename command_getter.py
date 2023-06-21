""" Module handles commands """
import socketserver
import time
import logging
from threading import Thread

if __package__.strip() == "":
    from logger import log  # pylint: disable=import-error
    from settings import Settings  # pylint: disable=import-error
else:
    from .logger import log
    from .settings import Settings

inner_queue = None
HOST = "localhost"
received = None


class ThreadedTCPServer(socketserver.ThreadingMixIn,
                        socketserver.TCPServer):
    """ Multi-threaded TCP server """
    def __init__(self, server_address, RequestHandlerClass,
                 bind_and_activate=True):
        self.halted = False
        socketserver.TCPServer.__init__(self, server_address,
                                        RequestHandlerClass, bind_and_activate)

    @log(logging.ERROR, print_args=True)
    def handle_error(self, request, client_address):
        pass

    @log(logging.ERROR)
    def handle_timeout(self):
        pass

    def set_halted(self):
        """ Set server status """
        self.halted = True

    def is_halted(self):
        """ Gets the server status """
        return self.halted


class CommandHandler(socketserver.StreamRequestHandler):
    """Class handles a command"""

    @staticmethod
    @log(logging.DEBUG, print_args=True, print_return=True)
    def __create_command_from_input(data):
        """Create a command from the received data."""
        line = data.split('|')

        if len(line) > 1:
            return_value = (line[0], line[1])
        else:
            return_value = (line[0], None)

        return return_value

    def handle(self):
        """ Handles command """
        global received

        data = self.rfile.readline().strip().decode().replace(r"\/", "__")
        inner_queue.put(self.__create_command_from_input(data))

        received = data


class CommandGetter(Thread):
    """ Handles """
    @staticmethod
    @log(print_args=True, print_return=True)
    def __start_server(port):
        """Start"""
        server = ThreadedTCPServer((HOST, port), CommandHandler)
        return (server, server.server_address)

    def __init__(self, message_queue, port=0):
        """ Init with queue and port """
        Thread.__init__(self)
        global inner_queue
        inner_queue = message_queue
        self.server, self.server_address = self.__start_server(port)
        self.port = self.server_address[1]
        self.fetch_interval = Settings.getInstance().get_timer_interval()

    @log(logging.DEBUG)
    def run(self):
        """ Start listing for commands """
        server_thread = Thread(target=self.server.serve_forever)
        server_thread.daemon = True
        server_thread.start()
        fetch_interval = self.fetch_interval
        while (server_thread.is_alive and self.server is not None
               and not self.server.is_halted()):
            time.sleep(fetch_interval)
            global received  # pylint: disable=global-statement
            if received == "stop":
                received = None
                self.shutdown()
                break

    def shutdown(self):
        """Shuts the server down

        Do not log this method. Viewer freezes when logged."""
        if self.server is not None:
            self.server.set_halted()
        self.server.shutdown()
        self.server.server_close()


if __name__ == "__main__":
    import queue
    getter = CommandGetter(9999, queue.Queue())
    getter.start()

    getter.join()
