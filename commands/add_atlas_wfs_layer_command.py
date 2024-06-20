""" Add Atlas WFS layer to QGIS Project """
import logging
from qgis.core import (QgsProject,  # pylint: disable=import-error
                       QgsVectorLayer, QgsDataSourceUri,QgsVectorFileWriter, QgsApplication,QgsMessageLog)
import os
from ..logger import Logger
from ..logger import log
from ..settings import Settings
from ..street_smart import AbstractCommand

RECORDING_LAYER_NAME = Settings.getInstance().getRecordingLayerName()


class AddAtlasWFSLayerCommand(AbstractCommand):
    '''
    Class for Add WFS Layer Command
    '''
    def __init__(self, iface, streetsmart):
        '''
        Constructor
        '''
        super().__init__(iface, streetsmart)
        port = streetsmart.log_port
        self.logger = Logger(__name__, port).get()

    @staticmethod
    def icon_path():
        '''
        Path for the icon
        '''
        return ':/plugins/street_smart/resources/mActionAdd.svg'

    def text(self):
        '''
        Text for the command to show
        '''
        return super().tr(u'Add Atlas Recording WFS')

    def parent(self):
        '''
        Parent
        '''
        return self.iface.mainWindow()

    def callback(self):
        '''
        Code to execute when command is clicked
        '''
        if self.are_usersettings_available():
            self.add_wfs_layer()
            self.streetsmart.buttonstate.atlas_added = True
        else:
            self.show_set_settings_message_box()

    @log()
    def add_wfs_layer(self):
        '''add'''
        recording_uri = self.create_wfs_definition()

        self._add_layer_to_legend(recording_uri)

    @staticmethod
    def _add_layer_to_legend(recording_uri):
        '''add'''

        for lyr in QgsProject.instance().mapLayers().values():
            if lyr.name() == "CycloMedia Recording":
                QgsProject.instance().removeMapLayers([lyr.id()]) 

        root = QgsProject.instance().layerTreeRoot()
        rec_layer = QgsVectorLayer(recording_uri.uri(),
                                   RECORDING_LAYER_NAME, "WFS")
        rec_layer.setScaleBasedVisibility(True)
        rec_layer.setMinimumScale(5000)
        QgsProject.instance().addMapLayer(rec_layer, False)
        root.insertLayer(0, rec_layer)

  



    @staticmethod
    @log(logging.DEBUG, print_return=True)
    def __get_settings():
        """Returns the plugin settings."""
        return_value = Settings.getInstance().settings
        return return_value



    @log(logging.DEBUG, print_return=True)
    def create_wfs_definition(self):
        ''' Create definition for the Atlas Recording WFS '''
        settings = self.__get_settings()
        uri = settings[Settings.RECORDING_WFS_LOCATION].value
        get_filter_parameters = Settings.getInstance().getAtlasWFSFilter()
        if not get_filter_parameters:
            get_filter_parameters = "expiredAt is null"
        ds_uri = QgsDataSourceUri(uri)
        ds_uri.setParam('url', uri)
        ds_uri.setParam('typename', 'atlas:Recording')
        ds_uri.setParam('srsname', Settings.getInstance().getAtlasSRSName())
        ds_uri.setParam("username",
                        settings[Settings.USERNAME].value)
        ds_uri.setParam("password",
                        settings[Settings.PASSWORD].value)
        print(Settings.getInstance().getAtlasSRSName())
        # ds_uri.setParam("authcfg", Settings.getInstance().getAuthcfg())
        ds_uri.setParam("filter", get_filter_parameters)
        ds_uri.setParam('restrictToRequestBBOX', '1')
        ds_uri.setParam('InvertAxisOrientation', '1')
        ds_uri.setParam('version', '1.1.0')

        return ds_uri
