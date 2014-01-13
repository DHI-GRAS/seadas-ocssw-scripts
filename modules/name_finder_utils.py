"""
Utility functions for the next_name_finder program and associated moduled.
"""

__author__ = 'melliott'

import aquarius_next_level_name_finder
import next_level_name_finder
import viirs_next_level_name_finder

def create_level_finder(finder_class, clopts, data_file_list, target_program):
    """
    Instantiates an instance of finder_class and returns it.
    """
    level_finder = None
    if clopts:
        if clopts.suite and clopts.product:
            level_finder = finder_class(data_file_list, target_program,
                                        clopts.suite, clopts.product)
        elif clopts.suite:
            level_finder = finder_class(data_file_list, target_program,
                                        clopts.suite)
        elif clopts.product:
            level_finder = finder_class(data_file_list, target_program, None,
                                        clopts.product)
        else:
            level_finder = finder_class(data_file_list, target_program)
    else:
        level_finder = finder_class(data_file_list, target_program)
    return level_finder

def get_level_finder(data_file_list, target_program, clopts=None):
    """
    Returns an appropriate level finder object for the data file passed in.
    """
    if data_file_list[0].sensor.find('MODIS') != -1:
        level_finder = create_level_finder(next_level_name_finder.ModisNextLevelNameFinder,
                                           clopts, data_file_list,
                                           target_program)
    elif data_file_list[0].sensor.find('SeaWiFS') != -1:
        level_finder = create_level_finder(next_level_name_finder.SeawifsNextLevelNameFinder,
                                           clopts, data_file_list,
                                           target_program)
    elif data_file_list[0].sensor.find('Aquarius') != -1:
        level_finder = create_level_finder(aquarius_next_level_name_finder.AquariusNextLevelNameFinder,
                                           clopts, data_file_list,
                                           target_program)
    elif data_file_list[0].sensor.find('MERIS') != -1:
        level_finder = create_level_finder(next_level_name_finder.MerisNextLevelNameFinder,
                                           clopts, data_file_list,
                                           target_program)
    elif data_file_list[0].sensor.find('VIIRS') != -1:
        level_finder = create_level_finder(viirs_next_level_name_finder.ViirsNextLevelNameFinder,
                                           clopts, data_file_list,
                                           target_program)
    else:
        level_finder = create_level_finder(next_level_name_finder.NextLevelNameFinder,
                                           clopts, data_file_list,
                                           target_program)
    return level_finder
