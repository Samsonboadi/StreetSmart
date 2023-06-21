"""Shows the CEF browser with a Panorama viewer.

This module contains the functionality to display an browser window with a view
to the street smart imagery. It is intended to work together with the qgis
plugin but can also work standalone (although with less functionality).

This module defines the following interface:

    - a PanoramaViewer class

"""
#  pylint: disable=c-extension-no-member
import argparse
import logging
import os
import platform
import queue
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
from typing import Tuple

from cefpython3 import cefpython as cef

from logger import Logger  # pylint: disable=import-error
from logger import log  # pylint: disable=import-error

from command_getter import CommandGetter  # pylint: disable=import-error
from command_handler import CommandHandler  # pylint: disable=import-error

# log_with uses __name__ to fetch a logger, log_with is called when the module
# with the call is imported. Therefore the __name__ must be changed is soon as
# possible.
standalone = False
if __name__ == "__main__":
    # Hack to remove __main__ from logs
    __name__ = os.path.splitext(os.path.basename(__file__))[0]
    standalone = True


# constants
_DEBUG_CEF = True
_HOST = "localhost"
_INDEX_URI = "panorama_viewer_index.html"

# globals
logger = None

class _LifespanHandler():  # pylint: disable=too-few-public-methods
    """LifespanHandler knows when the CEF browser is closed."""
    def __init__(self):
        self.cef_browser_closed = False

    @log(logging.INFO)
    def OnBeforeClose(self, browser):  # pylint: disable=unused-argument
        """Sets attribute which indicates that the browser is closed.

        Once the browser is closed, the servers must also be closed."""
        print("browser closed")
        self.cef_browser_closed = True

    @log(logging.INFO)
    def DoClose(self, browser):  # pylint: disable=unused-argument
        """Sets attribute which indicates that the browser is closed.

        Once the browser is closed, the servers must also be closed."""
        print("browser closed")
        self.cef_browser_closed = True
        return True
    
    def OnKeyEvent(self, browser, event, event_type, *args, **kwargs):
        if event_type == cef.KEYEVENT_RAWKEYDOWN:
            # Check for the Ctrl+C keyboard shortcut
            if event["code"] == "KeyC" and event["modifiers"] == cef.EVENTFLAG_CTRL_DOWN:
                # Get the selected text from the browser
                browser.GetFocusedFrame().ExecuteJavascript("document.execCommand('copy');")
        return False


class _SendToQGIS():  # pylint: disable=too-few-public-methods
    """Sends a message to the listeners. """
    def __init__(self, streetsmart_port: int):
        self.port = streetsmart_port

    @log(logging.DEBUG, print_args=True)
    def send_message(self, msg: str):
        """Sends a message to a TCP server in a parallel thread."""
        address = (_HOST, self.port)
        s = _SendMessageInThread(address, msg)
        s.start()


class _SendMessageInThread(threading.Thread):
    """ Class sends messages to QGIS """
    def __init__(self, address: Tuple[str, int], msg: str):
        threading.Thread.__init__(self)
        self.msg = msg
        self.address = address

    @log()
    def run(self):
        """Sends message """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            if not _try_to_connect_to_socket(sock, self.address):
                return
            if not _try_to_send_to_socket(sock, self.msg):
                return


