"""
A module containomg the ViirsNextLevelNameFinder class for finding standard
output file names for VIIRS files when run through OBPG software.
"""

__author__ = 'melliott'

__version__ = '1.0.2-2015-04-24'

import modules.next_level_name_finder as next_level_name_finder
import re
import sys

class AquariusNextLevelNameFinder(next_level_name_finder.NextLevelNameFinder):
    """
    A class to determine what the standard OBPG filename would be for
    Aquarius files when the given input name is run through the next
    level of OBPG processing.
    """
    PROCESSING_LEVELS = {
        'l1agen':         'Level 1A',
        'Level 1A':       'Level 1A',
        'l1aextract_seawifs' : 'l1aextract_seawifs',
        'l1bgen':         'Level 1B',
        'Level 1B':       'Level 1B',
        'l1brsgen':       'l1brsgen',
        'l1mapgen':       'l1mapgen',
        'l2gen_aquarius': 'Level 2',
        'Level 2':        'Level 2',
        'l2bin_aquarius': 'l2bin_aquarius',
        'l2brsgen':       'l2brsgen',
        'l2extract':      'l2extract',
        'l2mapgen':       'l2mapgen',
        'l3bin':          'l3bin',
        'L3b':            'l3bin',
        'l3gen':          'l3gen',
        'l3mapgen':       'SMI',
        'SMI':            'SMI',
        'smigen':         'SMI'
    }

    def __init__(self, data_files_list, next_level, suite=None,
                 resolution=None, oformat=None):
        super(AquariusNextLevelNameFinder, self).__init__(data_files_list,
                                                          next_level, suite,
                                                          resolution, oformat)

    def _get_l2_extension(self):
        l1_parts = self.data_files[0].name.split('.')
        if len(l1_parts) > 2:
            err_msg = 'Error! Unable to determine extension for {0}'.\
                      format(self.data_files[0].name)
            sys.exit(err_msg)
        extension = re.sub(r'L1[AB]_(.*)', r'.L2_\g<1>', l1_parts[1])
        return extension

    def _get_l2_name(self):
        """
        An internal method to return the L2 name from an L1 file.
        """
        basename = self._get_single_file_basename()
        if basename != 'indeterminate':
            if self.suite:
                next_lvl_name = basename + self._get_l2_extension() + self.suite
            else:
                next_lvl_name = basename + self._get_l2_extension()
        else:
            err_msg = 'Error!  Could not determine L2 name for {0}'.\
            format(self.data_files[0].name)
            sys.exit(err_msg)
        return next_lvl_name

    def _get_transition_functions(self):
        """
        An internal method to set up the "table" of functions to be
        called for each level of processing.
        """
        return {'Level 1A': {
                    'Level 1B': self._get_l1b_name,
                    'l1aextract_seawifs' : self._get_l1aextract_name,
                    'l1bgen' : self._get_l1b_name,
                    'l1mapgen': self._get_l1mapgen_name,
                    'Level 2' : self._get_l2_name },
                'Level 1B': {
                    'Level 2': self._get_l2_name,
                    'l1brsgen': self._get_l1brsgen_name,
                    'l1mapgen': self._get_l1mapgen_name },
                'Level 2': { 'l2bin_aquarius': self._get_l3bin_name,
                    'l2extract': self._get_l2extract_name,
                    'l3bin': self._get_l3bin_name,
                    'l2brsgen': self._get_l2brsgen_name,
                    'l2mapgen': self._get_l2mapgen_name },
                'Level 3 Binned': {
                    'l3bin' : self._get_l3bin_name,
                    'SMI' : self._get_smigen_name,
                    'l3gen': self._get_l3gen_name}
        }
