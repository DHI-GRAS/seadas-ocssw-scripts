"""
A module containing the ViirsNextLevelNameFinder class for finding standard
output file names for VIIRS files when run through OBPG software.
"""


import datetime
import os
import re
import sys
import types
import modules.next_level_name_finder as next_level_name_finder
# import next_level_name_finder

__author__ = 'melliott'

__version__ = '1.0.4-2018-06-27'

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

    def _get_data_version(self):
        """
        Return the data version for Aquarius, such as "_V5.0.0".
        """
        aq_ver = ''
        if len(self.data_files) == 1:
            base_name = os.path.basename(self.data_files[0].name)
            if base_name.count('.') > 1:
                aq_ver = re.findall('(\_V\d*\.\d*.*$)', base_name)[-1]
        return aq_ver

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

    def _get_l3bin_name(self):
        """
        An internal method to return the L3bin name from an L2 or L3bin file.
        """
        first_char = self.get_platform_indicator()
        sday, syear = self._get_start_doy_year()
        eday, eyear = self._get_end_doy_year()
        if sday and syear and sday > 0 and syear > 0:
            sdate = datetime.datetime.strptime(str(syear) + '-' + str(sday),
                                               '%Y-%j')
        else:
            err_msg = 'Error! Cannot process start date data: year = ' \
            '{0}, doy = {1}'.format(syear, sday)
            sys.exit(err_msg)
        if eday and eyear and eday > 0 and eyear > 0:
            edate = datetime.datetime.strptime(str(eyear) + '-' + str(eday),
                                               '%Y-%j')
        else:
            err_msg = 'Error! Cannot process end date data: year = {0},' \
            'doy = {1}'.format(eyear, eday)
            sys.exit(err_msg)
        days_diff = next_level_name_finder._get_days_diff(edate, sdate)

        if self.suite is None:
            self.suite = '_SCI'
        
        if days_diff == 0:
            extension = '.L3b_DAY'
            next_lvl_name = first_char + str(syear) + str(sday) + extension +\
                            self.suite
        else:
            if days_diff == 7:
                extension = '.L3b_8D'
            else:
                extension = '.L3b_CU'
            next_lvl_name = first_char + str(syear) + str(sday) +\
                            str(eyear) + str(eday) + extension + self.suite
        return next_lvl_name

    def get_next_level_name(self):
        """
        The API method to return the file name of the next level file(s) from
        the file given when the object was instantiated.  For example, if the
        given filename is an L1B file, the next level file name will be an L2.
        For some levels, if the filename already follows the OBPG convention,
        the only change will be to the extension; e.g. A2000123010100.L1B_LAC ->
        A2000123010100.L2_LAC.  However, it is not assumed that the input file
        follows this convention, so the output file name is derived from data
        in the file header.
        """
        next_level_name = 'indeterminate'
        if len(self.data_files) > 0:
            if isinstance(self.transition_functions[self.data_files[0].file_type], types.FunctionType) \
               or isinstance(self.transition_functions[self.data_files[0].file_type], types.MethodType):
                next_level_name = self.transition_functions[self.data_files[0].file_type]()
            elif self.next_level in self.transition_functions[
                    self.data_files[0].file_type].keys():
                next_level_name = self.transition_functions[\
                                  self.data_files[0].file_type]\
                [self.next_level]()
            else:
                err_msg = 'Error! Cannot transition {0} to {1}.'.format(
                    self.data_files[0].name, self.next_level)
                sys.exit(err_msg)
            next_level_name += self._get_data_version()
#         extra_ext = self._get_extra_extensions()
#         if extra_ext:
#             if next_level_name.find(extra_ext) == -1:
#                 # extra_ext in not in the name yet, add it.
#                 if extra_ext[0] != '.':
#                     next_level_name += '.' + extra_ext
#                 else:
#                     next_level_name += extra_ext

        return next_level_name

    def _get_single_file_basename(self):
        """
        For Aquarius, the base name is just copied over, instead of taken from
        the metadata (JIRA ticket 1074).
        """
        basename = os.path.basename(self.data_files[0].name).split('.')[0]
        return basename

    def _get_transition_functions(self):
        """
        An internal method to set up the "table" of functions to be
        called for each level of processing.
        """
        return {'Level 1A': {'Level 1B': self._get_l1b_name,
                             'l1aextract_seawifs' : self._get_l1aextract_name,
                             'l1bgen' : self._get_l1b_name,
                             'l1mapgen': self._get_l1mapgen_name,
                             'Level 2' : self._get_l2_name
                            },
                'Level 1B': {'Level 2': self._get_l2_name,
                             'l1brsgen': self._get_l1brsgen_name,
                             'l1mapgen': self._get_l1mapgen_name
                            },
                'Level 2': {'l2bin_aquarius': self._get_l3bin_name,
                            'l2extract': self._get_l2extract_name,
                            'l3bin': self._get_l3bin_name,
                            'l2brsgen': self._get_l2brsgen_name,
                            'l2mapgen': self._get_l2mapgen_name
                           },
                'Level 3 Binned': {'l3bin' : self._get_l3bin_name,
                                   'SMI' : self._get_l3mapgen_name,
                                   'l3gen': self._get_l3gen_name
                                  }
               }
