# -*- coding: utf-8 -*-
"""StreetSmart

This module is the main entrance for the QGIS plugin. The functions and classes
in this module make it possible to communicate between QGIS, the plugin
commands and the panorama viewer.

This module defines:

    - an AbstractCommand class which must be implemented by the actions which
      the plugin will register in the QGIS toolbar.

    - the StreetSmart class which is the entry point for the plugin and
      contains the necessary functionality for the plugin

    - a SendMessage class which sends message over TCP to the panorama viewer.

"""
import importlib


import inspect
import logging
import os
import os.path
import queue
import signal
import socket
import subprocess
import sys
import time
import typing
import shutil



from abc import abstractmethod, ABCMeta
from threading import Thread
from qgis.PyQt.QtCore import (QTimer)  # pylint: disable=import-error
from qgis.PyQt.QtCore import (  # pylint: disable=import-error
    QSettings,
    QTranslator,
    QCoreApplication,
)

from qgis.core import (QgsVectorLayer,QgsExpressionContextUtils, QgsProject,Qgis)  # pylint: disable=import-error
from qgis.PyQt.QtGui import QIcon  # pylint: disable=import-error
from qgis.PyQt.QtWidgets import (QAction, QMessageBox)  # pylint: disable=import-error
from qgis.PyQt.QtCore import (QObject, pyqtSignal)  # pylint: disable=import-error
from PyQt5.QtWidgets import QInputDialog, QVBoxLayout, QWidget, QCheckBox, QDialog, QLabel, QDialogButtonBox
from .install import install_cefpython3,check_DLLS,copy_missen_DLLS,return_Qgis_bin_path,check_Cefpython_installation
from .checkboxDLLs import CheckboxDialog

# pylint: disable=wildcard-import, unused-wildcard-import
# Try-Except construct is needed because sphinx autodoc feature does not
# import this module from a package and thus cannot use relative imports.
try:
    # Initialize Qt resources from file resources.py
    from .resources import *  # noqa: F403,F401
    from .command_getter import CommandGetter
    from .logger import Logger
    from .logger import log
    from .logger import set_socket_port
    from .settings import Settings
    from .controller import initialize_servers
    from .utils import (start_python_script, convert_meters_to_mapunits)
except ImportError:
    from resources import *  # noqa: F403,F401
    from command_getter import CommandGetter
    from logger import Logger
    from logger import log
    from logger import set_socket_port
    from settings import Settings
    from controller import initialize_servers
    from utils import (start_python_script, convert_meters_to_mapunits)
# pylint: enable=wildcard-import, unused-wildcard-import
#Get Qgis version and append Ebinoath to system ENV
    get_Qgis_version = QgsExpressionContextUtils.globalScope().variable('qgis_version')
    get_Qgis_version = get_Qgis_version.split('-')[0]
    sources_path=os.path.join(r"C:\Program Files\QGIS " +get_Qgis_version + "/bin")
    os.environ['PATH'] += sources_path
    import sys
    sys.path.append(sources_path)

# Module constants
HOST = "localhost"
GEOJSON_PACKAGE_NAME = "geojson"
SHAPELY_PACKAGE_NAME = "shapely"
CEFPYTHON_PACKAGE_NAME = "cefpython3"
CEFPYTHON_PACKAGE_VERSION = "66.1"
CEFPYTHON_FULL_PACKAGE_NAME = CEFPYTHON_PACKAGE_NAME + "==" + CEFPYTHON_PACKAGE_VERSION  # pylint: disable=line-too-long
PYTHON_EXECUTABLE = "python.exe"
COMMANDSDIRECTORY = "commands"

FILENAME = os.path.basename(__file__)
if __name__ == "__main__":
    logger = Logger(FILENAME).get()
else:
    logger = Logger(__name__).get()  # pylint: disable=invalid-name

show_cmd = False





