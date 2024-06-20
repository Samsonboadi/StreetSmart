""" Cone Handler module """
import math
import logging
from qgis.PyQt.QtGui import QColor  # pylint: disable=import-error
from qgis.core import (  # pylint: disable=import-error
    QgsPointXY, QgsGeometry, QgsProject, QgsCoordinateTransform,
    QgsCoordinateReferenceSystem,Qgis,QgsWkbTypes)
from qgis.gui import (  # pylint: disable=import-error
    QgsRubberBand)
try:
    from .settings import Settings
    from .logger import Logger
    from .logger import log
    from .geometry_utils import (transform_coordinate)
    from .utils import (convert_distance)
    from .street_smart import StreetSmart_Cone
except:
    from settings import Settings
    from logger import Logger
    from logger import log
    from geometry_utils import (transform_coordinate)
    from utils import (convert_distance)
    from street_smart import StreetSmart_Cone

CONE_BORDER_WIDTH = 3

logger = Logger(__name__).get()

class ConeHandler():
    """ Cone Handler """

    # Class variable
    previous_cone = None

    def __init__(self, streetsmart, cone_height):
        self.streetsmart = streetsmart
        self.iface = streetsmart.iface
        self.cone_height = cone_height
        self.cone = None

    def handle(self, args):
        """ Handle cone command """
        # pylint: disable=unused-variable, invalid-name
        if args is None:
            self.__remove_previous_cone()
        else:
            project_srs = self.iface.mapCanvas().mapSettings().destinationCrs()
            self.cone = StreetSmart_Cone(None, project_srs)
            r_id, x, y, z, srs, rot, r, g, b, a = args.split(',')
            color = QColor(int(r), int(g), int(b), int(float(a)))
            transformed_point = self._transform_cone_point(float(x), float(y),
                                                           srs, project_srs)
            self.create_and_draw_cone(transformed_point,
                                      rot, color)
            
    def center_map(self,point):

        # Convert the QgsPointXY to a QgsGeometry object
        geometry_feature = QgsGeometry.fromPointXY(point)

        # Get the geometry of the clicked feature
        #geometry = geometry_feature.geometry.geometry()
        # Get the center point of the feature's bounding box
        center_point = geometry_feature.boundingBox().center()

        # Set the center of the map canvas to the center point
        #canvas.setCenter(center_point)
        self.iface.mapCanvas().setCenter(center_point)

    @log(logging.DEBUG, print_args=True, print_return=True)
    def _transform_cone_point(self, x, y, srs, to_srs):
        """Transform coordinate to mapCanvas crs"""
        # from_srs = QgsCoordinateReferenceSystem(srs)
        transformed_point = transform_coordinate(x, y, srs, to_srs)
        # project = QgsProject.instance()
        # transform = QgsCoordinateTransform(from_srs, to_srs, project)
        # transformed = transform.transform(x, y)
        # return transformed
        return transformed_point

    def _create_cone_polyline(self, point):
        """ Create the cone from a top point """
        # height = self.cone_height
        canvas_units = self.iface.mapCanvas().mapUnits()
        height = convert_distance(self.cone_height, 0, canvas_units)
        angle = Settings.getInstance().get_cone_angle()
        cone_top_x = point.x()
        cone_top_y = point.y()

        if float(angle) > 89:
            angle = 89
        h_fov = math.radians(angle)  # Should come from recording
        scale = self.iface.mapCanvas().scale()
        tana = math.tan(h_fov)

        real_height = height * scale
        real_width = tana * real_height

        points = [[QgsPointXY(cone_top_x, cone_top_y),
                   QgsPointXY(cone_top_x - real_width,
                              cone_top_y + real_height),
                   QgsPointXY(cone_top_x + real_width,
                              cone_top_y + real_height)]]
        return points

    def __remove_previous_cone(self):
        """ Remove previous cone """
        previous_cone = self.streetsmart.buttonstate.previous_cone
        if previous_cone is not None:
            self.iface.mapCanvas() .scene().removeItem(
                previous_cone.cone)
                # previous_cone)


    def create_and_draw_cone(self, point, orientation, color):
        """ Draw cone on canvas """

        self.__remove_previous_cone()
        points = self._create_cone_polyline(point)
        self.center_map(point)

        # Rotate cone
        cone_geometry = QgsGeometry.fromPolygonXY(points)
        cone_geometry.rotate(float(orientation), QgsPointXY(point.x(),
                                                            point.y()))

        # Create and draw cone
        # For polygon

        #cone = QgsRubberBand(self.iface.mapCanvas(), Qgis.GeometryType.Polygon)
        cone = QgsRubberBand(self.iface.mapCanvas(), QgsWkbTypes.PolygonGeometry)
        cone.setToGeometry(cone_geometry, None)
        cone.setColor(color)
        cone.setWidth(CONE_BORDER_WIDTH)

        self.streetsmart.buttonstate.previous_cone = StreetSmart_Cone(cone, self.cone.srs)
        self.iface.mapCanvas().refresh()