class PanoramaViewer():
    """ Main PanoramaViewer class """
    @log()
    def __init__(self, command_sender, commandline_switches):
        self.commandline_switches = commandline_switches
        self.command_sender = command_sender
        self.lifespan_handler = _LifespanHandler()
        self.command_queue = queue.Queue(maxsize=0)
        self.cef_browser = None
        self.pid_filename = None
        self.tcp_server = None
        self.panorama_viewer_loaded = False
        self.panorama_viewer_initialized = False

    @log(message="Viewer is running in process " + str(os.getpid()))
    def show(self):
        """ Show PanoramaViewer """

        # Start local http server
        self.pid_filename = _start_http_server(0)

        port = _fetch_http_port_number(self.pid_filename)
        self.cef_browser = self.start_cef_browser(port, self.lifespan_handler,
                                                  self.commandline_switches)

    @staticmethod
    @log(level=logging.DEBUG, print_return=True)
    def __create_html_url(port):
        """Creates the url for the start page."""
        return "http://{}:{}/{}".format(_HOST, str(port), _INDEX_URI)

    def start_cef_browser(self, port, lifespan_handler, commandline_switches):
        """ Function starts the browser """

        _check_versions()

        # Set excepthook to shutdown all CEF processes on error
        sys.excepthook = cef.ExceptHook
        if _DEBUG_CEF:
            settings = {
                "debug": True,
                "log_severity": cef.LOGSEVERITY_VERBOSE,
                "log_file": r"c:\temp\debug.log",
                "uncaught_exception_stack_size": -1,
                "ignore_certificate_errors": True,
            }
        else:
            settings = {}

        cef.Initialize(settings=settings, switches=commandline_switches)

        index_url = self.__create_html_url(port)
        cef_browser = cef.CreateBrowserSync(
            url=index_url,
            window_title="Street Smart Panorama Viewer")

        cef_browser.SetClientHandler(lifespan_handler)

        self.set_javascript_bindings(cef_browser)

        return cef_browser

    def _setup_message_loop(self):
        """Sets things up for the message loop to start.

        Starts the TCP server to receive commands.
        """
        self.tcp_server = _start_tcp_server(self.command_queue)
        server_port = self.tcp_server.server_address[1]
        self.command_sender.send_message("serveron|{}".format(server_port))

    @log(logging.DEBUG)
    def _shutdown_message_loop(self):
        """Closes everything after the panoramaviewer is closed."""
        if self.pid_filename:
            self.shutdown(self.pid_filename, self.tcp_server)
            os.remove(self.pid_filename)

    def exec_(self):
        """Starts message loop."""

        self._setup_message_loop()

        # Start Message loop
        self.do_work(self.command_queue, self.lifespan_handler,
                     self.cef_browser, log_port)

        self._shutdown_message_loop()

    @log(logging.DEBUG)
    def add_overlay(self, geojson, name, srs, sld_text, color):
        """ Adds overlay to the panoramaviewer """
        self.cef_browser.ExecuteFunction(
            "addOverlay", geojson, name, srs, sld_text, color)

    def js_measure(self, msg):
        """ Function call from the browser when a measurement is changed """
        self.command_sender.send_message("measure|{}".format(msg))

    def js_cone(self, msg):
        """ Function called from the browser """
        self.command_sender.send_message("cone|{}".format(msg))

    def js_window_loaded(self):
        """ Sends message to QGIS to indicate that the browser is loaded.
        Function called from the browser
        """
        self.panorama_viewer_loaded = True
        self.command_sender.send_message("windowloaded")

    def js_initialized(self):
        """ Function called from the browser """
        self.panorama_viewer_initialized = True

    @log(level=logging.DEBUG)
    def set_javascript_bindings(self, browser):
        """ Sets the functions which can be called from javascript """
        bindings = cef.JavascriptBindings(
            bindToFrames=False, bindToPopups=False)
        bindings.SetFunction("js_cone", self.js_cone)
        bindings.SetFunction("js_measure", self.js_measure)
        bindings.SetFunction("js_initialized", self.js_initialized)
        bindings.SetFunction("js_window_loaded", self.js_window_loaded)
        browser.SetJavascriptBindings(bindings)

    @staticmethod
    @log(print_args=True, print_return=True)
    def __kill_process(pid):
        """Kills the given process."""
        if pid != 0:
            try:
                os.kill(pid, 15)
            except OSError:
                # TODO: log exception
                # self.logger.exception("Could not stop http process %d", pid)
                return "Could not stop http process {}".format(pid)

    @staticmethod
    @log()
    def __stop_tcp_server(tcp_server):
        """Stops a server."""
        tcp_server.shutdown()

    @log(print_args=True)
    def __stop_http_server(self, pid_filename):
        """Stops the http server."""
        pid = _get_httpserver_pid(pid_filename)
        self.__kill_process(pid)

    @log(print_args=True)
    def shutdown(self, pid_filename, tcp_server):
        """ Shutdown all servers and the browser """
        # Send stop to QGIS TCP server
        self.command_sender.send_message("stop")

        self.__stop_http_server(pid_filename)
        self.__stop_tcp_server(tcp_server)

        cef.Shutdown()

    @log(level=logging.INFO)
    def do_work(self,
                command_queue: queue.Queue,
                lifespan_handler: _LifespanHandler,
                cef_browser, log_port=0):
        """
        Handles the commands given to the browser

        These commands the user gives through mouse and keyboard as well as
        the commands which are given via the tcp socket
        """
        command_handler = CommandHandler(cef_browser, log_port)

        while (lifespan_handler and not lifespan_handler.cef_browser_closed
               and not killer.kill_now):
            cef.MessageLoopWork()
            self.localMessageLoopWork(command_queue, command_handler)
            time.sleep(0.01)

        # TODO: close httpserver and tcp server if browser is closed
        print("Stopped do_work loop")
        logging.info("Stopped do_work loop")

    @staticmethod
    @log(logging.INFO)
    def __add_command_to_wait_list(comm):
        """Adds commands to a list to be processed when the communication
        between Viewer and QGIS is established."""
        temp_list.append(comm)

    @staticmethod
    @log(logging.INFO)
    def __process_wait_list(command_handler):
        """Process the commands which were given before the communication
        between Viewer and QGIS was established."""
        comm = temp_list.pop()
        _try_to_execute_command(command_handler, comm)

    def localMessageLoopWork(self,
                             command_queue: queue.Queue,
                             command_handler: CommandHandler):
        """ Processes one command from the queue

        First command must be an 'initialize'. Keep all other commands waiting
        in a temp_list.

        Method runs every *interval* seconds(DEFAULT = 0.1s)
        """
        while self.panorama_viewer_loaded and not command_queue.empty():
            try:
                comm = command_queue.get_nowait()
            except queue.Empty:
                break

            if (not self.panorama_viewer_initialized and not
                    comm[0].startswith("init")):
                self.__add_command_to_wait_list(comm)
            else:
                _try_to_execute_command(command_handler, comm)

        while self.panorama_viewer_initialized and len(temp_list) > 0:
            comm = temp_list.pop()
            _try_to_execute_command(command_handler, comm)


