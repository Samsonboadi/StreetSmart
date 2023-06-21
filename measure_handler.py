'''
Measure Module

To run standalone: set env variable PYTHONHOME
set PYTHONHOME = C:\\PROGRA~1\\QGIS3~1.4\\apps\\Python37

Run with python at C:\\PROGRA~1\\QGIS3~1.4\\apps\\Python37
C:\\PROGRA~1\\QGIS3~1.4\\apps\\Python37\\python.exe measure_handler.py

'''
import json
import sys
import site
import unittest
from unittest.mock import Mock

DIRS = [r'C:/PROGRA~1/QGIS3~1.4/apps/qgis-ltr/./python']
for d in DIRS:
    site.addsitedir(d)

# pylint: disable=import-error, wrong-import-position
from qgis.core import (   # noqa: E402, F401
                       QgsCoordinateTransform,
                       QgsFields,
                       QgsGeometry)
from qgis.core import (QgsFeature,  # noqa: E402, F401
                       QgsWkbTypes,
                       QgsMapLayer)
# pylint: enable= wrong-import-position
if __name__ == '__main__':
    from logger import Logger
else:
    try:
        from .logger import Logger
    except ImportError:
        from logger import Logger

logger = Logger(__name__).get()  # pylint: disable=invalid-name


class CreateMeasurement():
    '''
    Class for Create Measure Command
    '''
    def __init__(self, iface):
        '''
        Constructor
        '''
        self.iface = iface

    def _get_active_layer(self) -> QgsMapLayer:
        ''' Get active layer '''
        print("Active layer: %s", self.iface.activeLayer())
        logger.debug("Active layer: %s", self.iface.activeLayer())
        print("Active layer name: %s", self.iface.activeLayer().name())
        logger.debug("Active layer name: %s", self.iface.activeLayer().name())
        return self.iface.activeLayer()

    @staticmethod
    def _create_new_feature(vectorlayer):
        ''' Create an empty Feature '''
        return QgsFeature(vectorlayer.fields())

    @staticmethod
    def _save_feature_with_undo(vectorlayer, feature):
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

    @staticmethod
    def _update_featuregeometry_with_undo(vectorlayer, fid, geometry):
        ''' Update Feature with undo '''
        print("beginEditComand")
        vectorlayer.beginEditCommand("Update Measurement")

        print("change geometry for feature {}".format(fid))
        logger.debug("change geometry for feature %s", fid)
        if not vectorlayer.changeGeometry(fid, geometry,
                                          skipDefaultValue=False):
            print("DestroyEditCommand")
            vectorlayer.destroyEditCommand()
        else:
            print("EndEditCommand")
            vectorlayer.endEditCommand()

    def _refresh(self, layer):
        ''' Refresh layer '''
        if self.iface.mapCanvas().isCachingEnabled():
            layer.triggerRepaint()
        else:
            self.iface.mapCanvas().refresh()

    def _create_feature_with_geometry(self, active_layer, geometry):
        ''' Create a feature for the given layer with the given geometry '''
        feature = self._create_new_feature(active_layer)
        feature.setGeometry(geometry)

        return feature

    def update_feature(self, feature, new_geometry):
        ''' Change the geometry of an existing feature '''
        active_layer = self._get_active_layer()
        self._update_featuregeometry_with_undo(active_layer, feature.id(),
                                               new_geometry)
        self._refresh(active_layer)

    @staticmethod
    def __geometry_is_valid_for_current_layer(feature_geometry,
                                              layer_geometry_type):
        ''' Returns true if geometry types correspond and the geometry
        is valid.
        '''

        if not feature_geometry:
            print("No geometry")
            return False

        print(feature_geometry.type())
        print(layer_geometry_type)

        if feature_geometry.type() == layer_geometry_type:
            print("Geometry types are correct")
            if layer_geometry_type == 0:  # POINT
                return True
            if layer_geometry_type == 1:  # POLYLINE
                print("Length: ", feature_geometry.length())
                return feature_geometry.length() > 0
            if layer_geometry_type == 2:  # POLYGON
                print("Area: ", feature_geometry.area())
                return feature_geometry.area() > 0

        print("No valid layer geometry: ", layer_geometry_type,
              " for geometry ", feature_geometry.type)
        return False

    def create_feature(self, geometry):
        ''' Create a feature with the given geometry '''
        print("Start Create Feature")
        print(geometry)
        logger.debug("Start Create Feature")
        active_layer = self._get_active_layer()
        layer_geometry_type = active_layer.geometryType()
        print("Layer Geometry Type ", layer_geometry_type)
        print("Layer Geometry Type ",
              QgsWkbTypes.geometryDisplayString(layer_geometry_type))
        if geometry:
            print("Geometry Geometry Type ", geometry.type())
            print("Geometry Geometry Type ",
                  QgsWkbTypes.geometryDisplayString(geometry.type()))

        if not self.__geometry_is_valid_for_current_layer(geometry,
                                                          layer_geometry_type):
            print("No valid geometry for the selected layer")
            return None

        feature = self._create_feature_with_geometry(active_layer, geometry)
        self._save_feature_with_undo(active_layer, feature)
        self._refresh(active_layer)

        return feature


