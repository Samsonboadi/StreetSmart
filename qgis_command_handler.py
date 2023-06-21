''' Module fetches commands for QGIS Street Smart plugin '''
import queue

try:
    from .logger import Logger
    from .cone_handler import ConeHandler
    from .settings import Settings
    from .measure_handler import MeasureHandler
    from .window_loaded_handler import WindowLoadedHandler
    from .commands.create_measure_command import CreateMeasureCommand
except ImportError:
    from logger import Logger
    from cone_handler import ConeHandler
    from settings import Settings
    from measure_handler import MeasureHandler
    from window_loaded_handler import WindowLoadedHandler
    from commands.create_measure_command import CreateMeasureCommand


logger = Logger(__name__).get()  # pylint: disable=invalid-name


class QGISCommandHandler():  # pylint: disable=too-few-public-methods
    ''' Public interface for QGIS '''
    def __init__(self, streetsmart, command_queue):
        self.command_queue = command_queue
        self.streetsmart = streetsmart
        self.iface = streetsmart.iface
        height = Settings.getInstance().get_cone_height()
        self.cone_handler = ConeHandler(self.streetsmart, height)
        self.measureHandler = MeasureHandler(self.iface, None)
        self.window_loaded_handler = WindowLoadedHandler(self.streetsmart,
                                                         Settings.getInstance())

    def fetch_commands(self):
        ''' Fetch commands from queue '''
        try:
            while not self.command_queue.empty():
                comm = self.command_queue.get_nowait()
                if comm[0] == "cone":
                    logger.debug("Cone with %s", comm[1])
                    self.cone_handler.handle(comm[1])
                elif comm[0] == "measure":
                    commands = [c for c in self.streetsmart.commands if isinstance(c, CreateMeasureCommand)]
                    if commands and commands[0].is_checked:
                        logger.debug("Measure with %s", comm[1])
                        self.measureHandler.handle(comm[1])
                    else:
                        logger.debug("Measure received but command is not checked")
                elif comm[0] == "windowloaded":
                    logger.debug("Window Loaded")
                    self.window_loaded_handler.handle(None)
                elif comm[0] == "stop":
                    logger.debug("Viewer Stopped")
                    # Stop is given when viewer is closed. Assume this here
                    self.streetsmart.buttonstate.viewer_open = False
                    self.streetsmart.buttonstate.panorama_viewer_server_port = 0
                    self.cone_handler.handle(None)
                elif comm[0] == "serveron":
                    logger.debug("Server On")
                    self.streetsmart.pv_server_port = int(comm[1])
                else:
                    logger.debug("Ongekend commando %s", comm[0])
        except queue.Empty:
            logger.debug("QGIS Command Queue is empty")