class AbstractCommand(metaclass=ABCMeta):
    """Definition of the interface a command must have."""
    def __init__(self, iface, streetsmart):
        '''
        Constructor
        '''
        self.iface = iface
        self.__streetsmart = streetsmart
        self.__enabled = True

    @property
    def action(self):
        """Returns the Qt action for this command."""
        return self.streetsmart.get_action_for_command(self)

    @property
    def streetsmart(self):
        """Returns the Street Smart reference."""
        return self.__streetsmart

    @property
    def enabled(self):
        """Return true if the command is enabled."""
        return self.__enabled

    @enabled.setter
    def enabled(self, value):
        self.__enabled = value

    def __set_enabled(self, enabled):
        """Sets the enabled flag for a command."""
        action = self.streetsmart.get_action_for_command(self)
        if action:
            action.setEnabled(enabled)
        self.__enabled = enabled

    def set_enabled(self):
        """Sets a command to enabled."""
        self.__set_enabled(True)

    def set_disabled(self):
        """Sets a command to disabled."""
        self.__set_enabled(True)

    def show_set_settings_message_box(self):
        """Show message"""
        title = self.tr('Add Atlas WFS')
        message = self.tr('Please set username and password first in the settings dialog box')
        QMessageBox.information(None, title, message, QMessageBox.Ok)

    @staticmethod
    @log(logging.DEBUG, print_return=True)
    def are_usersettings_available():
        """Returns true if username and password are set"""
        if Settings.getInstance().settings[Settings.PASSWORD].value:
            return True
        return False

    @staticmethod
    def tr(message):
        """Returns the message

        A stupid way to have pyupdate5 get the message. All string in a
        function called tr() or translate() are found.
        """
        return QCoreApplication.translate('StreetSmart', message)

    @staticmethod
    @abstractmethod
    def icon_path():
        """Returns the path of the icon to shown on the toolbar."""

    @abstractmethod
    def text(self):
        """Returns the tooltip text to be shown when hoovering the toolbar."""

    @abstractmethod
    def parent(self):
        """Parent of the action."""

    @abstractmethod
    def callback(self):
        """Method to be executed when the action is clicked."""


class StreetSmart_Cone(typing.NamedTuple):
    """A streetsmart cone"""
    cone: typing.Any
    srs: str


