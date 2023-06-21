""" Module select cyclorama """
import json
import logging

from qgis.gui import (QgsMapToolEmitPoint)  # pylint: disable=import-error
from ..logger import Logger
from ..logger import log
from ..street_smart import AbstractCommand

logger = Logger(__name__).get()


class ShowCycloramaCommand(AbstractCommand):
    """
    Class for Show Cyclorama Command
    """
    def __init__(self, iface, streetsmart):
        """
        Constructor
        """
        super().__init__(iface, streetsmart)
        super().set_disabled()
        self.streetsmart.buttonstate.atlas_wfs_added.connect(self.set_enabled)
        self.streetsmart.buttonstate.atlas_wfs_removed.connect(
            self.set_disabled)
        self.select_point_tool = QgsMapToolEmitPoint(self.iface.mapCanvas())
        self.select_point_tool.canvasClicked.connect(self.canvas_clicked)

    @staticmethod
    def icon_path():
        """
        Path for the icon
        """
        return ':/plugins/street_smart/resources/mActionSelect.svg'

    def text(self):
        """
        Text for the command to show
        """
        return super().tr('Select Cyclorama point')

    def parent(self):
        """
        Parent
        """
        return self.iface.mainWindow()

    def callback(self):
        """
        Code to execute when command is clicked
        """
        if self.are_usersettings_available():
            self.iface.mapCanvas().setMapTool(self.select_point_tool)
        else:
            self.show_set_settings_message_box()

    @log(logging.DEBUG, print_return=True)
    def __create_point_string(self, point) -> str:
        """Creates JSON string from point"""
        logger.debug("Select cyclorama around (%s,%s)", point.x, point.y)
        point = "{},{}".format(point.x(), point.y())
        crs = self.iface.mapCanvas().mapSettings().destinationCrs().authid()
        msg = {}
        msg["point"] = point
        msg["crs"] = crs
        return json.dumps(msg).replace('\n', '')

    def __send_point_to_viewer(self, point) -> None:
        """Sends the view point to the viewer."""
        msg = self.__create_point_string(point)
        msg = "open|" + msg + '\n'

        self.streetsmart.sendToViewer(msg)

    @log(logging.DEBUG, print_args=True)
    def canvas_clicked(self, point, button):
        """ Draw cone on the clicked point

        Input: point: point where the user has clicked on the canvas

        Output: none
        """
        if not self.streetsmart.panorama_viewer_visible:
            self.streetsmart.show_viewer()

        self.__send_point_to_viewer(point)

        self.streetsmart.buttonstate.viewer_open = True
