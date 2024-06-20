""" Module for Add Overlay Command """

# pylint: disable=wrong-import-position
import logging
import json
from shapely.geometry import shape
from PyQt5.QtWidgets import QMessageBox

from geojson.feature import Feature  # noqa
from PyQt5.QtXml import (QDomDocument)  # noqa pylint: disable=no-name-in-module
from qgis.core import (QgsFeatureRequest,  # noqa pylint: disable=import-error
                       QgsJsonExporter,
                       QgsPointXY,
                       QgsProject,
                       QgsRectangle,
                       QgsVectorLayer,
                       QgsCircle,
                       )

from ..logger import Logger  # noqa
from ..logger import log  # noqa
from ..settings import Settings  # noqa
from ..sld import create_sld_description  # noqa
from ..street_smart import AbstractCommand  # noqa
from ..geometry_utils import (transform_point,
                              transform_json_feature_collection,
                              simplify_json_feature_collection)
from ..utils import (convert_distance)
#from qgis.core import QgsMessageLog
logger = Logger(__name__).get()


def remove_newline(message: str) -> str:
    """ Remove newline from a string """
    return "".join([l.strip() for l in message.splitlines()])


@log(logging.DEBUG, print_args=True, print_return=True)
def _loop_toc(scale):
    """
    Loop over all layers in the table of contents to find visible layers
    """
    cyclo_layer_name = Settings.getInstance().getRecordingLayerName()
    root_toc = QgsProject.instance().layerTreeRoot()
    checked_layers = root_toc.checkedLayers()
    visible_layers = [layer for layer in checked_layers
                      if layer.isInScaleRange(scale)
                      and not cyclo_layer_name.lower() in layer.name().lower()
                      and isinstance(layer, QgsVectorLayer)]

    return visible_layers


def _get_sld_for_layer(layer: QgsVectorLayer) -> str:
    """ Get SLD for symbology layer """
    temp_doc = QDomDocument()
    element = temp_doc.createElement("sld")
    error = ""
    if layer.writeSld(element, temp_doc, error, {}):
        temp_doc.appendChild(element)

    if not error:
        return create_sld_description(temp_doc)

    logger.error("Error fetching SLD for layer %s. Error: %s",
                 layer.name(), error)
    return ''


class ExplodeGeometryCollection:
    """Explodes a feature with a geometry collection into several simple
    features
    """
    @staticmethod
    def _create_shapely_geometry(geojson_geometry):
        """Creates a shapely shape from the Well Known Text geometry"""
        return shape(geojson_geometry)

    @staticmethod
    def _geometry_as_json(shapely_geometry):
        """Converts a shapely geometry to geoJSON"""
        geometry = Feature(geometry=shapely_geometry)
        return geometry.geometry

    def explode_geometry_collection(self, geojson_geometry_collection):
        """Creates a list of simple geometries"""
        geometry = self._create_shapely_geometry(geojson_geometry_collection)
        return geometry

    def explode_feature(self, feature_as_json: str):
        """Create a list of features each with the original attributes and a
        simple geometry"""
        feature = json.loads(feature_as_json)
        geometry = self._create_shapely_geometry(feature["geometry"])
        exploded_features = []
        
        if hasattr(geometry, "geoms"):
            # Iterate over each geometry within the MultiPolygon
            for simple_geometry in geometry.geoms:
                new_feature = json.loads(feature_as_json)
                new_feature["geometry"] = self._geometry_as_json(simple_geometry)
                exploded_features.append(new_feature)
        else:
            exploded_features.append(json.loads(feature_as_json))

        return exploded_features


    def explode_feature_collection(self,
                                   featurecollection_as_json: str) -> str:
        """Creates a list of features each with the attributes of the original
        feature and with a simple geometry

        :param featurecollection_as_json: FeatureCollection as GeoJSON string

        :returns: Another FeatureCollection as GeoJSON string
        """
        featurecollection = json.loads(featurecollection_as_json)
        exploded_features = []
        for feature in featurecollection["features"]:
            features = self.explode_feature(json.dumps(feature))
            exploded_features.extend(features)
        exploded_feature_collection = {}
        exploded_feature_collection["type"] = "FeatureCollection"
        exploded_feature_collection["features"] = exploded_features
        return json.dumps(exploded_feature_collection)