class ButtonStateSubject(QObject):
    """Sends signals whenever the state of the plugin is changed.

    Keeps track of the state of the plugin."""
    panorama_viewer_opened = pyqtSignal()
    panorama_viewer_closed = pyqtSignal()
    atlas_wfs_added = pyqtSignal()
    atlas_wfs_removed = pyqtSignal()
    new_project_created = pyqtSignal()
    project_read = pyqtSignal()
    map_canvas_refreshed = pyqtSignal()
    map_scale_changed = pyqtSignal()
    cone_moved = pyqtSignal()
    panorama_viewer_server_port_set = pyqtSignal()

    def __init__(self, iface, streetsmart):
        """Constructor

        :params iface: Interface with QGIS
        :type iface: QgsInterface
        """
        super().__init__()
        self.__viewer_open = False
        self.__wfs_added = False
        self.__previous_cone: typing.Optional[StreetSmart_Cone] = None
        self.iface = iface
        self.__panorama_viewer_server_port = 0
        self.__streetsmart = streetsmart

        # Wire up the signals
        iface.newProjectCreated.connect(self.on_project_created)
        iface.projectRead.connect(self.on_project_read)
        map_canvas = iface.mapCanvas()
        map_canvas.mapCanvasRefreshed.connect(self.on_map_canvas_refreshed)
        map_canvas.scaleChanged.connect(self.on_map_scale_changed)
        QgsProject.instance().layerWillBeRemoved.connect(self.on_layer_will_be_removed)


        #TODO refactor checks if the required DLLS are available if not copies them from the Bin dir to the DLLS dir
        if not check_DLLS()[0]:
            files = ['libssl-1_1-x64.dll', 'libcrypto-1_1-x64.dll']
            checkbox_dialog = CheckboxDialog(files)
            result = checkbox_dialog.exec_()
            # Get the selected files if the OK button is clicked
            print("returned files",check_DLLS()[1])
            
            if result == QDialog.Accepted:
                #selected_files = checkbox_dialog.selected_files
                print("Selected files:", files)
                for files in files:
                    print(files)
                    copy_missen_DLLS(os.path.join(return_Qgis_bin_path(check_DLLS()[1]),files),os.path.join(check_DLLS()[1],files))
            else:
                print("Dialog canceled")


        #TODO check if Cefpython3 is not installed and install it
        if not check_Cefpython_installation():
            install_cefpython3()





    









    

    @property
    def panorama_viewer_server_port(self):
        """Returns the port the panorama viewer is listening to."""
        return self.__panorama_viewer_server_port

    @panorama_viewer_server_port.setter
    def panorama_viewer_server_port(self, value):
        logger.debug("Set state port to %s", value)
        self.__panorama_viewer_server_port = value
        if value != 0:
            self.panorama_viewer_server_port_set.emit()

    @property
    def previous_cone(self):
        """ Returns the cone which is currently shown on the mapCanvas """
        return self.__previous_cone

    @staticmethod
    @log(logging.DEBUG, print_return=True)
    def get_rubberband_points(cone):
        """ Returns the points of the given rubberband """
        if cone:
            return [cone.getPoint(0, i) for i in range(cone.numberOfVertices())]

        return []

    def on_layer_will_be_removed(self, layer_id):
        """Handles the layer removed signal"""
        layer = QgsProject.instance().mapLayer(layer_id)
        default_layer_name = Settings.getInstance().getRecordingLayerName()
        if (layer
                and layer.name() == default_layer_name):
            self.__streetsmart.hide_viewer()
            self.atlas_added = False

    @log(logging.DEBUG, print_args=True, print_return=True)
    def __has_cone_moved(self, previous_cone, cone):
        """Returns True if the cone has moved."""
        previous_points = self.get_rubberband_points(previous_cone)
        current_points = self.get_rubberband_points(cone)

        for point in current_points:
            for prev_point in previous_points:
                # Compare points, if one point is in an area 1 meters then the
                # cone is not moved.
                epsilon = convert_meters_to_mapunits(1, self.iface.mapCanvas())
                if point.compare(prev_point, epsilon=epsilon):
                    return False

        return True

    @log(logging.DEBUG)
    def raise_if_cone_moved(self, previous_cone, cone):
        """ Emit signal if the cone has moved

        The cone has move if all three points are different
        """
        if self.__has_cone_moved(previous_cone, cone):
            self.cone_moved.emit()

    @previous_cone.setter
    def previous_cone(self, cone):
        if not self.__previous_cone:
            prev_cone = None
        else:
            prev_cone = self.__previous_cone.cone
        self.__previous_cone = cone
        self.raise_if_cone_moved(prev_cone, cone.cone)

    def set_cone_srs(self, srs: str):
        """Set spatial reference for cone"""
        self.__previous_cone.srs = srs

    @property
    def viewer_open(self):
        """ Returns true if the panorama viewer is visible """
        return self.__viewer_open

    @viewer_open.setter
    def viewer_open(self, value):
        print("Set Viewer ", value)
        if value == self.__viewer_open:
            return

        if value:
            print("Emit Panorama Viewer Opened")
            self.panorama_viewer_opened.emit()
        else:
            print("Emit Panorama Viewer Closed")
            self.panorama_viewer_closed.emit()

        self.__viewer_open = value

    @property
    def atlas_added(self):
        """ Returns true if the Atlas WFS is added to the current project """
        return self.__wfs_added

    @atlas_added.setter
    def atlas_added(self, value):
        if value:
            self.atlas_wfs_added.emit()
        else:
            self.atlas_wfs_removed.emit()

        self.__wfs_added = value

    def on_project_created(self):
        """ Executes when a new project is created """
        self.__streetsmart.hide_viewer()
        self.viewer_open = False
        self.new_project_created.emit()

    @staticmethod
    @log(level=logging.DEBUG, print_return=True)
    def __get_legend_layer_names():
        """Returns a list with layer names"""
        layers = QgsProject.instance().mapLayers().values()
        return [l.name() for l in layers]

    @log(level=logging.DEBUG, print_return=True)
    def project_contains_atlas_layer(self):
        """Returns if the current project has the atlas layer in its legend."""
        layer_names = self.__get_legend_layer_names()
        return Settings.getInstance().getRecordingLayerName() in layer_names

    def on_project_read(self):
        """ Executes when an existing project is read """
        self.__streetsmart.hide_viewer()
        # stop_panorama_viewer_if_necessary()
        if not self.project_contains_atlas_layer():
            self.viewer_open = False
            self.atlas_added = False
        else:
            self.atlas_added = True

        self.project_read.emit()

    def on_map_canvas_refreshed(self):
        """ Executes when the mapCanvas is refreshed """
        self.map_canvas_refreshed.emit()

    def on_map_scale_changed(self):
        """ Executes when the mapScale is changed """
        self.map_scale_changed.emit()


