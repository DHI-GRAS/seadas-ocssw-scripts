
"""
The next_level_name_finder module contains the NextLevelNameFinder class, its
subclass ModisNextLevelNameFinder, and miscellaneous functions for working with
OBPG file names, etc.
"""

__author__ = 'melliott'

import calendar
import datetime
import get_obpg_file_type
import obpg_data_file
import os
import ProcUtils
import re
import sys
import types

DEBUG = False
#DEBUG = True

def convert_str_to_int(short_str):
    """
    Returns an integer taken from the passed in string.
    """
    try:
        int_value =  int(short_str)
    except ValueError:
        err_msg = "Error! Unable to convert {0} to integer.".format(short_str)
        sys.exit(err_msg)
    return int_value

def _get_data_files_info(flf):
    """
    Returns a list of data files read from the specified input file.
    """
    data_file_list = []
    with open(flf, 'rt') as file_list_file:
        inp_lines = file_list_file.readlines()
    for line in inp_lines:
        filename = line.strip()
        if os.path.exists(filename):
            file_typer = get_obpg_file_type.ObpgFileTyper(filename)
            file_type, sensor = file_typer.get_file_type()
            stime, etime = file_typer.get_file_times()
            data_file = obpg_data_file.ObpgDataFile(filename, file_type,
                                                    sensor, stime, etime)
            data_file_list.append(data_file)
    data_file_list.sort()
    return data_file_list

def get_l0_timestamp(l0_file_name):
    """
    An internal method to get the date/time stamp from L0 files.
    """
    time_stamp = ''
    if os.path.exists(l0_file_name + '.const'):
        with open(l0_file_name + '.const') as constructor_file:
            constructor_data = constructor_file.readlines()
        for line in constructor_data:
            if line.find('starttime=') != -1:
                start_time = line[line.find('=') + 1].strip()
                break
        time_stamp = ProcUtils.date_convert(start_time, 't', 'j')
    else:
        input_basename = os.path.basename(l0_file_name)
        if re.match('MOD00.[AP]\d\d\d\d\d\d\d\.\d\d\d\d', input_basename):
            time_stamp = input_basename[7:14] + input_basename[15:19] + '00'
        else:
            err_msg = "Unable to determine time stamp for input file {0}".\
            format(l0_file_name)
            sys.exit(err_msg)
    return time_stamp


def get_time_period_extension(start_date_str, end_date_str):
    """
    Return the part of the file extension based on the time period within the
    start and end dates.
    """
    first_date = datetime.datetime.strptime(start_date_str, '%Y%j%H%M%S')
    last_date = datetime.datetime.strptime(end_date_str, '%Y%j%H%M%S')
    date_diff = last_date - first_date
    if date_diff.days == 0:
        time_ext = '_DAY'
    elif date_diff.days == 7:
        time_ext = '_8D'
    elif is_month(first_date, last_date):
        time_ext = '_MO'
    elif is_year(first_date, last_date):
        time_ext = '_YR'
    else:
        time_ext = '_CU'
    return time_ext

def is_month(day1, day2):
    """
    Returns True if the days are the endpoints of a month; False otherwise.
    """
    return day1.month == day2.month and day1.day == 1 and\
           day2.day == calendar.monthrange(day1.year, day1.month)[1]

def is_year(day1, day2):
    """
    Returns True if the days are the endpoints of a year; False otherwise.
    """
    return day1.year == day2.year and day1.month == 1 and day1.day == 1 and\
           day2.month == 12 and day2.day == 31


class NextLevelNameFinder(object):
    """
    A class to determine what the standard OBPG filename would be when the
    given input name is run through the next level of OBPG processing.
    Note that MODIS and SeaWiFS files are handled in subclasses.
    """
    PROCESSING_LEVELS = {
        'l1agen':         'Level 1A',
        'Level 1':        'Level 1B',
        'Level 1A':       'Level 1A',
        'l1bgen':         'Level 1B',
        'Level 1B':       'Level 1B',
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
        'Level 3 Binned': 'l3bin',
        'SMI':            'SMI',
        'smigen':         'SMI'
    }

    transitions = {
        'general' : {'L1A':'L1B', 'L1B': 'L2', 'L2': 'L3b',
                     'L3b': ['L3b', 'SMI']},
        'modis' : {'L0': 'L1A', 'L1A':['GEO', 'L1B'], 'L1B': 'L2', 'L2': 'L3b',
                   'L3b': ['L3b', 'SMI']}
    }

    def __init__(self, data_files_list, next_level, l2_suite='_OC'):
        if len(data_files_list) == 0:
            err_msg = "Error!  No data file specified for NextLevelNameFinder."
            sys.exit(err_msg)
        if next_level in self.PROCESSING_LEVELS.keys():
            self.next_level = self.PROCESSING_LEVELS[next_level]
        elif next_level in processable_programs:
            if len(data_files_list) == 1:
                file_list = data_files_list[0].name
            elif len(data_files_list) == 2:
                file_list = data_files_list[0].name + ' and ' + \
                            data_files_list[1].name
            else:
#                file_list = [df.name + ', ' for df in data_files_list[:-1]] + \
#                            ' and ' + data_files_list[-1].name
                file_list = ', '.join([str(df.name) for df in data_files_list[:-1]])
                file_list += ', and ' + data_files_list[-1].name
            err_msg = 'Error!  Cannot transition {0} to {1}.'.format(file_list,
                                                                     next_level)
            sys.exit(err_msg)
        else:
            err_msg = 'Error!  "{0}" is not a recognized target output type.'.\
            format(next_level)
            sys.exit(err_msg)
        self.data_files = data_files_list
        self._set_next_suffixes()
        self._set_transition_functions()
        self._set_transition_sequence()
        if l2_suite[0:1] == '_':
            self.l2_suite = l2_suite
        else:
            self.l2_suite = '_' + l2_suite
        if not (self.data_files[0].file_type in self.transition_functions):
            if (self.data_files[0].file_type in self.PROCESSING_LEVELS):
                for df in self.data_files:
                    df.file_type = self.PROCESSING_LEVELS[df.file_type]


    def _do_extension_substitution(self):
        """
        An internal method to do a simple substitution of the file's extension.
        This is just a placeholder and will eventually be removed.
        """
        # todo: remove this method when every transition is implemented.
        basename = os.path.split(self.data_files[0].name)[1]
        basename_parts = basename.rsplit('.', 2)
        suffix = 'unk'
        keys_list =  self.next_suffix.keys()
        for key in keys_list:
            if basename_parts[1].find(key) != -1:
                if self.transition_sequence.index(key) <\
                   self.transition_sequence.index('L2'):
                    suffix = re.sub(key, self.next_suffix[key],
                                    basename_parts[1])
                else:
                    suffix = self.next_suffix[key]
                break
        return basename_parts[0] + '.' + suffix

    def _extract_l1_time(self, date_str, time_str):
        """
        An internal method to extract the date/time stamp from L1 files.
        """
        year = int(date_str[0:4])
        mon = int(date_str[5:7])
        dom = int(date_str[8:10])
        hour = int(time_str[0:2])
        mins = int(time_str[3:5])
        secs = int(time_str[6:8])
        dt_obj = datetime.datetime(year, mon, dom, hour, mins, secs)
        return dt_obj.strftime('%Y%j%H%M%S')

    def _get_end_doy_year(self):
        """
        Extract a day of year and year from an L0 file's metadata and return
        them as integer values .
        """
        if self.data_files[-1].end_time:
            year = self.data_files[-1].end_time[0:4]
            day = self.data_files[-1].end_time[4:7]
        elif self.data_files[-1].metadata:
            day_str = 'End Day'
            yr_str = 'End Year'
            day = convert_str_to_int(self.data_files[-1].metadata[day_str])
            year = convert_str_to_int(self.data_files[-1].metadata[yr_str])
        else:
            err_msg = 'Error! Cannot find end time for {0}'.format(
                self.data_files[-1].name)
            sys.exit(err_msg)
        return day, year

    def _get_l1aextract_name(self):
        """
        Returns the output name from running one of the l1aextract_INST programs
        (where INST = "modis" or "seawifs").
        """
        # Note: This method was placed in the NextLevelNameFinder class, since
        # the functionality is common to both the MODIS and SeaWiFS instruments.
        # However, it is called by the subclasses for those instruments, not
        # from this class.
        next_lvl_name = os.path.basename(self.data_files[0].name) + '.sub'
        return next_lvl_name

    def _get_l1b_extension(self):
        """
        Returns the file extension for L1B files.
        """
        return '.L1B_LAC'

    def _get_l1b_name(self):
        """
        An internal method to return the L1B name from an L1A file.
        """
        next_lvl_name = ''
        first_char = self.get_platform_indicator()
        if self.data_files[0].start_time:
            next_lvl_name = first_char +\
                            self.data_files[0].start_time +\
                            self._get_l1b_extension()
        if self.data_files[0].metadata is not None:
            next_lvl_name = first_char +\
                            self._extract_l1_time(self.data_files[0].metadata['RANGEBEGINNINGDATE'],
                                                  self.data_files[0].metadata['RANGEBEGINNINGTIME']) +\
                            self._get_l1b_extension()
        return next_lvl_name

    def _get_l1brsgen_name(self):
        """
        An internal method to get the L1 browse file name.
        """
        ext = '.L1B_BRS'
        return self._get_single_file_basename() + ext

    def _get_l1mapgen_name(self):
        """
        An internal method to get the L1 mapped file name.
        """
