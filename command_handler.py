""" Handles the commands to the Street Smart browser """

import json
import logging
from logger import Logger  # pylint: disable=import-error
from logger import log  # pylint: disable=import-error

cef_browser = None


@log(level=logging.INFO)
def js_init(args):
    """ Calls the cef browser to initialize the StreetSmart api
    args is a json string
    """
    try:
        settings = json.loads(args)
        userSettings = settings["userSettings"]
        addressSettings = settings["addressSettings"]
        configSettings = settings["configSettings"]
        cef_browser.ExecuteFunction("initApi", userSettings,
                                    addressSettings, configSettings)
    except:
        logging.exception("Probleem")


@log(level=logging.DEBUG)
def js_open(args):
    ''' Calls the javascript function to open a coordinate '''
    print("Execute javascript open with ", args)
    cef_browser.ExecuteFunction("open", args)


@log(level=logging.DEBUG)
def js_addoverlay(args):
    """ Adds an overlay to the Street Smart browser """
    geojson, name, srs, sldText, color = args.split('/')
    geojson = geojson.replace("__", r"/")
    sldText = sldText.replace("__", r"/")
    print("Execute addoverlay with {}, {}, {}, {}, {}".format(
        geojson, name, srs, sldText, color))
    cef_browser.ExecuteFunction(
        "addOverlay", geojson, name, srs, sldText, color)


@log(level=logging.DEBUG)
def js_removeoverlay(_):
    """ Send command to remove all overlay layers """
    cef_browser.ExecuteFunction("removeOverlay")


@log(level=logging.DEBUG)
def js_restartmeasure(args):
    """ Calls cef browser to stop and start a measurement
    args in ['point', 'polyline', 'polygon']
    """
    cef_browser.ExecuteFunction("stopMeasure")
    cef_browser.ExecuteFunction("startMeasure", args)


@log(level=logging.DEBUG)
def js_startmeasure(args):
    """ Calls cef browser to start a measurement
    args in ['point', 'polyline', 'polygon']
    """
    cef_browser.ExecuteFunction("startMeasure", args)


@log(level=logging.DEBUG)
def js_stopmeasure(args):
    """ Calls cef browser to stop a measurement """
    cef_browser.ExecuteFunction("stopMeasure")


@log(level=logging.DEBUG)
def js_getmeasure(args):
    """ Calls cef browser for measurement """
    cef_browser.ExecuteFunction("getMeasure")


@log(level=logging.INFO)
def stopviewer(args):
    """Closes the browser"""
    cef_browser.CloseBrowser(False)


js_commands = {
    "initapi": js_init,
    "open": js_open,
    "overlay": js_addoverlay,
    "removeoverlay": js_removeoverlay,
    "startmeasure": js_startmeasure,
    "restartmeasure": js_restartmeasure,
    "stopmeasure": js_stopmeasure,
    "getmeasure": js_getmeasure,
    "stopviewer": stopviewer,
}


class CommandHandler():
    ''' Dispatches the commands for the viewer '''
    @log(level=logging.INFO)
    def __init__(self, browser, log_port=0):
        global cef_browser
        cef_browser = browser
        if log_port != 0:
            Logger(__name__, log_port).get()


    @staticmethod
    @log(print_args=True)
    def execute(command):
        """ Calls the corresponding function for the given command """
        if command[0] in js_commands:
            js_commands[command[0]](command[1])
        else:
            logging.debug("Keyword %s not found", command[0])