class GeometryParser():
    ''' Geometry methods '''
    def create_geometry_from_array(self, geometry_type, geometry_array):
        ''' Create a geometry from the WKT '''

        wkt = self.create_wkt(geometry_type, geometry_array)
        geometry = QgsGeometry.fromWkt(wkt)
        return geometry

    @staticmethod
    def create_point_as_string(coordinate):
        ''' rt '''
        return " ".join(map(str, coordinate))

    def create_point_as_wkt(self, coordinate):
        ''' rt '''
        # pylint: disable=invalid-name
        p = self.create_point_as_string(coordinate)
        return "POINT ({})".format(p)

    def create_linestring_as_string(self, coordinates):
        ''' xxx '''
        point_list = [self.create_point_as_string(c) for c in coordinates]
        return "({})".format(",".join(point_list))

    def create_linestring_as_wkt(self, coordinates):
        ''' xxx '''
        return "LINESTRING {}".format(
            self.create_linestring_as_string(coordinates))

    def create_polygon_as_wkt(self, coordinates):
        ''' cc '''
        linestrings = [self.create_linestring_as_string(line)
                       for line in coordinates]
        return "POLYGON ({})".format(",".join(linestrings))

    def create_wkt(self, geometry_type, point_collection):
        ''' x '''
        if point_collection is None:
            return None

        geometry_type = geometry_type.upper()
        if geometry_type == 'POINT':
            return self.create_point_as_wkt(point_collection)

        if geometry_type == 'LINESTRING':
            return self.create_linestring_as_wkt(point_collection)

        if geometry_type == 'POLYGON':
            return self.create_polygon_as_wkt(point_collection)

        logger.error("%s is an invalid geometrytype", geometry_type)
        return None


class MeasureHandler():  # pylint: disable=too-few-public-methods
    ''' Class handling the Measurements '''
    def __init__(self, iface, to_crs):
        self.__current_measurement_id = None
        self.__current_geometry = None
        self.__iface = iface
        self.__create_feature = CreateMeasurement(self.__iface)
        self.__feature = None

    def handle(self, measure):
        '''Handles a change in viewer measurement.'''
        logger.debug("Handle measure: %s", measure)
        try:
            measure = json.loads(measure)
        except json.JSONDecodeError as e:
            print("Error loading measurement json {}".format(e))
            logger.exception("Error loading measurement json")
            return

        measure_feature = measure['features'][0]
        id_measurement = measure_feature['properties']['id']
        geometry_type_measurement = measure_feature['geometry']['type']
        geometry_measurement = measure_feature['geometry']['coordinates']
        geometry_parser = GeometryParser()
        current_geometry = geometry_parser.create_geometry_from_array(
            geometry_type_measurement, geometry_measurement)
        print("Previous measurement id {}"
              .format(self.__current_measurement_id))
        print("New measurement id {}".format(id_measurement))

        if self.__current_measurement_id == id_measurement:
            print("Same Measurement ID -> Update feature {}"
                  .format(self.__feature.id()))
            self.__create_feature.update_feature(self.__feature,
                                                 current_geometry)
        else:
            print("Other Measurement ID -> Create new Feature")
            self.__feature = self.__create_feature.create_feature(
                current_geometry)
            if self.__feature is None:
                return

        self.__current_measurement_id = id_measurement
        self.__current_geometry = current_geometry

    @property
    def current_measurement_id(self):
        ''' Current Measurement ID '''
        return self.__current_measurement_id

    @property
    def current_geometry(self):
        ''' Returns current geometry '''
        return self.__current_geometry