#        ext = '.L1B_MAP'
        if self.data_files[0].file_type == 'Level 1A':
            ext = '.L1A_MAP'
        elif self.data_files[0].file_type == 'Level 1B':
            ext = '.L1B_MAP'
        else:
            ext = '.L1_MAP'
        return self._get_single_file_basename() + ext

    def _get_l2_extension(self):
        """
        Return the appropriate extension for an L2 file.
        """
        ext = '.L2_LAC'
        for data_file in self.data_files:
            if data_file.name.find('GAC') != -1:
                ext = '.L2_GAC'
                break
        return ext

    def _get_l2extract_name(self):
        """
        Return the extension for an L2 extract file.
        """
        next_lvl_name = self._get_l2_name() + '.sub'
        return next_lvl_name

    def _get_l2_name(self):
        """
        An internal method to return the L2 name from an L1 file.
        """
        next_lvl_name = ''
        basename = self._get_single_file_basename()
        if basename != 'indeterminate':
            next_lvl_name = basename + self._get_l2_extension() + self.l2_suite
        else:
            err_msg = 'Error!  Could not determine L2 name for {0}'.\
                      format(self.data_files[0].name)
            sys.exit(err_msg)
        return next_lvl_name

    def _get_l2brsgen_name(self):
        """
        An internal method to get the L1 browse file name.
        """
        ext = '.L2_BRS'
        return self._get_single_file_basename() + ext

    def _get_l2mapgen_name(self):
        """
        An internal method to get the L1 mapped file name.
        """
        ext = '.L2_MAP'
        return self._get_single_file_basename() + ext

