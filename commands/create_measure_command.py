''' Module for Starting a Measurement '''
import logging

# pylint: disable=no-name-in-module, wrong-import-position, import-error
# noqa: E402
from qgis.core import (  # noqa: E402
    QgsVectorLayer,
)
from PyQt5.QtWidgets import QMessageBox
from ..logger import Logger  # noqa: E402
from ..logger import log  # noqa: E402
from ..street_smart import AbstractCommand  # noqa: E402

logger = Logger(__name__).get()


class CreateMeasureCommand(AbstractCommand):
    '''
    Class for Create Measure Command
    '''
    def __init__(self, iface, streetsmart):
        '''
        Constructor
        '''
        super().__init__(iface, streetsmart)
        super().set_disabled()
        self.is_checked = False
        self.streetsmart.buttonstate.panorama_viewer_opened.connect(
            self.set_enabled)
        self.streetsmart.buttonstate.panorama_viewer_closed.connect(
            self.set_disabled)

    @staticmethod
    def icon_path():
        '''
        Path for the icon
        '''
        return ':/plugins/street_smart/resources/mActionAllEdits.svg'

    def text(self):
        '''
        Text for the command to show
        '''
        return super().tr("Start Measure")

    def parent(self):
        '''
        Parent
        '''
        return self.iface.mainWindow()

    # TODO: create a checkedabstractcommand and move this code into it. This
    # command and add_overlay_command both are childeren.
    def __set_action_state(self):
        """ Toggles the state of the action """
        action = self.action
        if action:
            action.setCheckable(True)
            action.setChecked(not self.is_checked)
            self.is_checked = not self.is_checked

    def callback(self):
        '''
        Code to execute when command is clicked
        '''
        self.__set_action_state()
        if self.is_checked:
            active_layer = self.iface.activeLayer()
            is_vector_layer = isinstance(active_layer, QgsVectorLayer)
            #if not is_vector_layer:
                #QMessageBox.information(None, "Information", "Please start Editing on a vector Layer first") 
                #return
            if (is_vector_layer and active_layer.isEditable()):
                feature_type = self.streetsmart.get_vectorlayer_feature_type(active_layer)  # pylint: disable=line-too-long
                self.__send_start_measure(feature_type)
                self.iface.currentLayerChanged.connect(
                    self.streetsmart.current_layer_changed)
            else:
                QMessageBox.information(None, "Information", "Please start Editing on a vector Layer first") 
            #return
        else:
            
            self.streetsmart.sendToViewer("stopmeasure")
         
            try:
                self.iface.currentLayerChanged.disconnect(
                    self.streetsmart.current_layer_changed)
            except Exception:
                print("Error disconnecting")

    @log(logging.DEBUG)
    def __send_start_measure(self, measure_type):
        '''
        Send measure message to Panorama Viewer
        '''
        msg = "startmeasure|" + measure_type
        self.streetsmart.sendToViewer(msg)