@log(logging.DEBUG, print_return=True, print_args=True)
def _transform_coordinates(json_features: str, from_srs_id, to_srs_id):
    """Transform the coordinates for the features"""
    if json_features is None:
        return None
    if from_srs_id is None or to_srs_id is None:
        return json_features

    json_features = json.loads(json_features)
    json_features = transform_json_feature_collection(json_features,
                                                      from_srs_id, to_srs_id)
    return json.dumps(json_features)


@log(logging.DEBUG, print_return=True, print_args=True)
def _simplify_featuregeometry(json_features: str, tolerance):
    """Transform the coordinates for the features"""
    if json_features is None:
        return None
    json_features = json.loads(json_features)
    json_features = simplify_json_feature_collection(json_features,
                                                     tolerance)
    return json.dumps(json_features)


@log(logging.DEBUG, print_return=True, print_args=True)
def _get_features_as_json(layer: QgsVectorLayer,
                          point: QgsPointXY,
                          width: int) -> str:
    """Returns a GeoJSON string for all features in the layer around a point

    A feature will be duplicated if the original feature has a collection as
    geometry (e.g., multipoint, multiline,...). The geometry for each duplicated
    feature is a simple geometry from the collection.

    :param layer: QgsVectorLayer for which the features will be returned
    :param point: QgsPointXY around where the features will be searched for
    :param width: Width of the bounding box in which features will be searched for

    :returns: a GeoJSON featurecollection string if features are found,
        otherwise None
    """
    json_features = _get_all_layer_features_as_json(layer, point, width)
    if _has_features(json_features):
        exp = ExplodeGeometryCollection()
        exploded_json_features = exp.explode_feature_collection(json_features)
        return exploded_json_features

    return ""


@log(logging.DEBUG, print_return=True, print_args=True)
def _get_all_layer_features_as_json(layer: QgsVectorLayer,
                                    point: QgsPointXY,
                                    width: int) -> str:
    """Returns a GeoJSON string for all features in the layer around a point

    A feature will be duplicated if the original feature has a collection as
    geometry (e.g., multipoint, multiline,...). The geometry for each duplicated
    feature is a simple geometry from the collection.

    :param layer: QgsVectorLayer for which the features will be returned
    :param point: QgsPointXY around where the features will be searched for
    :param width: Width of the bounding box in which features will be searched for

    :returns: a GeoJSON featurecollection string if features are found,
        otherwise None
    """
    rectangle = QgsRectangle.fromCenterAndSize(point, width, width)
    #cirlce = QgsCircle.fromCenterDiameter(point, width)

    _feature_iterator = layer.getFeatures(QgsFeatureRequest(rectangle))

    json_exporter = QgsJsonExporter()
    json_features = json_exporter.exportFeatures(_feature_iterator)

    return json_features


def _has_features(json_featurecollection: str) -> bool:
    """Returns True if the featurecollection has features

    :param json_featurecollection: FeatureCollection GeoJSON string

    :returns: True if the featurecollection contains features; otherwise, False
    """
    featurecollection = json.loads(json_featurecollection)

    return len(featurecollection["features"]) > 0