#    def _get_l3bin_name(self):
#        """
#        An internal method to return the L3bin name from an L2 or L3bin file.
#        """
#        return self._do_extension_substitution()

    def _get_l3bin_name(self):
        """
        An internal method to return the L3bin name from an L2 or L3bin file.
        """
        first_char = self.get_platform_indicator()
        sday, syear = self._get_start_doy_year()
        eday, eyear = self._get_end_doy_year()
        sdate = datetime.datetime.strptime(str(syear)+'-'+str(sday), '%Y-%j')
        edate = datetime.datetime.strptime(str(eyear)+'-'+str(eday), '%Y-%j')
        days_diff = (edate - sdate).days

        if days_diff == 0:
            extension = '.L3b_DAY'
            next_lvl_name = first_char + str(syear) + str(sday) + extension +\
                            self.l2_suite
        else:
            if days_diff == 7:
                extension = '.L3b_8D'
            else:
                extension = '.L3b_CU'
            next_lvl_name = first_char + str(syear) + str(sday) +\
                            str(eyear) + str(eday) + extension + self.l2_suite
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
        return next_level_name

    def _set_next_suffixes(self):
        """
        An internal method to set up the dictionary which tells what the
        suffix transitions should be.  Separated from __init__() so that
        it can be overridden.
        """
        self.next_suffix = {'L1A' : 'L1B', 'L1B' : 'L2', 'L2' : 'L3b'}

    def get_platform_indicator(self):
        """
        Returns a character which indicates what platform (instrument) the
        data in the file is from.  This is usually used as the first character
        of an output file.
        """
        indicator_dict = {'Aquarius': 'Q', 'CZCS': 'C', 'MERIS': 'M',
                          'MODIS Aqua':  'A', 'MODIS Terra': 'T',
                          'MOS': 'M', 'OCM2': 'O2_', 'OCTS': 'O',
                          'OSMI': 'K', 'SeaWiFS': 'S'}

        if self.data_files[0].sensor in indicator_dict.keys():
            indicator = indicator_dict[self.data_files[0].sensor]
        else:
            err_msg = 'Error!  Platform indicator, {0}, for {1} is not known.'.\
                      format(self.data_files[0].sensor, self.data_files[0].name)
            sys.exit(err_msg)
        for df in self.data_files[1:]:
            if df.sensor in indicator_dict.keys():
                if indicator != indicator_dict[df.sensor]:
                    indicator = 'X'
                    break
        return indicator

    def _get_single_file_basename(self):
        """
        Determine the base part of the output file for a single input file.
        """
        basename = 'indeterminate'
        first_char = self.get_platform_indicator()
        if self.data_files[0].start_time:
            basename = first_char + self.data_files[0].start_time
        elif self.data_files[0].metadata is not None:
            basename = first_char + self._extract_l1_time(
                            self.data_files[0].metadata['RANGEBEGINNINGDATE'],
                            self.data_files[0].metadata['RANGEBEGINNINGTIME'])
        return basename

    def _get_smigen_name(self):
        """
        Returns the output name from from smigen for an L3 Binned file or group
        of files.
        """
        first_char = self.get_platform_indicator()
        sday, syear = self._get_start_doy_year()
        eday, eyear = self._get_end_doy_year()
        sdate = datetime.datetime.strptime(str(syear)+'-'+str(sday), '%Y-%j')
        edate = datetime.datetime.strptime(str(eyear)+'-'+str(eday), '%Y-%j')
        days_diff = (edate - sdate).days
        if days_diff == 0:
            extension = '.L3m_DAY'
            smi_name = first_char + str(syear) + str(sday) + extension +\
                            self.l2_suite
        else:
            if days_diff == 7:
                extension = '.L3m_8D'
            else:
                extension = '.L3m_CU'
            smi_name = first_char + str(syear) + str(sday) +\
                            str(eyear) + str(eday) + extension + self.l2_suite
        return smi_name

    def _get_start_doy_year(self):
        """
        Extract a day of year and year from an L0 file's metadata and return
        them as integer values .
        """
        if self.data_files[0].end_time:
            year = self.data_files[0].start_time[0:4]
            day = self.data_files[0].start_time[4:7]
        elif self.data_files[0].metadata:
            day_str = 'Start Day'
            yr_str = 'Start Year'
            day = convert_str_to_int(self.data_files[0].metadata[day_str])
            year = convert_str_to_int(self.data_files[0].metadata[yr_str])
        else:
            err_msg = 'Error! Cannot find end time for {0}'.format(
                self.data_files[0].name)
            sys.exit(err_msg)
        return day, year

    def _set_transition_functions(self):
        """
        An internal method to set up the "table" of functions to be
        called for each level of processing.  Separated from __init__() so it
        can be overridden.
        """
        self.transition_functions = {'Level 1A': {
                                         'Level 1B':
                                             self._get_l1b_name,
                                         'l1mapgen':
                                             self._get_l1mapgen_name,
                                         'Level 2':
                                             self._get_l2_name
                                     },
                                     'Level 1B': {
                                         'Level 2':
                                             self._get_l2_name,
                                         'l1brsgen':
                                             self._get_l1brsgen_name,
                                         'l1mapgen':
                                             self._get_l1mapgen_name
                                     },
                                     'Level 2': {
                                         'l2bin':
                                             self._get_l3bin_name,
                                         'l2extract':
                                             self._get_l2extract_name,
                                         'l3bin':
                                             self._get_l3bin_name,
                                         'l2brsgen':
                                             self._get_l2brsgen_name,
                                         'l2mapgen':
                                             self._get_l2mapgen_name
                                     },
                                     'Level 3 Binned': {
                                         'l3bin' : self._get_l3bin_name,
                                         'SMI' :   self._get_smigen_name
                                     }
        }

    def _set_transition_sequence(self):
        """
        An internal method to set up the sequence of transitions.  Separated
        from __init__() so it can be overridden.
        """
        self.transition_sequence = ['L1A', 'L1B', 'L2', 'L3bin']

#########################################

