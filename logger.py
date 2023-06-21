"""
Logging class
"""
import logging
from logging.handlers import SocketHandler
from functools import wraps


FORMAT_STRING = '%(asctime)s %(levelname)s:%(name)s %(message)s'
CONSOLE_FORMAT_STRING = '%(message)s'


def set_socket_port(port):
    """Adds a sockethandler to the root logger"""
    _add_sockethandler_if_necessary(port)


def get_logger_name(func):
    """Creates logger name"""
    if hasattr(func, "__class__"):
        class_name = func.__class__.__name__
    else:
        class_name = None

    module = func.__module__

    if class_name and class_name != "function":
        name = (module + "." + class_name + "." + func.__qualname__)
    else:
        name = (module + "." + func.__qualname__)

    return name


def log(level=logging.INFO, message=None, print_args=False,
        print_return=False):
    """Decorator log function """
    def logfunction(func):
        """ Decorator logs function enter and exit """
        @wraps(func)
        def fn_wrapper(*args, **kwargs):
            name = get_logger_name(func)
            logger = logging.getLogger(name)

            if func.__name__:
                logger.log(level, "Entering %s", func.__name__)
            else:
                logger.log(level, "Entering an unknown function")

            if message is not None:
                logger.log(level, message)

            if print_args:
                if args:
                    logger.log(level, "Positional parameters %s", args)
                if kwargs:
                    logger.log(level, "Named parameters %s", kwargs)

            return_value = func(*args, **kwargs)

            if print_return:
                logger.log(level, "Return value: %s", return_value)

            if func.__name__:
                logger.log(level, "Exiting %s", func.__name__)
            else:
                logger.log(level, "Leaving an unknown function")


            return return_value

        return fn_wrapper
    return logfunction


def _create_file_handler(file_name):
    """ Create file handler """
    file_handler = logging.FileHandler(file_name, mode='w')
    formatter = logging.Formatter(FORMAT_STRING)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)
    return file_handler


def _create_console_handler():
    """ Create Console Handler """
    handler = logging.StreamHandler()
    formatter = logging.Formatter(CONSOLE_FORMAT_STRING)
    handler.setFormatter(formatter)
    handler.setLevel(logging.DEBUG)
    return handler


def _create_socket_handler(port):
    """ Create Socket Handler """
    handler = SocketHandler("localhost", port)
    handler.setLevel(logging.DEBUG)
    return handler


def _add_handlers(logger, port=None, file_name=None):
    """Adds handlers."""
    if port is None:
        if file_name:
            logger.addHandler(_create_file_handler(file_name))
        logger.addHandler(_create_console_handler())
    if port is not None:
        logger.addHandler(_create_socket_handler(port))


def _add_sockethandler_if_necessary(port=None):
    """Adds sockethandler if there is no sockethandler already."""
    for handler in logging.root.handlers:
        if isinstance(handler, SocketHandler):
            break
    else:
        if port is not None:
            logging.root.addHandler(_create_socket_handler(port))


def _add_handlers_if_necessary(port, filename):
    """Adds handlers to the root logger."""
    if not logging.root.handlers:
        _add_handlers(logging.root, port, filename)
    else:
        _add_sockethandler_if_necessary(port)


class Logger():  # pylint: disable=too-few-public-methods
    """Logger Class"""
    default_filename = r"c:\temp\streetsmart_start.log"

    def __init__(self, name, port=None, level=logging.DEBUG,
                 filename=None):
        _add_handlers_if_necessary(port, filename)
        logging.root.setLevel(logging.DEBUG)
        logger = logging.getLogger(name)
        logger.setLevel(level)

        self._logger = logger

    def get(self):
        """ Return the logger """
        return self._logger