class AddOverlayCommand(AbstractCommand):
    """
    Class for Add Overlay Command
    """
    def __init__(self, iface, streetsmart):
        """
        Constructor
        """
        super().__init__(iface, streetsmart)
        super().set_disabled()
        self.is_checked = False
        self.streetsmart.buttonstate.panorama_viewer_opened.connect(
            self.set_enabled)
        self.streetsmart.buttonstate.panorama_viewer_closed.connect(
            self.set_disabled)
        self.streetsmart.buttonstate.cone_moved.connect(self.on_cone_moved)

    @log(logging.DEBUG)
    def on_cone_moved(self):
        """ Resends the overlays when the cone is moved """
        if self.is_checked:
            self.sendMessageToRemoveOverlay()
            self.__send_overlay()

    @staticmethod
    def icon_path():
        """
        Path for the icon
        """
        return ':/plugins/street_smart/resources/overlay.svg'

    def text(self):
        """
        Text for the command to show
        """
        return super().tr("Add Overlay layers to Panorama Viewer")

    def parent(self):
        """
        Parent
        """
        return self.iface.mainWindow()

    @log(logging.DEBUG)
    def __send_overlay(self):
        """ Creates json for the features on all visible layers"""
        try:

            if not self.is_checked:
                self.sendMessageToRemoveOverlay()
                return

            search_radius = Settings.getInstance().get_overlay_search_radius()
            cone = self.streetsmart.buttonstate.previous_cone

            # Cone can be None if panorama view has no valid recordings
            if not cone or not cone.cone:
                return

            cone_point = cone.cone.getPoint(0)
            cone_srs = cone.srs
            for visible_layer in _loop_toc(self.iface.mapCanvas().scale()):
                layer_srs = visible_layer.sourceCrs()
                layer_srs_id = layer_srs.authid()
                layer_map_units = layer_srs.mapUnits()
                transformed_cone_point = transform_point(cone_point, cone_srs,
                                                        layer_srs_id)
                transformed_search_radius = convert_distance(search_radius, 0,
                                                            layer_map_units)
                json_features = _get_features_as_json(visible_layer,
                                                    transformed_cone_point,
                                                    transformed_search_radius)
                #QgsMessageLog.logMessage(str(transformed_cone_point), "transformed_cone_point")
                #QgsMessageLog.logMessage(str(transformed_search_radius), "transformed_search_radius")
                if json_features:
                    json_features = _transform_coordinates(json_features,
                                                        layer_srs_id,
                                                        cone_srs.authid())
                    # 0.01 seems a good value.
                    # Shapely is a 2D library, simplify does not work on a 3D object.
                    # Remove simplify entirely
                    # tolerance = convert_distance(0.01, 0, layer_map_units)
                    # json_features = _simplify_featuregeometry(json_features,
                    #                                           tolerance)

                    sld_text = _get_sld_for_layer(visible_layer)
                    if sld_text is None:
                        sld_text = ''

                    # Escape the slash character
                    json_features = json_features.replace(r"/", "__")
                    sld_text = sld_text.replace(r"/", "__")
                    self.sendMessageToAddOverlay(json_features,
                                                visible_layer.name(),
                                                cone_srs.authid(), sld_text,
                                                'FF0000')
        except Exception:
            QMessageBox.information(None, "Information", "Something happenend") 

    def __set_action_state(self):
        """ Toggles the state of the action """
        action = self.action
        if action:
            action.setCheckable(True)
            action.setChecked(not self.is_checked)
            self.is_checked = not self.is_checked

    def callback(self):
        """ Code to execute when command is clicked

        Previous_cone must be set.
        """
        visible_layer = _loop_toc(self.iface.mapCanvas().scale())
        cone = self.streetsmart.buttonstate.previous_cone
        if (len(visible_layer)<= 0 ) or cone == None or cone.cone ==None:
            QMessageBox.information(None, "Information", "There are no vector layers to be added to the viewer\n or Panoramer viewer not started yet") 
            return
        else:
            self.__set_action_state()
            self.__send_overlay()

    def sendMessageToRemoveOverlay(self):
        """ Send remove overlay to viewer
        """
        msg = ("removeoverlay")
        self.streetsmart.sendToViewer(msg)

    @log(logging.DEBUG, print_args=True)
    def sendMessageToAddOverlay(self, json_features: str, layer_name: str,
                                srs: str, sld_text: str, color: str):
        """
        Send overlay message to Panorama Viewer
        """
        json_wo_newlines = remove_newline(json_features)
        sld_wo_newlines = remove_newline(sld_text)
        msg = ("overlay|" + json_wo_newlines + "/" + layer_name + "/" + srs
               + "/" + sld_wo_newlines + "/" + color + '\n')
        self.streetsmart.sendToViewer(msg)