@log(logging.DEBUG, print_args=True, print_return=True)
def _try_to_connect_to_socket(sock: socket,
                              address: Tuple[str, int]) -> bool:
    """Tries to connect to a socket.

    Return True if connected
    """
    try:
        sock.connect(address)
        return True
    except OSError:
        # logger.exception("Cannot connect to %s", address)
        return False


@log(logging.DEBUG, print_args=True, print_return=True)
def _try_to_send_to_socket(sock: socket, msg: str) -> bool:
    """Tries to send the message to the socket."""
    try:
        sock.sendall(bytes(msg + '\n', "utf-8"))
        # logger.debug("Send %s", msg)
        return True
    except OSError:
        # logger.exception("Error sending to socket")
        return False


@log(level=logging.DEBUG, print_return=True)
def _fetch_http_port_number(filename):
    """Fetches the port nummer from the httpd temporary file.

    Must wait till port number is written to the file.
    """
    while True:
        with open(filename, 'r') as process_file:
            lines = process_file.readlines()

        if len(lines) >= 2:
            return int(lines[1].strip())


def _create_temp_filename():
    """ Create a tempfile and return the name """
    handle, filename = tempfile.mkstemp()
    os.close(handle)
    return filename


@log(level=logging.DEBUG, print_return=True)
def _determine_http_server_exe_path():
    """Determines http server path"""
    base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, "httpserver.py")


@log(level=logging.DEBUG, print_return=True)
def _determine_python_exe_path():
    """Determines python executable path"""
    return os.path.join(sys.base_exec_prefix, 'python.exe')


@log()
def _start_http_server(port):
    """Starts http server in another process."""
    file_to_execute = _determine_http_server_exe_path()
    python_exe = _determine_python_exe_path()
    temp_filename = _create_temp_filename()
    subprocess.Popen([python_exe, file_to_execute, str(port),
                      temp_filename, str(log_port)], creationflags=subprocess.CREATE_NO_WINDOW)

    # logger.debug("HTTP Server started with pid %s", proc.pid)
    return temp_filename


