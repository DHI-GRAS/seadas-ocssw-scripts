"""
The viirs_next_level_name_finder module contains the ViirsNextLevelNameFinder
class for finding standard output file names for VIIRS files when run through
OBPG software.
"""

# import os
import re
import modules.next_level_name_finder as next_level_name_finder


__author__ = 'melliott'

__version__ = '1.0.4-2016-04-29'

class ViirsNextLevelNameFinder(next_level_name_finder.NextLevelNameFinder):
    """
    A class to determine the standard OBPG filename for VIIRS files when the
    given input name is run through the next level of OBPG processing.
    """

    PROCESSING_LEVELS = {
        'l1agen':         'Level 1A',
        'Level 1A':            'Level 1A',
        'l1aextract_viirs' :   'l1aextract_viirs',
        'geolocate_viirs' :    'geo',
        'geo' :                'geo',
        'calibrate_viirs':     'Level 1B',
        'Level 1B':       'Level 1B',
        'level 1b':       'Level 1B',
        'l1brsgen':       'l1brsgen',
        'l1mapgen':       'l1mapgen',
        'l2gen':          'Level 2',
        'Level 2':        'Level 2',
        'l2bin':          'l2bin',
        'l2brsgen':       'l2brsgen',
        'l2extract':      'l2extract',
        'l2mapgen':       'l2mapgen',
        'l3bin':          'l3bin',
        'L3b':            'l3bin',
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

    def _get_geo_extension(self):
        """
        Returns the file extension for GEO MOD files.
        """
        if 'J1' in self.data_files[0].sensor:
            return '.GEO-M_JPSS1'
        return '.GEO-M_SNPP'

    def _get_l1b_extension(self):
        """
        Returns the file extension for L1B MOD files.
        """
        if 'J1' in self.data_files[0].sensor:
            return '.L1B-M_JPSS1'
        return '.L1B-M_SNPP'

    def _get_geo_name(self):
        """
        Returns the name of the GEO file.
        """
        if self.data_files[0].start_time:
            time_stamp = self.data_files[0].start_time
        elif self.data_files[0].metadata:
            time_stamp = self._extract_l1_time(
                self.data_files[0].metadata['RANGEBEGINNINGDATE'],
                self.data_files[0].metadata['RANGEBEGINNINGTIME'])
        geo_name = self.get_platform_indicator() + time_stamp +\
                   self._get_geo_extension()
        return geo_name


    def get_platform_indicator(self):
        """
        Returns a character which indicates what platform (instrument) the
        data in the file is from.  This is usually used as the first character
        of an output file.
        """
        return 'V'

    def _get_extra_extensions(self):
        """
        Make sure ".tar" is stripped out before determining what ."extra"
        extensions may be needed.
        """
        orig_name = self.data_files[0].name
        self.data_files[0].name = re.sub(r"\.tar", "", self.data_files[0].name)

        extra_ext = super(ViirsNextLevelNameFinder, self)._get_extra_extensions()
        self.data_files[0].name = orig_name
        return extra_ext

    def _get_l2_extension(self):
        """
        Return the appropriate extension for an L2 file.
        """
        if 'J1' in self.data_files[0].sensor:
            return '.L2_JPSS1'
        return '.L2_SNPP'

    def _get_transition_functions(self):
        """
        An internal method to set up the "table" of functions to be
        called for each level of processing.
        """
        return {'Level 1A': {'Level 1B':   self._get_l1b_name,
                             'geo':      self._get_geo_name,
                             'l1aextract_viirs' : self._get_l1aextract_name,
                             'l1bgen' :  self._get_l1b_name,
                             'l1brsgen': self._get_l1brsgen_name,
                             'l1mapgen': self._get_l1mapgen_name,
                             'Level 2' : self._get_l2_name
                            },
                'SDR': {'Level 1B': self._get_l1b_name,
                        'l1aextract_seawifs' : self._get_l1aextract_name,
                        'l1bgen' :  self._get_l1b_name,
                        'l1brsgen': self._get_l1brsgen_name,
                        'l1mapgen': self._get_l1mapgen_name,
                        'Level 2' : self._get_l2_name
                       },
                'Level 1B':  {'Level 2': self._get_l2_name,
                              'l1brsgen': self._get_l1brsgen_name,
                              'l1mapgen': self._get_l1mapgen_name
                             },
                'Level 2': {'l2bin':     self._get_l3bin_name,
                            'l2extract': self._get_l2extract_name,
                            'l3bin':     self._get_l3bin_name,
                            'l2brsgen':  self._get_l2brsgen_name,
                            'l2mapgen':  self._get_l2mapgen_name
                           },
                'Level 3 Binned': {'l3bin' :    self._get_l3bin_name,
                                   'l3gen':     self._get_l3gen_name,
                                   'l3mapgen' : self._get_l3mapgen_name,
                                   'SMI' :      self._get_l3mapgen_name
                                  }
               }