class ModisNextLevelNameFinder(NextLevelNameFinder):
    """
    A class to determine what the standard OBPG filename would be
    for MODIS files when the given input name is run through the next
    level of OBPG processing.
    """
    PROCESSING_LEVELS = {
        'l1agen':            'Level 1A',
        'modis_L1A.py':      'Level 1A',
        'Level 1A':          'Level 1A',
        'geogen':            'GEO',
        'modis_GEO.py':      'GEO',
        'GEO':               'GEO',
        'l1aextract_modis':  'l1aextract_modis',
        'l1bgen':            'Level 1B',
        'Level 1B':          'Level 1B',
        'modis_L1B.py':      'Level 1B',
        'l1brsgen':          'l1brsgen',
        'l1mapgen':          'l1mapgen',
        'l2gen':             'Level 2',
        'Level 2':           'Level 2',
        'l2bin':             'l2bin',
        'l2brsgen':          'l2brsgen',
        'l2extract':         'l2extract',
        'l2mapgen':          'l2mapgen',
        'Level 3 Binned':    'l3bin',
        'l3bin':             'l3bin',
        'L3b':               'l3bin',
        'SMI':               'SMI',
        'smigen':            'SMI'
    }

    def __init__(self, data_files_list, next_level, l2_suite='_OC'):
        super(ModisNextLevelNameFinder, self).__init__(data_files_list,
                                                       next_level, l2_suite)

    def _get_aqua_l0_to_l1a_name(self):
        """
        An internal method to return the L1A name from an Aqua L0 file.
        """
        time_stamp = get_l0_timestamp(self.data_files[0].name)
        l1a_name = 'A' + time_stamp + self._get_l1a_extension()
        return l1a_name

    def _get_geo_extension(self):
        """
        Returns the file extension for GEO files.
        """
        return '.GEO'

    def _get_geo_name(self):
        """
        Returns the name of the GEO file.
        """
        if self.data_files[0].start_time:
            time_stamp = self.data_files[0].start_time
        elif self.data_files[0].metadata:
            time_stamp = self._extract_l1_time(self.data_files[0].metadata['RANGEBEGINNINGDATE'],
                                               self.data_files[0].metadata['RANGEBEGINNINGTIME'])
        geo_name = self.get_platform_indicator() + time_stamp +\
                   self._get_geo_extension()
        return geo_name

    def _get_l1a_extension(self):
        """
        Returns the file extension for L1A files.
        """
        return '.L1A_LAC'

    def _get_l1a_name(self):
        """
        An internal method to return the L1A name from an L0 file.
        """
        if self.data_files[0].sensor.find('Aqua') != -1:
            next_level_name = self._get_aqua_l0_to_l1a_name() #first_char = 'A'
        else:
            next_level_name = self._get_terra_l0_to_l1a_name() #first_char = 'T'
        return next_level_name

    def _get_l1b_extension(self):
        """
        Returns the file extension for L1B files.
        """
        return '.L1B_LAC'

    def _get_l1b_name(self):
        """
        An internal method to return the L1B name from an L1A file.
        """
        next_lvl_name = 'indeterminate'
        first_char = self.get_platform_indicator()
        if self.data_files[0].start_time:
            next_lvl_name = first_char +\
                            self.data_files[0].start_time +\
                            self._get_l1b_extension()
        if self.data_files[0].metadata is not None:
            next_lvl_name = first_char +\
                            self._extract_l1_time(
                              self.data_files[0].metadata['RANGEBEGINNINGDATE'],
                              self.data_files[0].metadata['RANGEBEGINNINGTIME']) +\
                            self._get_l1b_extension()
        return next_lvl_name


    def _get_l2_extension(self):
        """
        Returns the extension for an L2 file.
        """
        return '.L2_LAC'

    def _get_l2_name(self):
        """
        An internal method to return the L2 name from an L1B file.
        """
        first_char = self.get_platform_indicator()
        if self.data_files[0].start_time:
            next_lvl_name = first_char +\
                            self.data_files[0].start_time +\
                            self._get_l2_extension()
        elif self.data_files[0].metadata:
            next_lvl_name = first_char +\
                            self._extract_l1_time(
                              self.data_files[0].metadata['RANGEBEGINNINGDATE'],
                              self.data_files[0].metadata['RANGEBEGINNINGTIME']) +\
                            self._get_l2_extension()
        if self.l2_suite:
            next_lvl_name += self.l2_suite
        return next_lvl_name #self._do_extension_substitution()

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
        next_level_name = 'Error computing output file name.'
        if len(self.data_files) > 0:
            if (self.data_files[0].file_type == 'Level 0'):
                next_level_name = self._get_l1a_name()
            elif self.data_files[0].file_type in self.transition_functions:
                if isinstance(self.transition_functions[self.data_files[0].file_type],
                                types.FunctionType) or \
                     isinstance(self.transition_functions[self.data_files[0].file_type],
                                types.MethodType):
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
        return next_level_name

    def get_platform_indicator(self):
        """
        Returns a character which indicates whether a file contains Aqua or
        Terra data, A = Aqua and T = Terra.  This can be used as the first
        character of an output file.
        """
        if self.data_files[0].sensor.find('Aqua') != -1:
            indicator = 'A'
        elif self.data_files[0].sensor.find('Terra') != -1:
            indicator = 'T'
        elif self.data_files[0].metadata is not None:
            if 'LONGNAME' in self.data_files[0].metadata.keys():
                if self.data_files[0].metadata['LONGNAME'].find('Aqua') != -1:
                    indicator = 'A'
                elif self.data_files[0].metadata['LONGNAME'].find('Terra') != \
                     -1:
                    indicator = 'T'
                else:
                    err_msg = 'Error! Cannot find MODIS platform for {0}.'.\
                              format(self.data_files[0].name)
                    sys.exit(err_msg)
            else:
                if self.data_files[0].metadata['Title'].find('MODISA') != -1:
                    indicator = 'A'
                elif self.data_files[0].metadata['Title'].find('MODIST') != -1:
                    indicator = 'T'
                else:
                    err_msg = 'Error!  Cannot find MODIS platform for {0}.'.\
                    format(self.data_files[0].name)
                    sys.exit(err_msg)
        return indicator

    def _get_terra_l0_to_l1a_name(self):
        """
        An internal method to return the L1A name from an Aqua L0 file.
        """
        time_stamp = get_l0_timestamp(self.data_files[0].name)
        l1a_name = 'T' + time_stamp + self._get_l1a_extension()
        return l1a_name

    def _set_next_suffixes(self):
        """
        An internal method to set the dictionary which tells what the
        suffix transitions should be.
        """
        self.next_suffix = {'L0': 'L1A', 'L1A' : 'L1B', 'L1B' : 'L2',
                            'L2' : 'L3b'}

    def _set_transition_functions(self):
        """
        An internal method to set up the "table" of functions to be
        called for each level of processing.
        """
        self.transition_functions = {'Level 0': self._get_l1a_name,
                                     'Level 1A': {'GEO':
                                                      self._get_geo_name,
                                                  'Level 1B':
                                                      self._get_l1b_name,
                                                  'l1aextract_modis' :
                                                      self._get_l1aextract_name,
                                                  'l1bgen' :
                                                      self._get_l1b_name,
                                                  'Level 2' :
                                                      self._get_l2_name
                                                 },
                                     'Level 1B': {'Level 2':
                                                      self._get_l2_name,
                                                  'l1brsgen':
                                                      self._get_l1brsgen_name,
                                                  'l1mapgen':
                                                      self._get_l1mapgen_name
                                                 },
                                     'Level 2': { 'l2bin':
                                                      self._get_l3bin_name,
                                                  'l2extract':
                                                      self._get_l2extract_name,
                                                  'l3bin':
                                                      self._get_l3bin_name,
                                                  'l2brsgen':
                                                      self._get_l2brsgen_name,
                                                  'l2mapgen':
                                                      self._get_l2mapgen_name
                                                },
                                     'Level 3 Binned': {
                                         'l3bin' : self._get_l3bin_name,
                                         'SMI' : self._get_smigen_name
                                     }
        }

    def _set_transition_sequence(self):
        """
        An internal method to set up the sequence of transitions.  Separated
        from __init__() so that it can be overridden.
        """
        self.transition_sequence = ['L1A', 'L1B', 'L2', 'L3bin']