class SendMessage(Thread):
    """ Send a Message """
    @log(logging.DEBUG)
    def __init__(self, state, msg):
        Thread.__init__(self)
        self.__state = state
        self.__msg = msg

    def run(self):
        logger.debug("SendMessage instance started")
        count = 0
        while self.__state.panorama_viewer_server_port == 0:
            count = count + 1
            time.sleep(0.1)
            if count > 1000:
                count = 0
                logger.debug("Still waiting for pv server port")

        logger.debug("Got pv port %s",
                     self.__state.panorama_viewer_server_port)
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                logger.debug("Send %s to port %d", self.__msg,
                             self.__state.panorama_viewer_server_port)
                sock.connect((HOST, self.__state.panorama_viewer_server_port))
                sock.sendall(bytes(self.__msg, "utf-8"))

            logger.debug("Should have send message %s", self.__msg)
        except OSError:
            logger.exception("Probleem")


class StreetSmart:  # pylint: disable=too-many-instance-attributes
    """QGIS Plugin Implementation.

    The StreetSmart class is the intermediate between QGIS and the Street Smart
    plugin functionality. The constructor gets an instance of the QgsInterface.
    The class must have an initGui, """

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        if logger:
            logger.debug("Init StreetSmart Plugin")

        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        if logger:
            logger.debug("Locale: %s", locale)
        locale_path = os.path.join(
            plugin_dir,
            'i18n',
            'StreetSmart_{}.qm'.format(locale))

        if logger:
            logger.debug("Locale path: %s", locale_path)
        if os.path.exists(locale_path):
            if logger:
                logger.debug("Install Translator")
                logger.debug("Locale path: %s", locale_path)
                logger.debug("Locale: %s", locale)
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.commands = []  # Commands must be save, otherwise they disappear
        self.proc = None
        self.__pv_server_port = 0

        self.menu = self.tr(u'&StreetSmart')
        self.toolbar = self.iface.addToolBar(u'Street Smart')
        self.toolbar.setObjectName(u'Street Smart')
        self.buttonstate = ButtonStateSubject(iface, self)
        self.command_queue = queue.Queue()
        self.command_handler = None
        self.log_port = None
        self.log_pid = None
        _install_cefpython_when_not_available()
        _install_geojson_when_not_available()
        _install_shapely_when_not_available() 
        #_copy_ssl_modules("libcrypto-1_1-x64.dll")
        #_copy_ssl_modules("libcrypto-1_1.dll","libcrypto-1_1.dll") 
       # _copy_ssl_modules("libssl-1_1-x64.dll")
        #_copy_ssl_modules("libssl-1_1.dll","libssl-1_1.dll")

    @property
    def pv_server_port(self):
        """Returns the Panorama Viewer server port."""
        return self.__pv_server_port

    @pv_server_port.setter
    def pv_server_port(self, value):
        logger.debug("Set port %s", value)
        self.buttonstate.panorama_viewer_server_port = value

    @property
    def panorama_viewer_visible(self):
        """Returns true if the panorama viewer is visible."""
        if self.proc is not None:
            poll = self.proc.poll()
            if poll is None:
                # panoramaview subprocess is still alive
                return True

        return False

    def get_action_for_command(self, command):
        """Returns the QGIS action for the StreetSmart command."""
        action = None
        if self.commands:
            try:
                command_index = self.commands.index(command)
            except ValueError:
                command_index = -1

            if command_index >= 0:
                action = self.actions[command_index]

        return action

    @log(level=logging.DEBUG, print_args=True)
    def sendToViewer(self, msg: str):  # pylint: disable=invalid-name
        """Sends message to viewer."""
        logger.debug("Send message to PanoramaViewer: %s", msg)

        sender = SendMessage(self.buttonstate, msg)
        sender.start()

    # noinspection PyMethodMayBeStatic
    @staticmethod
    def tr(message):  # pylint: disable=invalid-name
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('StreetSmart', message)

    def add_action(  # pylint: disable=too-many-arguments
            self,
            icon_path,
            text,
            callback,
            enabled_flag=True,
            add_to_menu=True,
            add_to_toolbar=True,
            status_tip=None,
            whats_this=None,
            parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            # Adds plugin icon to Plugins toolbar
            self.toolbar.addAction(action)
#            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):  # pylint: disable=invalid-name
        """Creates the menu entries and toolbar icons inside the QGIS GUI."""

        log_pid, server_log_port = initialize_servers()
        print("Initialized: ", log_pid, server_log_port)
        self.log_port = server_log_port
        self.log_pid = log_pid
        set_socket_port(server_log_port)
        # Must create a new logger to add the tcp handler.
        # The set_socket_port apparently does not suffice
        Logger(__name__, port=server_log_port).get()  # pylint: disable=invalid-name
        logger.info("=== %s initialized ===", __name__)

        self.install_commands()

    def current_layer_changed(self, new_current_layer):
        """ Event handler when current layer changes """
        is_vector_layer = isinstance(new_current_layer, QgsVectorLayer)
        if is_vector_layer and new_current_layer.isEditable():
            geometry_type = self.get_vectorlayer_feature_type(new_current_layer)
            geometry_type = geometry_type if geometry_type else 'point'  # Set default value
            self.sendToViewer("restartmeasure|" + geometry_type)
        else:
            self.sendToViewer("stopmeasure")

    @log(level=logging.DEBUG, print_return=True)
    def get_vectorlayer_feature_type(self, layer):
        """ Returns the geometric type of features are kept in the layer """
        geometry_type = layer.geometryType()
        return self.__geometry_to_string(geometry_type)

    @staticmethod
    @log(level=logging.DEBUG, print_args=True, print_return=True)
    def __geometry_to_string(geometry_type: int):
        """Converts a geomtry type to a readable string."""
        if geometry_type == 0:
            return "point"
        if geometry_type == 1:
            return "polyline"
        if geometry_type == 2:
            return 'polygon'

        return None

    @log(level=logging.DEBUG)
    def __add_actions(self, modules):
        """ Add Actions """
        toolbar_ordered_commands = ['AddAtlasWFSLayerCommand',
                                    'ShowCycloramaCommand',
                                    'AddOverlayCommand',
                                    'CreateMeasureCommand',
                                    'ManageSettingsCommand',
                                    'ShowHelpCommand',
                                    ]

        all_commands = {}
        for module in modules:
            pkg_parent = module[0]
            command_module = module[1]
            clsmembers = inspect.getmembers(command_module,
                                            inspect.isclass)
            for clsname, cls in clsmembers:
                if (cls.__module__.startswith(pkg_parent) and
                    issubclass(cls, AbstractCommand)):
                        all_commands[clsname] = cls

        for cmd in toolbar_ordered_commands:
            if cmd in all_commands:
                cls = all_commands[cmd]
                del all_commands[cmd]
                self.__create_action_from_class(cls, True)

        for cmd in all_commands:
            cls = all_commands[cmd]
            self.__create_action_from_class(cls, False)

        # Import QGISCommandHandler here, to prevent cyclic imports e.g.
        # QGISCommandHandler imports CreateMeasureCommand which imports
        # StreetSmart which imports logger
        # pylint: disable=import-outside-toplevel
        from .qgis_command_handler import QGISCommandHandler
        # pylint: enable=import-outside-toplevel
        self.command_handler = QGISCommandHandler(self, self.command_queue)

    def __create_action_from_class(self, command_class, add_to_toolbar):
        """ Create an action from a given AbstractCommand class """
        command_instance = command_class(self.iface, self)
        if hasattr(command_instance, 'enabled'):
            enabled = command_instance.enabled
        else:
            enabled = True

        self.add_action(
            command_instance.icon_path(),
            text=self.tr(command_instance.text()),
            add_to_toolbar=add_to_toolbar,
            enabled_flag=enabled,
            callback=command_instance.callback,
            parent=command_instance.parent())

        self.commands.append(command_instance)

    def install_commands(self):
        """ Install all the commands """
        modules = _import_commands(COMMANDSDIRECTORY)
        self.__add_actions(modules)

    @staticmethod
    @log(print_return=True)
    def __start_qgis_command_tcp_server(command_queue):
        """ Start tcp server to get commands from panoramaviewer """
        server = CommandGetter(command_queue)
        port = server.server_address[1]
        server.start()
        return port

    def __create_proxy_command_line_arguments(self):
        """Returns the proxy arguments for the viewer."""
        from . import proxyutils
        import urllib.request
        proxies = urllib.request.getproxies()
        qgis_settings = Settings.getInstance().settings
        proxy_settings = proxyutils.ProxySettings(
                use_proxy_server=qgis_settings[Settings.USE_PROXY_SERVER].value,
                proxy_server_type=qgis_settings[Settings.PROXY_SERVER_TYPE].value,
                proxy_excluded_urls=qgis_settings[Settings.PROXY_EXCLUDED_URLS].value,
                proxy_no_proxy_urls=qgis_settings[Settings.PROXY_NO_PROXY_URLS].value,
                proxy_address=qgis_settings[Settings.PROXY_ADDRESS].value,
                proxy_port=qgis_settings[Settings.PROXY_PORT].value
        )
        return proxyutils.create_proxy_command_line_arguments(proxy_settings, proxies)

    @log(print_return=True)
    def __create_command_line_arguments(self, port, log_port):
        """Returns the command line arguments for the viewer process."""
        cmd_line_args = [str(port), str(log_port)]
        cmd_line_args.extend(self.__create_proxy_command_line_arguments())
        return cmd_line_args

    @log()
    def start_panorama_viewer(self, port, log_port):
        """ Start the panorama viewer in another process """
        cmd_line_args = self.__create_command_line_arguments(port, log_port)
        print("Args for start Viewer")
        print(cmd_line_args)
        print("Start Viewer")
        return start_python_script("panorama_viewer.py",
                                   cmd_line_args, not show_cmd)

    @log()
    def show_viewer(self):
        """Show CEF browser window"""

        if self.panorama_viewer_visible:
            return

        # Command server must be started before CEF is shown.
        port = self.__start_qgis_command_tcp_server(self.command_queue)

        # Show CEF
        self.proc = self.start_panorama_viewer(port, self.log_port)

        # Start fetching commands
        self.__fetch_viewer_commands()

    def __fetch_viewer_commands(self):
        """ Fetch the commands from the panorama viewer """
        self.command_handler.fetch_commands()
        interval = int(Settings.getInstance().get_timer_interval())
        QTimer.singleShot(interval, self.__fetch_viewer_commands)

    @log()
    def __remove_actions(self):
        """Removes the Qt actions"""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&StreetSmart'),
                action)
            self.iface.removeToolBarIcon(action)

    @log()
    def hide_viewer(self):
        """Stops the panorama viewer."""
        if self.panorama_viewer_visible:
            self.sendToViewer("stopviewer")

    @log()
    def unload(self):
        """Restores the state of QGIS as if the plugin was never installed.

        Removes the plugin menu items and icons from QGIS GUI. Stops the
        viewer."""

        self.hide_viewer()

        # Stop log service
        self.__kill_process(self.log_pid)

        self.__remove_actions()

        # remove the toolbar
        del self.toolbar

        logging.info("Shutdown")
        logging.shutdown()

    @staticmethod
    @log(print_args=True)
    def __kill_process(pid):
        """Kills a process """
        os.kill(pid, signal.SIGTERM)


