"""Utilities to start a python subprocess"""
import logging
import os
import subprocess
import sys

from .logger import (Logger, log)
from qgis.core import QgsMessageLog
logger = Logger(__name__).get()

DETACHED_PROCESS = 0x00000008
CREATE_NEW_PROCESSGROUP = 0x00000200


@log(logging.DEBUG, print_args=True)
def start_command(command, detached_process, new_processgroup=True):
    """Starts a shell command"""
    flags = 0x0

    if new_processgroup:
        flags = CREATE_NEW_PROCESSGROUP

    if detached_process:
        flags = flags | DETACHED_PROCESS

    return subprocess.Popen(command, close_fds=True,
                            creationflags=flags)


@log(logging.DEBUG, print_args=True)
def start_python_script(python_file_name, args, detached_process,
                        new_processgroup=True):
    """Starts a python script with the same python interpreter"""
    base_path = os.path.dirname(os.path.abspath(__file__))
    file_to_execute = os.path.join(base_path, python_file_name)
    python_exe = os.path.join(sys.base_exec_prefix, 'python.exe')
    command = [python_exe, file_to_execute]
    command.extend(args)

    proc = start_command(command, detached_process, new_processgroup)

    # logger.info("panoramaviewer pid: %s", proc.pid)
    return proc


@log(logging.DEBUG, print_args=True, print_return=True)
def convert_meters_to_mapunits(value, map_canvas):
    """Converts and returns a value in meters to the units used in the
    canvas."""
    canvas_units = map_canvas.mapUnits()
    return convert_distance(value, 0, canvas_units)


@log(logging.DEBUG, print_args=True, print_return=True)
def convert_distance(value, from_distance, to_distance):
    """Converts a distance to another distance unit"""
    # Conversion table for Meters, Km, Feet, NauticalMiles, Yards, Miles, Degrees, Centimeters, Millimeters, Unknown
    to_meters = [1, 1000, 0.3048, 1852.001, 0.9144, 1609.344, 111111.111, 0.01, 0.001, 1]

    value_in_meters = value * to_meters[from_distance]
    transformed_value = value_in_meters / to_meters[to_distance]
    print("Test transformed search radius",transformed_value)
    logger.debug(transformed_value)
    #QgsMessageLog.logMessage(str(transformed_value),"transformed_value" )
    return transformed_value

