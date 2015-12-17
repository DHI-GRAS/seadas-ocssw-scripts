"""
Utility functions for the next_name_finder program and associated modules.

These functions were placed in a separate module to prevent "circular imports".
Take care making modifications.
"""

__author__ = 'melliott'

__version__ = '1.0.3-2015-08-10'

import modules.aquarius_next_level_name_finder as \
        aquarius_next_level_name_finder
import modules.next_level_name_finder as next_level_name_finder
import modules.viirs_next_level_name_finder as viirs_next_level_name_finder

def convert_opts_to_dict(options):
    """
    Converts optparse options into a dictionary
    """
    ret_dict = {}
    if options.resolution:
        ret_dict['resolution'] = options.resolution
    if options.suite:
        ret_dict['suite'] = options.suite
    if options.oformat:
        ret_dict['oformat'] = options.oformat
    return ret_dict

def create_level_finder(finder_class, clopts, data_file_list, target_program):
    """
    Instantiates an instance of finder_class and returns it.
    """
    level_finder = None
    if 'resolution' in clopts:
        resolution = clopts['resolution']
    else:
        resolution = None
    if 'suite' in clopts:
        suite = clopts['suite']
    else:
        suite = None
    if 'oformat' in clopts:
        oformat = clopts['oformat']
    else:
        oformat = None
    level_finder = finder_class(data_file_list, target_program, suite,
                                resolution, oformat)
    return level_finder

def get_level_finder(data_file_list, target_program, clopts=None):
    """
    Returns an appropriate level finder object for the data file passed in.
    """
    if not isinstance(clopts, dict):
        # Assuming the clopts passed in is a group of options from optparse.
        clopts = vars(clopts)

    if data_file_list[0].sensor.find('MODIS') != -1:
        level_finder = create_level_finder(
            next_level_name_finder.ModisNextLevelNameFinder, clopts,
            data_file_list, target_program)
    elif data_file_list[0].sensor.find('SeaWiFS') != -1:
        level_finder = create_level_finder(
            next_level_name_finder.SeawifsNextLevelNameFinder, clopts,
            data_file_list, target_program)
    elif data_file_list[0].sensor.find('Aquarius') != -1:
        level_finder = create_level_finder(
            aquarius_next_level_name_finder.AquariusNextLevelNameFinder, clopts,
            data_file_list, target_program)
    elif data_file_list[0].sensor.find('MERIS') != -1:
        level_finder = create_level_finder(
            next_level_name_finder.MerisNextLevelNameFinder, clopts,
            data_file_list, target_program)
    elif data_file_list[0].sensor.find('VIIRS') != -1:
        level_finder = create_level_finder(
            viirs_next_level_name_finder.ViirsNextLevelNameFinder, clopts,
            data_file_list, target_program)
    else:
        level_finder = create_level_finder(
            next_level_name_finder.NextLevelNameFinder, clopts,
            data_file_list, target_program)
    return level_finder