def _copy_ssl_modules(file_source):
    """ The Python ssl module for latest version of Qgis(python39) needs to be
    copied to the correct location for pip install to work
    files to copy 
    1. libcrypto-1_1-x64.dll
    2. libssl-1_1-x64.dll
    
    sorces path C:\Program Files\QGIS 3.22.9/bin
    destination path C:\Program Files\QGIS 3.22.9/apps\Python39\DLLs"""

    get_Qgis_version = QgsExpressionContextUtils.globalScope().variable('qgis_version')
    get_Qgis_version = get_Qgis_version.split('-')[0]
    sources_path=os.path.join(r"C:\Program Files\QGIS " +get_Qgis_version + "/bin",file_source)
    destination_path=os.path.join(r"C:\Program Files\QGIS " + get_Qgis_version +"/apps\Python39\DLLs",file_source)

    if not os.path.exists(destination_path):
        shutil.copy2(sources_path,destination_path)


def _import_commands(directory: str) -> typing.List:
    """Imports all the modules under a given directory.

    :paramater directory: absolute path to the directory which contains the
        modules
    :returns: A list with all the modules in the directory"""
    _old_cwd = os.getcwd()
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    result = []

    possible_commands = os.listdir(directory)

    for command in possible_commands:
        if not (command != "__init__.py" and command.endswith(".py")):
            continue

        if logger:
            logger.debug("Import %s", command)
        filename, _ = os.path.splitext(command)
        modulename = directory + "." + filename
        if __name__ != '__main__':
            pkg = ".".join(__name__.split('.')[:-1])
            if len(pkg.strip()) > 0:
                modulename = pkg + "." + modulename
                pkg_parent = pkg + "." + directory
        try:
            command_module = importlib.import_module(modulename)
            result.append((pkg_parent, command_module))
        except ImportError as e:
            print(e)

    # Restore old path
    os.chdir(_old_cwd)

    return result