def _get_httpserver_pid(filename):
    """ Returns the pid of the http server """
    with open(filename, 'r') as f:
        file_content = f.readline()

    try:
        pid = int(file_content)
    except ValueError:
        pid = 0

    return pid


@log()
def _start_tcp_server(command_queue):
    """Starts the server to listen for calls from QGIS.  """
    tcp_server = CommandGetter(command_queue)
    tcp_server.start()

    return tcp_server


temp_list = []


def write(message):
    """ Write to log file"""
    print("Logger: ", message)
    with open(r"c:\temp\simplelog.log", "a") as flog:
        flog.write(message + '\n')


@log(level=logging.DEBUG, print_args=True)
def _try_to_execute_command(command_handler: CommandHandler,
                            command: Tuple[str, str]):  # , logger: Logger):
    """Tries to execute a command."""
    try:
        command_handler.execute(command)
    except Exception as ex:  # Catch unhandled errors from commands. pylint: disable=broad-except
        write("Unhandled exception in command {}, {}".format(command, ex))
        # logger.exception('Unhandled exception in command %s', command)
        # logger.exception('Unhandled exception in command %s', command)


def _check_versions():
    """Checks CEF versions """
    ver = cef.GetVersion()
    print("[hello_world.py] CEF Python %s", ver["version"])
    print("[hello_world.py] Chromium %s", ver["chrome_version"])
    print("[hello_world.py] CEF %s", ver["cef_version"])
    print("[hello_world.py] Python %s %s",
          platform.python_version(),
          platform.architecture()[0])
    assert cef.__version__ >= "57.0", "CEF Python v57.0+ required to run this"


@log(print_args=True, print_return=True)
def create_commandline_switches(args):
    print("Args")
    print(args)
    rv = {}
    if args.proxy_bypass_list:
        rv["proxy-bypass-list"] = args.proxy_bypass_list
    if args.proxy_server:
        rv["proxy-server"] = args.proxy_server
    if args.no_proxy_server:
        rv["no-proxy-server"] = ""
    if args.proxy_auto_detect:
        rv["proxy_auto_detect"] = ""

    print(rv)
    return rv


@log(print_args=True)
def main(args):
    """ Starts a browser and initialize the bindings """
    Logger(__name__, args.log_port).get()  # Needed to initialize the SocketLogger
    sender = _SendToQGIS(args.command_port)
    commandline_switches = create_commandline_switches(args)
    p = PanoramaViewer(sender, commandline_switches)
    p.show()
    p.exec_()


@log(print_return=True)
def parse_arguments():
    """Parses the command line arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument("command_port",
                        help="port to which commands will be send",
                        type=int)
    parser.add_argument("log_port", help="port to which logging will be send",
                        type=int)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--no-proxy-server", help="no proxy server",
                       action="store_true")
    group.add_argument("--proxy-auto-detect", help="proxy auto detect",
                       action="store_true")
    group.add_argument("--proxy-server", help="proxy server")
    group.add_argument("--proxy-pac-url", help="proxy pac url")
    parser.add_argument("--proxy-bypass-list", help="proxy bypass list")

    ar = parser.parse_args()
    return ar


class GracefullKiller:
    """Class responsible for cleaning up when process is killed

    https://stackoverflow.com/questions/18499497/how-to-process-sigterm-signal-gracefully
    """
    kill_now = False

    def __init__(self):
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)
        signal.signal(signal.SIGBREAK, self.exit_gracefully)

    def exit_gracefully(self, signum, frame):
        """Sets kill flag"""
        print("Caught signal, set stop flag")
        self.kill_now = True


# __name__ is redefined so attribute standalone must be checked
if __name__ == '__main__' or standalone:
    killer = GracefullKiller()
    print('Argument List:', str(sys.argv))
    cmd_line_args = parse_arguments()
    log_port = cmd_line_args.log_port  # TODO: Remove this. Start http server in main, not in PV class
    main(cmd_line_args)

    print("Gracefully stopped")
    logging.shutdown()