class TestMeasureHandler(unittest.TestCase):
    ''' Tests '''

    def test_geometry_geometrytype_empty(self):
        ''' Test '''
        measure = {
            'features': [
                {
                    'properties': {'id': '1'},
                    'geometry': {'type': '', 'coordinates': ''}
                }], 'crs': {'properties': {'name': ''}}}
        measure_json = json.dumps(measure)
        iface = Mock()
        iface.activeLayer.return_value = Mock()
        iface.activeLayer().geometryType.return_value = 0
        iface.activeLayer().fields.return_value = QgsFields()
        handler = MeasureHandler(iface, None)
        handler.handle(measure_json)
        self.assertTrue(handler.current_geometry.isEmpty())

    def test_geometry_geometrytype_invalid(self):
        ''' Test '''
        measure = {
            'features': [
                {
                    'properties': {'id': '1'},
                    'geometry': {'type': 'PP', 'coordinates': ''}
                }], 'crs': {'properties': {'name': ''}}}
        measure_json = json.dumps(measure)
        iface = Mock()
        iface.activeLayer.return_value = Mock()
        iface.activeLayer().geometryType.return_value = 0
        iface.activeLayer().fields.return_value = QgsFields()
        handler = MeasureHandler(iface, None)
        handler.handle(measure_json)
        self.assertTrue(handler.current_geometry.isEmpty())

    def test_geometry_empty_point(self):
        ''' Test '''
        measure = {
            'features': [
                {
                    'properties': {'id': '1'},
                    'geometry': {'type': 'Point', 'coordinates': None}
                }], 'crs': {'properties': {'name': ''}}}
        measure_json = json.dumps(measure)
        iface = Mock()
        iface.activeLayer.return_value = Mock()
        iface.activeLayer().geometryType.return_value = 0
        iface.activeLayer().fields.return_value = QgsFields()
        handler = MeasureHandler(iface, None)
        handler.handle(measure_json)
        self.assertTrue(handler.current_geometry.isEmpty())

    def test_geometry_valid_point(self):
        ''' Test '''
        measure = {
            'features': [
                {
                    'properties': {'id': '1'},
                    'geometry': {'type': 'Point',
                                 'coordinates': [10, 20, 30]}
                }], 'crs': {'properties': {'name': ''}}}
        measure_json = json.dumps(measure)
        iface = Mock()
        iface.activeLayer.return_value = Mock()
        iface.activeLayer().geometryType.return_value = 0
        iface.activeLayer().fields.return_value = QgsFields()
        handler = MeasureHandler(iface, None)
        handler.handle(measure_json)
        self.assertTrue(handler.current_geometry
                        .equals(QgsGeometry.fromWkt('POINT (10 20 30)')))

    def test_geometry_valid_linestring(self):
        ''' Test '''
        measure = {
            'features': [
                {
                    'properties': {'id': '1'},
                    'geometry': {'type': 'Linestring',
                                 'coordinates': [[10, 20, 30], [20, 30, 40]]}
                }], 'crs': {'properties': {'name': ''}}}
        measure_json = json.dumps(measure)
        iface = Mock()
        iface.activeLayer.return_value = Mock()
        iface.activeLayer().geometryType.return_value = 0
        iface.activeLayer().fields.return_value = QgsFields()
        handler = MeasureHandler(iface, None)
        handler.handle(measure_json)
        print(handler.current_geometry)
        print(QgsGeometry.fromWkt('LINESTRING (10 20 30, 20 30 40)'))
        self.assertTrue(handler.current_geometry
                        .equals(QgsGeometry.fromWkt(
                            'LINESTRING (10 20 30, 20 30 40)')))

    def test_geometry_valid_polygon(self):
        ''' Test '''
        measure = {
            'features': [
                {
                    'properties': {'id': '1'},
                    'geometry': {'type': 'Polygon',
                                 'coordinates': [[[10, 20, 30], [20, 30, 40], [15, 30, 50], [10, 20, 30]]]}  # noqa: E501 pylint: disable=line-too-long
                }], 'crs': {'properties': {'name': ''}}}
        measure_json = json.dumps(measure)
        iface = Mock()
        iface.activeLayer.return_value = Mock()
        iface.activeLayer().geometryType.return_value = 0
        iface.activeLayer().fields.return_value = QgsFields()
        handler = MeasureHandler(iface, None)
        handler.handle(measure_json)
        self.assertTrue(
            handler.current_geometry
            .equals(QgsGeometry
                    .fromWkt(
                        'POLYGON ((10 20 30, 20 30 40, 15 30 50, 10 20 30))')))

    def test_current_measurement_id(self):
        ''' Test '''
        measure = {
            'features': [
                {
                    'properties': {'id': '1'},
                    'geometry': {'type': '', 'coordinates': ''}
                }], 'crs': {'properties': {'name': ''}}}
        measure_json = json.dumps(measure)
        iface = Mock()
        iface.activeLayer.return_value = Mock()
        iface.activeLayer().geometryType.return_value = 0
        iface.activeLayer().fields.return_value = QgsFields()
        handler = MeasureHandler(iface, None)
        handler.handle(measure_json)
        self.assertEqual(handler.current_measurement_id, '1')
        handler.handle(measure_json)
        self.assertEqual(handler.current_measurement_id, '1')
        measure['features'][0]['properties']['id'] = '2'
        measure_json = json.dumps(measure)
        handler.handle(measure_json)
        self.assertEqual(handler.current_measurement_id, '2')

    def test_current_geometry_mustchange(self):
        ''' Test '''
        measure = {
            'features': [
                {
                    'properties': {'id': '1'},
                    'geometry': {'type': 'Point',
                                 'coordinates': [11, 21, 31]}
                }], 'crs': {'properties': {'name': ''}}}
        measure_json = json.dumps(measure)
        iface = Mock()
        iface.activeLayer.return_value = Mock()
        iface.activeLayer().geometryType.return_value = 0
        iface.activeLayer().fields.return_value = QgsFields()
        handler = MeasureHandler(iface, None)
        handler.handle(measure_json)
        self.assertTrue(handler.current_geometry
                        .equals(QgsGeometry.fromWkt('POINT (11 21 31)')))
        measure['features'][0]['geometry']['coordinates'] = [20, 30, 40]
        measure_json = json.dumps(measure)
        handler.handle(measure_json)
        self.assertTrue(handler.current_geometry
                        .equals(QgsGeometry.fromWkt('POINT (20 30 40)')))
        measure['features'][0]['properties']['id'] = '2'
        measure['features'][0]['geometry']['coordinates'] = [30, 40, 50]
        measure_json = json.dumps(measure)
        handler.handle(measure_json)
        self.assertTrue(handler.current_geometry
                        .equals(QgsGeometry.fromWkt('POINT (30 40 50)')))