def _install_package_with_pip(package_name: str) -> bool:
    """Installs cefpython3 package.

    :returns: True if package is installed successfully, False otherwise.
    """
    return_value = False
    python_exe = os.path.join(sys.base_exec_prefix, PYTHON_EXECUTABLE)
    cur_dir = os.path.dirname(os.path.abspath(__file__))
    try:
        returncode = subprocess.run([python_exe,
                                     "-m", "pip", "install",
                                     "--user",
                                     package_name],
                                    check=False,
                                    stderr=subprocess.PIPE,
                                    stdout=subprocess.PIPE)
        if returncode.returncode != 0:
            wheels_dir = os.path.join(cur_dir, "wheels")
            returncode = subprocess.run([python_exe,
                                         "-m", "pip", "install",
                                         "--user", "--no-index",
                                         "--find-links=" + wheels_dir,
                                         package_name],
                                        check=False,
                                        stderr=subprocess.PIPE,
                                        stdout=subprocess.PIPE)
            if returncode.returncode != 0:
                logger.error("Installation failed! Exit!")
                return_value = False

        if logger:
            logger.info("%s installation succeeded!", package_name)
        return_value = True
    except subprocess.CalledProcessError:
        if logger:
            logger.exception("Error occurred at installing %s", package_name)
        return_value = False

    return return_value


