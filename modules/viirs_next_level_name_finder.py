"""
The viirs_next_level_name_finder module contains the ViirsNextLevelNameFinder
class for finding standard output file names for VIIRS files when run through
OBPG software.
"""

__author__ = 'melliott'

__version__ = '1.0.2-2015-04-24'

import  modules.next_level_name_finder as next_level_name_finder

class ViirsNextLevelNameFinder(next_level_name_finder.NextLevelNameFinder):
    """
    A class to determine the standard OBPG filename for VIIRS files when the
    given input name is run through the next level of OBPG processing.
    """

    PROCESSING_LEVELS = {
        'l1agen':       'Level 1A',
        'Level 1A':     'Level 1A',
        'l1aextract_seawifs' : 'l1aextract_seawifs',
        'l1bgen':       'Level 1B',
        'Level 1B':     'Level 1B',
        'level 1b':       'Level 1B',
        'l1brsgen':     'l1brsgen',
        'l1mapgen':     'l1mapgen',
        'l2gen':        'Level 2',
        'Level 2':      'Level 2',
        'l2bin':        'l2bin',
        'l2brsgen':     'l2brsgen',
        'l2extract':    'l2extract',
        'l2mapgen':     'l2mapgen',
        'l3bin':        'l3bin',
        'L3b':          'l3bin',
        'l3gen':          'l3gen',
        'l3mapgen':       'SMI',           # Temporary(?)
        'SDR':          'Level 1B',
        'SMI':          'SMI',
        'smigen':       'SMI'
    }


    def __init__(self, data_files_list, next_level, suite=None,
                 resolution=None, oformat=None):
        super(ViirsNextLevelNameFinder, self).__init__(data_files_list,
                                                       next_level, suite,
                                                       resolution, oformat)

    def get_platform_indicator(self):
        """
        Returns a character which indicates what platform (instrument) the
        data in the file is from.  This is usually used as the first character
        of an output file.
        """
        return 'V'

    def _get_l2_extension(self):
        """
        Return the appropriate extension for an L2 file.
        """
        return '.L2_NPP'