class TestGeometryParser(unittest.TestCase):
    ''' Tests '''
    def test_point_as_string(self):
        ''' Test '''
        point = [10, 20, 30]
        handler = GeometryParser()
        point_wkt = handler.create_point_as_string(point)
        self.assertEqual(point_wkt, '10 20 30')

    def test_point_as_wkt(self):
        ''' Test '''
        point = [12, 22, 32]
        handler = GeometryParser()
        point_wkt = handler.create_point_as_wkt(point)
        self.assertEqual(point_wkt, 'POINT (12 22 32)')

    def test_linestring_as_wkt(self):
        ''' Test '''
        linestring = [[10, 20, 30], [20, 30, 40], [30, 40, 50]]
        handler = GeometryParser()
        linestring_wkt = handler.create_linestring_as_wkt(linestring)
        self.assertEqual(linestring_wkt,
                         'LINESTRING (10 20 30,20 30 40,30 40 50)')

    def test_polygon_as_wkt(self):
        ''' Test '''
        polygon = [[[10, 20, 30], [20, 30, 40], [30, 40, 50]]]
        handler = GeometryParser()
        polygon_wkt = handler.create_polygon_as_wkt(polygon)
        self.assertEqual(polygon_wkt,
                         'POLYGON ((10 20 30,20 30 40,30 40 50))')

    def test_geometry_degenerate_polygon(self):
        ''' test '''
        geometries = [
            ('Polygon',
             [[[10, 20, 30], [20, 30, 40], [30, 40, 50]]],
             'POLYGON ((10 20 30,20 30 40,30 40 50))',
             'POLYGONZ ((10 20 30, 20 30 40, 30 40 50))'
             ),
            ('Polygon',  # Polygon after 1 point
             [[[10, 20, 30], [10, 20, 30]]],
             'POLYGON ((10 20 30,10 20 30))',
             'POLYGONZ ((10 20 30, 10 20 30))'
             ),
            ('Polygon',  # Polygon after 2 points
             [[[10, 20, 30], [15, 25, 30], [10, 20, 30]]],
             'POLYGON ((10 20 30,15 25 30,10 20 30))',
             'POLYGONZ ((10 20 30, 15 25 30, 10 20 30))'
             ),
            ('Polygon',  # Polygon after 3 points
             [[[10, 20, 30], [15, 25, 30], [20, 30, 30], [10, 20, 30]]],
             'POLYGON ((10 20 30,15 25 30,20 30 30,10 20 30))',
             'POLYGONZ ((10 20 30, 15 25 30, 20 30 30, 10 20 30))'
             ),
        ]

        handler = GeometryParser()
        for geometry in geometries:
            with self.subTest(geometryType=geometry[0]):
                wkt = handler.create_wkt(geometry[0], geometry[1])
                self.assertEqual(wkt, geometry[2])

                qgis_geometry = handler.create_geometry_from_array(geometry[0],
                                                                   geometry[1])
                self.assertEqual(qgis_geometry.asWkt().upper(), geometry[3])

    def test_geometry_degenerate_line(self):
        ''' test '''
        geometries = [
            ('Point',
             [13, 23, 33],
             'POINT (13 23 33)',
             'POINTZ (13 23 33)'
             ),
            ('Linestring',  # After 1 point
             [[10, 20, 30], [10, 20, 30]],
             'LINESTRING (10 20 30,10 20 30)',
             'LINESTRINGZ (10 20 30, 10 20 30)'
             ),
            ('Linestring',  # After 2 points
             [[10, 20, 30], [20, 30, 40]],
             'LINESTRING (10 20 30,20 30 40)',
             'LINESTRINGZ (10 20 30, 20 30 40)'
             ),
            ('Linestring',
             [[10, 20, 30], [20, 30, 40], [30, 40, 50]],
             'LINESTRING (10 20 30,20 30 40,30 40 50)',
             'LINESTRINGZ (10 20 30, 20 30 40, 30 40 50)'
             ),
        ]

        handler = GeometryParser()
        for geometry in geometries:
            with self.subTest(geometryType=geometry[0]):
                wkt = handler.create_wkt(geometry[0], geometry[1])
                self.assertEqual(wkt, geometry[2])

                qgis_geometry = handler.create_geometry_from_array(geometry[0],
                                                                   geometry[1])
                self.assertEqual(qgis_geometry.asWkt().upper(), geometry[3])

    def test_geometry_point(self):
        ''' test '''
        geometries = [
            ('Point',
             [10, 20, 30],
             'POINT (10 20 30)',
             'POINTZ (10 20 30)'
             ),
        ]

        handler = GeometryParser()
        for geometry in geometries:
            with self.subTest(geometryType=geometry[0]):
                wkt = handler.create_wkt(geometry[0], geometry[1])
                self.assertEqual(wkt, geometry[2])

                qgis_geometry = handler.create_geometry_from_array(geometry[0],
                                                                   geometry[1])
                self.assertEqual(qgis_geometry.asWkt().upper(), geometry[3])


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == 't':
            FILENAME = r'test\server.log'
        else:
            FILENAME = sys.argv[1]
    else:
        unittest.main()
        sys.exit()

    with open(FILENAME, 'r') as f:
        MEASURES = f.readlines()

    MEASURES = [measure.strip(r'/n').strip().split('|')[1]
                for measure in MEASURES]
    HANDLER = MeasureHandler(None, None)
    for i in range(10):
        t = (i + 1) * -1
        HANDLER.handle(MEASURES[t])
