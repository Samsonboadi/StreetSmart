"""Some functions"""
import logging
from shapely.geometry import (shape, mapping)
from qgis.core import (  # pylint: disable=import-error
    QgsProject, QgsCoordinateTransform, QgsCoordinateReferenceSystem)
from .logger import (Logger, log)

logger = Logger(__name__).get()


def _get_transformer(from_srs, to_srs):
    """Returns coordinate transformer for the srs's"""
    if isinstance(from_srs, str):
        from_srs = QgsCoordinateReferenceSystem(from_srs)
    if isinstance(to_srs, str):
        to_srs = QgsCoordinateReferenceSystem(to_srs)
    project = QgsProject.instance()
    transform = QgsCoordinateTransform(from_srs, to_srs, project)
    return transform


@log(logging.DEBUG, print_args=True, print_return=True)
def transform_coordinate(x, y, from_srs, to_srs):
    """Transform coordinate to crs"""
    transform = _get_transformer(from_srs, to_srs)
    transformed = transform.transform(x, y)
    return transformed


@log(logging.DEBUG, print_args=True, print_return=True)
def transform_point(point, from_srs, to_srs):
    """Transform point to crs"""
    transform = _get_transformer(from_srs, to_srs)
    transformed = transform.transform(point)
    return transformed


def _transform_json_coordinate(coordinate, from_srs, to_srs):
    """Transforms a single coordinate"""
    point = transform_coordinate(coordinate[0], coordinate[1], from_srs, to_srs)
    return [point.x(), point.y()]


def _transform_json_coordinates(coordinates, from_srs, to_srs):
    """Transforms a list of coordinates"""
    if (isinstance(coordinates, list) and coordinates[0] and not
            isinstance(coordinates[0], list)):
        # coordinates is a coordinate
        return _transform_json_coordinate(coordinates, from_srs, to_srs)

    return [_transform_json_coordinates(sub_coordinates, from_srs, to_srs)
            for sub_coordinates in coordinates]


def _transform_json_geometry(feature, from_srs, to_srs):
    """Transform the geometry"""
    coords = feature['geometry']['coordinates']
    geom = _transform_json_coordinates(coords, from_srs, to_srs)
    feature['geometry']['coordinates'] = geom


def _transform_json_bbox(feature, from_srs, to_srs):
    """Transform the bounding box"""
    coords = feature['bbox']
    lower = _transform_json_coordinates(coords[:2], from_srs, to_srs)
    upper = _transform_json_coordinates(coords[2:], from_srs, to_srs)
    feature['bbox'] = lower + upper


def _transform_json_feature(feature, from_srs, to_srs):
    """Transforms a feature"""
    _transform_json_geometry(feature, from_srs, to_srs)
    _transform_json_bbox(feature, from_srs, to_srs)
    return feature


@log(logging.DEBUG, print_args=True, print_return=True)
def transform_json_feature_collection(fc, from_srs, to_srs):
    """Transforms a featurecollection"""
    if isinstance(from_srs, str):
        from_srs = QgsCoordinateReferenceSystem(from_srs)
    if isinstance(to_srs, str):
        to_srs = QgsCoordinateReferenceSystem(to_srs)

    if not from_srs.isValid() or not to_srs.isValid():
        return fc

    if from_srs.authid() == to_srs.authid():
        return fc

    features = [_transform_json_feature(feature, from_srs, to_srs)
                for feature in fc['features']]
    fc['features'] = features
    return fc


def _simplify_feature(feature, tolerance):
    """Transforms a feature"""
    geom = feature['geometry']
    print(geom)
    geom = shape(geom)
    simplified_geom = geom.simplify(tolerance, preserve_topology=False)
    print(mapping(simplified_geom))
    feature['geometry'] = mapping(simplified_geom)
    return feature


@log(logging.DEBUG, print_args=True, print_return=True)
def simplify_json_feature_collection(fc, tolerance):
    """Transforms a featurecollection"""
    if tolerance:
        features = [_simplify_feature(feature, tolerance)
                    for feature in fc['features']]
        fc['features'] = features

    return fc