#########################################

class SeawifsNextLevelNameFinder(NextLevelNameFinder):
    """
    A class to determine what the standard OBPG filename would be for
    SeaWiFS files when the given input name is run through the next
    level of OBPG processing.
    """
    PROCESSING_LEVELS = {
        'l1agen':       'Level 1A',
        'Level 1A':     'Level 1A',
        'l1aextract_seawifs' : 'l1aextract_seawifs',
        'l1bgen':       'Level 1B',
        'Level 1B':     'Level 1B',
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
        'SMI':          'SMI',
        'smigen':       'SMI'
    }

    def __init__(self, data_files_list, next_level, l2_suite='_OC'):
        super(SeawifsNextLevelNameFinder, self).__init__(data_files_list,
                                                       next_level, l2_suite)

    def _set_transition_functions(self):
        """
        An internal method to set up the "table" of functions to be
        called for each level of processing.
        """
        self.transition_functions = {'Level 1A': {'Level 1B':
                                                      self._get_l1b_name,
                                                  'l1aextract_seawifs' :
                                                      self._get_l1aextract_name,
                                                  'l1bgen' :
                                                      self._get_l1b_name,
                                                  'l1mapgen':
                                                      self._get_l1mapgen_name,
                                                  'Level 2' :
                                                      self._get_l2_name
                                     },
                                     'Level 1B': {'Level 2':
                                                      self._get_l2_name,
                                                  'l1brsgen':
                                                      self._get_l1brsgen_name,
                                                  'l1mapgen':
                                                      self._get_l1mapgen_name
                                     },
                                     'Level 2': { 'l2bin':
                                                      self._get_l3bin_name,
                                                  'l2extract':
                                                      self._get_l2extract_name,
                                                  'l3bin':
                                                      self._get_l3bin_name,
                                                  'l2brsgen':
                                                      self._get_l2brsgen_name,
                                                  'l2mapgen':
                                                      self._get_l2mapgen_name
                                     },
                                     'Level 3 Binned': {
                                         'l3bin' : self._get_l3bin_name,
                                         'SMI' : self._get_smigen_name
                                     }
        }