def _install_package(package_name, full_package_name=None):
    """Checks for a Python package and installs package if it is not
    available.

    :returns:  0 if package was not found but is installed successfully
              -1 if package was not found and could not be installed
               1 if package was already installed
    """
    full_package_name = full_package_name or package_name
    if importlib.util.find_spec(package_name) is None:
        if logger:
            logger.info("%s not installed. Try to install %s...", package_name,
                        full_package_name)

        return _install_package_with_pip(full_package_name)

    if logger:
        logger.info("%s already installed", package_name)
    return 1


def _install_cefpython_when_not_available():
    """Checks for CEF Python package and installs package if it is not
    available.

    :returns:  0 if cefpython3 was not found but is installed successfully
              -1 if cefpython3 was not found and could not be installed
               1 if cefpython3 was already installed
    """
    return _install_package(CEFPYTHON_PACKAGE_NAME, CEFPYTHON_FULL_PACKAGE_NAME)



def _install_shapely_when_not_available():
    """Checks for shapely Python package and installs package if it is not
    available.

    :returns:  0 if shapely was not found but is installed successfully
              -1 if shapely was not found and could not be installed
               1 if shapely was already installed
    """
    return _install_package(SHAPELY_PACKAGE_NAME)


def _install_geojson_when_not_available():
    """Checks for geoJSON Python package and installs package if it is not
    available.

    :returns:  0 if geoJSON was not found but is installed successfully
              -1 if geoJSON was not found and could not be installed
               1 if geoJSON was already installed
    """
    return _install_package(GEOJSON_PACKAGE_NAME)
