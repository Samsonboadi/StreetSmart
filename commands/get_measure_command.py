''' Module for Getting a Measurement from PanoramaViewer '''

from qgis.core import (QgsProject,  # pylint: disable=import-error
                       QgsGeometry,
                       QgsWkbTypes,
                       QgsFeature,
                       QgsVectorLayer,
                       QgsMapLayer)
from PyQt5.QtWidgets import QMessageBox

from ..logger import Logger
from ..street_smart import AbstractCommand

logger = Logger(__name__).get()  # pylint: disable=invalid-name


class GetMeasureCommand(AbstractCommand):
    '''
    Class for Create Measure Command
    '''
    def __init__(self, iface, streetsmart):
        '''
        Constructor
        '''
        super().__init__(iface, streetsmart)

    @staticmethod
    def icon_path():
        '''
        Path for the icon
        '''
        return ':/plugins/street_smart/resources/mActionDuplicateFeature.svg'

    def text(self):
        '''
        Text for the command to show
        '''
        return super().tr("Synchronize Measurements")

    def callback(self):
        '''
        Code to execute when command is clicked
        '''
        self.test_create_feature()

    @staticmethod
    def test_check_layer():
        ''' Test TOC methods '''
        project = QgsProject.instance()
        map_layers = project.mapLayers()
        for layer in map_layers.values():
            if isinstance(layer, QgsVectorLayer):
                if layer.isEditCommandActive():
                    print("Layer {} is currently being edited"
                          .format(layer.name()))
                    logger.debug("Layer %s is currently being edited",
                                 layer.name())
                if layer.isEditable():
                    print("Layer {} is editable"
                          .format(layer.name()))
                    logger.debug("Layer %s is editable",
                                 layer.name())
            else:
                print("layer {} is not an QgsVectorLayer".format(layer.name()))

    def get_active_layer(self) -> QgsMapLayer:
        ''' Get active layer '''
        print("Active layer: %s", self.iface.activeLayer())
        logger.debug("Active layer: %s", self.iface.activeLayer())
        print("Active layer name: %s", self.iface.activeLayer().name())
        logger.debug("Active layer name: %s", self.iface.activeLayer().name())
        return self.iface.activeLayer()

    def is_active_layer_editable(self) -> bool:
        ''' Return if active layer is editable '''
        print("Is active layer editable: ",
              self.get_active_layer().isEditable())
        logger.debug("Is active layer editable: %s",
                     self.get_active_layer().isEditable())
        return self.get_active_layer().isEditable()

    @staticmethod
    def create_point_geometry(around_point):
        ''' Create Point '''
        # pylint: disable=invalid-name
        X = around_point.x()
        Y = around_point.y()
        geometry_wkt = 'POINT ({} {})'.format(X, Y)
        return QgsGeometry.fromWkt(geometry_wkt)

    @staticmethod
    def create_line_geometry(around_point):
        ''' Create Line '''
        # pylint: disable=invalid-name
        x = around_point.x()
        y = around_point.y()
        geometry_wkt = ('MULTILINESTRING (({} {}, {} {}))'
                        .format(x - 10, y - 10, x + 10, y + 10))
        return QgsGeometry.fromWkt(geometry_wkt)

    @staticmethod
    def create_polygon_geometry(around_point):
        ''' Create Polygon '''
        # pylint: disable=invalid-name
        # pylint: disable=invalid-name
        x = around_point.x()
        y = around_point.y()
        geometry_wkt = ('POLYGON (({} {}, {} {}, {} {}, {} {}))'
                        .format(x - 10, y - 10, x + 10, y,
                                x + 10, y + 10, x - 10, y - 10))
        return QgsGeometry.fromWkt(geometry_wkt)

    @staticmethod
    def create_new_feature(vectorlayer):
        ''' Create an empty Feature '''
        return QgsFeature(vectorlayer.fields())

    @staticmethod
    def save_feature(vectorlayer, feature):
        ''' Save Feature '''
        # pylint: disable=unused-variable
        (res, out_features) = vectorlayer.dataProvider().addFeatures([feature])

    @staticmethod
    def save_feature_with_undo(vectorlayer, feature):
        ''' Save Feature with undo '''
        print("beginEditComand")
        vectorlayer.beginEditCommand("Create Feature")

        print("addFeature")
        if not vectorlayer.addFeature(feature):
            print("DestroyEditCommand")
            vectorlayer.destroyEditCommand()
        else:
            print("EndEditCommand")
            vectorlayer.endEditCommand()

    def refresh(self, layer):
        ''' Refresh layer '''
        if self.iface.mapCanvas().isCachingEnabled():
            layer.triggerRepaint()
        else:
            self.iface.mapCanvas().refresh()

    def create_geometry_around_point(self, geometry_type, around_point):
        ''' Create a geometry around the given point '''
        if geometry_type == 0:  # QgsWkbTypes.Point:
            geometry = self.create_point_geometry(around_point)
        elif geometry_type == 1:   # QgsWkbTypes.LineGeometry:
            geometry = self.create_line_geometry(around_point)
        elif geometry_type == 2:  # QgsWkbTypes.Polygon:
            geometry = self.create_polygon_geometry(around_point)
        else:
            geometry = None
        return geometry

    def create_feature_with_geometry(self, active_layer, geometry):
        ''' Create a feature for the given layer with the given geometry '''
        feature = self.create_new_feature(active_layer)
        feature.setGeometry(geometry)

        return feature

    def test_create_feature(self):
        ''' Create simple feature '''
        active_layer = self.get_active_layer()
        if active_layer.isEditable():
            geometry_type = active_layer.geometryType()
            print("Geometry Type ", geometry_type)
            print("Geometry Type ",
                  QgsWkbTypes.geometryDisplayString(geometry_type))
            center_point = self.iface.mapCanvas().center()
            geometry = self.create_geometry_around_point(geometry_type,
                                                         center_point)
            feature = self.create_feature_with_geometry(active_layer, geometry)
            before_save_fid = feature.id()
            self.save_feature_with_undo(active_layer, feature)
            after_save_fid = feature.id()
            self.refresh(active_layer)
            print("FID {} -> {}".format(before_save_fid, after_save_fid))
        else:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Information)
            msg.setText("Geselecteerde laag is niet editeerbaar")
            msg.setWindowTitle("Warning")
            msg.setDetailedText("Geselecteerde laag is {}".format(active_layer.name()))
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec_()

    def send_get_measure(self):
        '''
        Send get measure message to Panorama Viewer
        '''
        print("sendGetMeasure")
        logger.debug("sendGetMeasure")
        msg = "getmeasure"
        self.streetsmart.sendToViewer(msg)

    def parent(self):
        '''
        Parent
        '''
        return self.iface.mainWindow()