#########################################

class AquariusNextLevelNameFinder(NextLevelNameFinder):
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
        'l2gen':          'Level 2',
        'Level 2':        'Level 2',
        'l2bin_aquarius': 'l2bin_aquarius',
        'l2brsgen':       'l2brsgen',
        'l2extract':      'l2extract',
        'l2mapgen':       'l2mapgen',
        'l3bin':          'l3bin',
        'L3b':            'l3bin',
        'SMI':            'SMI',
        'smigen':         'SMI'
    }

    def __init__(self, data_files_list, next_level, l2_suite='_OC'):
        super(AquariusNextLevelNameFinder, self).__init__(data_files_list,
                                                           next_level, l2_suite)

    def _set_transition_functions(self):
        """
        An internal method to set up the "table" of functions to be
        called for each level of processing.
        """
        self.transition_functions = {'Level 1A': {'Level 1B':
                                                      self._get_l1b_name,
                                                  'l1aextract_seawifs' :
                                                      self._get_l1aextract_name,
                                                  'l1bgen' :
                                                      self._get_l1b_name,
                                                  'l1mapgen':
                                                      self._get_l1mapgen_name,
                                                  'Level 2' :
                                                      self._get_l2_name
        },
                                     'Level 1B': {'Level 2':
                                                      self._get_l2_name,
                                                  'l1brsgen':
                                                      self._get_l1brsgen_name,
                                                  'l1mapgen':
                                                      self._get_l1mapgen_name
                                     },
                                     'Level 2': { 'l2bin_aquarius':
                                                      self._get_l3bin_name,
                                                  'l2extract':
                                                      self._get_l2extract_name,
                                                  'l3bin':
                                                      self._get_l3bin_name,
                                                  'l2brsgen':
                                                      self._get_l2brsgen_name,
                                                  'l2mapgen':
                                                      self._get_l2mapgen_name
                                     },
                                     'Level 3 Binned': {
                                         'l3bin' : self._get_l3bin_name,
                                         'SMI' : self._get_smigen_name
                                     }
        }

#########################################

processable_programs = set(NextLevelNameFinder.PROCESSING_LEVELS.keys() +\
                           ModisNextLevelNameFinder.PROCESSING_LEVELS.keys() +\
                           SeawifsNextLevelNameFinder.PROCESSING_LEVELS.keys() +\
                           AquariusNextLevelNameFinder.PROCESSING_LEVELS.keys())
