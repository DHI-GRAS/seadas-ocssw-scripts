"""
The next_level_name_finder module contains the NextLevelNameFinder class, some
instrument specific subclasses, and miscellaneous functions for working with
OBPG file names, etc.
"""

import calendar
import datetime
import os
import re
import sys
import types
#from lxml.html.diff import start_tag

import get_obpg_file_type
import modules.obpg_data_file as obpg_data_file
import modules.ProcUtils as ProcUtils
import modules.time_utils as time_utils

__author__ = 'melliott'

__version__ = '1.0.6-2018-05-08'

DEBUG = False
#DEBUG = True

def convert_str_to_int(short_str):
    """
    Returns an integer taken from the passed in string.
    """
    try:
        int_value = int(short_str)
    except ValueError:
        err_msg = "Error! Unable to convert {0} to integer.".format(short_str)
        sys.exit(err_msg)
    return int_value

def find_extension(format_data_list, search_term):
    """
    Returns the extension from format_data_list that is indicated by
    search_term.
    """
    extension = None
    try:
        # Are we searching for a matching index number ...
        int(search_term)
        tuple_index = 0
    except ValueError:
        # ... or a matching format name?
        tuple_index = 1
    # Use a generator to find the match.
    format_index = next((i for i, t in enumerate(format_data_list) if format_data_list[i][tuple_index].lower() == search_term.lower()), None)
    if (format_index != None) and (format_index < len(format_data_list)):
        extension = format_data_list[format_index][2]
    else:
        for ext_candidate in format_data_list:
            if search_term.lower() == ext_candidate[2].lower():
                extension = ext_candidate[2]
                break
    return extension

def _get_days_diff(day1, day2):
    """
    Returns the number of days between two days, by subtracting day2 from day1.
    """
    return (day1 - day2).days


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
    A method to get the date/time stamp from L0 files.
    """
    # Todo: Add check & handling for time stamp in metadata.
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
        if re.match(r'MOD00.[AP]\d\d\d\d\d\d\d\.\d\d\d\d', input_basename):
            time_stamp = input_basename[7:14] + input_basename[15:19] + '00'
        elif re.match(r'[AP]\d\d\d\d\d\d\d\d\d\d\d\d\d\.L0_.{3}',
                      input_basename):
            time_stamp = input_basename[1:12] + '00'
        else:
            err_msg = "Unable to determine time stamp for input file {0}".\
            format(l0_file_name)
            sys.exit(err_msg)
    return time_stamp

def get_end_day_year(metadata):
    """
    Returns the end day and year for a file, determined from the contents of
    metadata as ints.
    """
    if 'End Day' in metadata:
        eday = convert_str_to_int(metadata['End Day'])
    elif 'Period End Day' in metadata:
        eday = convert_str_to_int(metadata['Period End Day'])
    elif 'time_coverage_end' in metadata:
        eday = time_utils.convert_month_day_to_doy(
            metadata['time_coverage_end'][5:7],
            metadata['time_coverage_end'][8:10],
            metadata['time_coverage_end'][0:4])
    else:
        err_msg = 'Error! Cannot determine end day.'
        sys.exit(err_msg)
    if 'End Year' in metadata:
        eyear = convert_str_to_int(metadata['End Year'])
    elif 'Period End Year' in metadata:
        eyear = convert_str_to_int(metadata['Period End Year'])
    elif 'time_coverage_end' in metadata:
        eyear = convert_str_to_int(metadata['time_coverage_end'][0:4])
    else:
        err_msg = 'Error! Cannot determine end year.'
        sys.exit(err_msg)
    return eday, eyear

def get_start_day_year(metadata):
    """
    Returns the start day and year for a file, determined from the contents of
    metadata as ints.
    """
    if 'Start Day' in metadata:
        sday = convert_str_to_int(metadata['Start Day'])
    elif 'Period Start Day' in metadata:
        sday = convert_str_to_int(metadata['Period Start Day'])
    elif 'time_coverage_start' in metadata:
        sday = time_utils.convert_month_day_to_doy(
            metadata['time_coverage_start'][5:7],
            metadata['time_coverage_start'][8:10],
            metadata['time_coverage_start'][0:4])
    else:
        err_msg = 'Error! Cannot determine start day.'
        sys.exit(err_msg)
    if 'Start Year' in metadata:
        syear = convert_str_to_int(metadata['Start Year'])
    elif 'Period Start Year' in metadata:
        syear = convert_str_to_int(metadata['Period Start Year'])
    elif 'time_coverage_start' in metadata:
        syear = convert_str_to_int(metadata['time_coverage_start'][0:4])
    else:
        err_msg = 'Error! Cannot determine start year.'
        sys.exit(err_msg)
    return sday, syear

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

def read_fileformats():
    """
    Returns a tuple containing the file formats.
    """

    format_file_path = os.path.join(os.getenv('OCDATAROOT'), 'common',
                                    'file_formats.txt')
    if os.path.exists(format_file_path):
        file_formats = []
        format_file_hndl = open(format_file_path)
        inp_lines = format_file_hndl.readlines()
        format_file_hndl.close()
        for line in inp_lines:
            cleaned_line = line.strip()
            if cleaned_line[0] != '#':
                #format = get_format(cleaned_line)
                file_format = tuple(cleaned_line.split(':'))

                file_formats.append(file_format)

        return file_formats
    else:
        err_msg = 'Error! Cannot find file {0}.'.format(format_file_path)
        sys.exit(err_msg)

class NextLevelNameFinder(object):
    """
    A class to determine what the standard OBPG filename would be when the
    given input name is run through the next level of OBPG processing.
    Note that some instruments are handled in subclasses.
    """
    PROCESSING_LEVELS = {
        'l1agen':         'Level 1A',
        'Level 1':        'Level 1B',
        'Level 1A':       'Level 1A',
        'level 1a':       'Level 1A',
        'l1bgen':         'Level 1B',
        'Level 1B':       'Level 1B',
        'level 1b':       'Level 1B',
        'l1brsgen':       'l1brsgen',
        'l1mapgen':       'l1mapgen',
        'l2gen':          'Level 2',
        'Level 2':        'Level 2',
        'level 2':        'Level 2',
        'l2bin':          'l2bin',
        'l2brsgen':       'l2brsgen',
        'l2extract':      'l2extract',
        'l2mapgen':       'l2mapgen',
        'l3bin':          'l3bin',
        'L3b':            'l3bin',
        'l3gen':          'l3gen',
        'l3mapgen':       'SMI',           # Temporary(?)
        'Level 3 Binned': 'l3bin',
        'SMI':            'SMI',
        'smigen':         'SMI'
    }

    transitions = {
        'general' : {'L1A':'L1B', 'L1B': 'L2', 'L2': 'L3b',
                     'L3b': ['L3b', 'SMI', 'l3gen']},
        # 'modis' : {'L0': 'L1A', 'L1A':['GEO', 'L1B'], 'L1B': 'L2',
        #            'L2': 'L3b','L3b': ['L3b', 'SMI']}
    }

    def __init__(self, data_files_list, next_level, suite=None,
                 resolution=None, oformat=None):
        if len(data_files_list) == 0:
            err_msg = "Error! No data file specified for {0}.".format(
                self.__class__.__name__)
            sys.exit(err_msg)
        self.user_next_level = next_level
        if next_level in list(self.PROCESSING_LEVELS.keys()):
            self.next_level = self.PROCESSING_LEVELS[next_level]
        #elif next_level in namer_constants.PROCESSABLE_PROGRAMS:
        #    if len(data_files_list) == 1:
        #        file_list = data_files_list[0].name
        #    elif len(data_files_list) == 2:
        #        file_list = data_files_list[0].name + ' and ' + \
        #                    data_files_list[1].name
        #    else:
        #        file_list = ', '.join([str(df.name)
        #                               for df in data_files_list[:-1]])
        #        file_list += ', and ' + data_files_list[-1].name
        #    err_msg = 'Error! Cannot transition {0} to {1}.'.format(file_list,
        #                                                            next_level)
        #    sys.exit(err_msg)
        else:
            err_msg = 'Error!  "{0}" is not a recognized target output type.'.\
            format(next_level)
            sys.exit(err_msg)
        self.data_files = data_files_list
        self.data_files.sort()
        self.next_suffix = self._get_next_suffixes()
        self.transition_functions = self._get_transition_functions()
        self.transition_sequence = self._get_transition_sequence()
        if suite:
            if suite[0:1] == '_':
                self.suite = suite
            else:
                self.suite = '_' + suite
        else:
            self.suite = None
        if not (self.data_files[0].file_type in self.transition_functions):
            if (self.data_files[0].file_type in self.PROCESSING_LEVELS):
                for dfile in self.data_files:
                    dfile.file_type = self.PROCESSING_LEVELS[dfile.file_type]
        self.resolution = resolution
        self.oformat = oformat

    def _do_extension_substitution(self):
        """
        An internal method to do a simple substitution of the file's extension.
        This is just a placeholder and will eventually be removed.
        """
        # todo: remove this method when every transition is implemented.
        basename = os.path.split(self.data_files[0].name)[1]
        basename_parts = basename.rsplit('.', 2)
        suffix = 'unk'
        keys_list = list(self.next_suffix.keys())
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
        year = convert_str_to_int(date_str[0:4])
        mon = convert_str_to_int(date_str[5:7])
        dom = convert_str_to_int(date_str[8:10])
        hour = convert_str_to_int(time_str[0:2])
        mins = convert_str_to_int(time_str[3:5])
        secs = convert_str_to_int(time_str[6:8])
        dt_obj = datetime.datetime(year, mon, dom, hour, mins, secs)
        return dt_obj.strftime('%Y%j%H%M%S')

    def _get_data_type(self):
        """
        Returns the data type (usually GAC or LAC).
        """
        if 'Data Type' in self.data_files[0].metadata:
            return self.data_files[0].metadata['Data Type']
        else:
            return "LAC"

    def _get_end_doy_year(self):
        """
        Extract a day of year and year from an L0 file's metadata and return
        them as integer values .
        """
        if self.data_files[-1].end_time:
            year = convert_str_to_int(self.data_files[-1].end_time[0:4])
            day = convert_str_to_int(self.data_files[-1].end_time[4:7])
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

    def _get_extra_extensions(self):
        """
        Return "extra" extensions, if any.  Particularly meant for handling
        input file names like "A2014009000000.L1A_LAC.x.hdf".
        """
        extra_ext = None
        if len(self.data_files) == 1:
            base_name = os.path.basename(self.data_files[0].name)
            if base_name.count('.') > 1:
                #name_parts = re.split("""\.L.*?\.""", base_name)
                name_parts = re.split(r"\.L.*?\.", base_name)
                if len(name_parts) > 1:
                    extra_ext = name_parts[1]
        if self.oformat:
            file_formats = read_fileformats()
            if extra_ext:
                formats_re = ''
                for file_format in file_formats[:-1]:
                    if file_format[2] != '':
                        formats_re += ''.join(['(', file_format[2], '$)|'])
                formats_re += ''.join(['(', file_formats[-1][2], '$)'])
                extra_ext = re.sub(formats_re, '', extra_ext)
                extra_ext = '.'.join([extra_ext, find_extension(file_formats,
                                                                self.oformat)])
            else:
                format_ext = find_extension(file_formats, self.oformat)
                if format_ext:
                    extra_ext = '' + format_ext
        return extra_ext

    def _get_l1aextract_name(self):
        """
        Returns the output name from running one of the l1aextract_INST programs
        (where INST = "modis" or "seawifs" or "viirs").
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
        return '.L1B_' + self._get_data_type()

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
        elif self.data_files[0].metadata is not None:
            next_lvl_name = first_char +\
                            self._extract_l1_time(self.data_files[0].metadata['RANGEBEGINNINGDATE'],
                                                  self.data_files[0].metadata['RANGEBEGINNINGTIME']) +\
                            self._get_l1b_extension()
        return next_lvl_name

    def _get_l1brsgen_name(self):
        """
        An internal method to get the L1 browse file name.
        """
        ext = '.L1B_BRS.hdf'
        return self._get_single_file_basename() + ext

    def _get_l1mapgen_name(self):
        """
        An internal method to get the L1 mapped file name.
        """
        if self.data_files[0].file_type == 'Level 1A':
            ext = '.L1A_MAP.ppm'
        elif self.data_files[0].file_type == 'Level 1B':
            ext = '.L1B_MAP.ppm'
        else:
            ext = '.L1_MAP.ppm'
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
            if self.suite is None:
                next_lvl_name = basename + self._get_l2_extension() + '_OC'
            else:
                next_lvl_name = basename + self._get_l2_extension() + self.suite
        else:
            err_msg = 'Error!  Could not determine L2 name for {0}'.\
                      format(self.data_files[0].name)
            sys.exit(err_msg)
        return next_lvl_name

    def _get_l2brsgen_name(self):
        """
        An internal method to get the L1 browse file name.
        """
        ext = '.L2_BRS.hdf'
        return self._get_single_file_basename() + ext

    def _get_l2mapgen_name(self):
        """
        An internal method to get the L1 mapped file name.
        """
        ext = '.L2_MAP.ppm'
        return self._get_single_file_basename() + ext

    def _get_l3base_name(self):
        """
        An internal method to return the L3bin name from an L2 or
        L3bin file.
        """
        basename = ''
        first_char = self.get_platform_indicator()
        sday, syear = self._get_start_doy_year()
        eday, eyear = self._get_end_doy_year()
        if sday and syear and sday > 0 and syear > 0:
            sdate = datetime.datetime.strptime(str(syear) + '-' + str(sday),
                                               '%Y-%j')
        else:
            err_msg = 'Error! Cannot process start date data: year = {0}' \
            ', doy = {1}'.format(syear, sday)
            sys.exit(err_msg)
        if eday and eyear and eday > 0 and eyear > 0:
            edate = datetime.datetime.strptime(str(eyear) + '-' + str(eday),
                                               '%Y-%j')
        else:
            err_msg = 'Error! Cannot process end date data: year = {0},' \
            'doy = {1}'.format(eyear, eday)
            sys.exit(err_msg)
        days_diff = _get_days_diff(edate, sdate)
        if days_diff == 0:
            basename = '%s%d%03d' % (first_char, syear, sday)
        else:
            basename = '%s%d%03d%d%03d' % (first_char, syear, sday, eyear, eday)
        return basename

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
        days_diff = _get_days_diff(edate, sdate)

        if self.suite is None:
            self.suite = '_OC'
        if days_diff == 0:
            extension = '.L3b_DAY'
            next_lvl_name = '%s%d%03d%s%s' % (first_char, syear, sday, extension, self.suite)
        else:
            if days_diff == 7:
                extension = '.L3b_8D'
            else:
                extension = '.L3b_CU'
            next_lvl_name = '%s%d%03d%d%03d%s%s' % (first_char, syear, sday, 
                                                    eyear, eday, extension, self.suite)
        return next_lvl_name

    def _get_l3gen_name(self):
        """
        Returns a name for an L3 bin file generated from an L3 bin file run
        through l3gen.
        """
        next_lvl_name = ''
        basename = self._get_l3base_name()
        sday, syear = self._get_start_doy_year()
        eday, eyear = self._get_end_doy_year()
        if sday and syear and sday > 0 and syear > 0:
            sdate = datetime.datetime.strptime(str(syear) + '-' + str(sday),
                                               '%Y-%j')
        else:
            err_msg = 'Error! Cannot process start date data: year = {0}, doy = {1}'.format(syear, sday)
            sys.exit(err_msg)
        if eday and eyear and eday > 0 and eyear > 0:
            edate = datetime.datetime.strptime(str(eyear) + '-' + str(eday),
                                               '%Y-%j')
        else:
            err_msg = 'Error! Cannot process end date data: year = {0}, doy = {1}'.format(eyear, eday)
            sys.exit(err_msg)
        days_diff = _get_days_diff(edate, sdate)
        if self.suite is None:
            self.suite = '_OC'
        if days_diff == 0:
            extension = '.L3b_DAY' + self.suite
        elif days_diff == 7:
            extension = '.L3b_8D' + self.suite
        else:
            extension = '.L3b' + self.suite
        basename = self._get_l3base_name()
        next_lvl_name = ''.join([basename, extension])
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
            elif self.next_level in list(self.transition_functions[
                    self.data_files[0].file_type].keys()):
                next_level_name = self.transition_functions[\
                                  self.data_files[0].file_type]\
                [self.next_level]()
            else:
                err_msg = 'Error! Cannot transition {0} to {1}.'.format(
                    self.data_files[0].name, self.next_level)
                sys.exit(err_msg)
        extra_ext = self._get_extra_extensions()
        if extra_ext:
            if next_level_name.find(extra_ext) == -1:
                # extra_ext in not in the name yet, add it.
                if extra_ext[0] != '.':
                    next_level_name += '.' + extra_ext
                else:
                    next_level_name += extra_ext

        return next_level_name

    def _get_next_suffixes(self):
        """
        An internal method to set up the dictionary which tells what the
        suffix transitions should be.  Separated from __init__() so that
        it can be overridden.
        """
        return {'L1A' : 'L1B', 'L1B' : 'L2', 'L2' : 'L3b'}

    def get_platform_indicator(self):
        """
        Returns a character which indicates what platform (instrument) the
        data in the file is from.  This is usually used as the first character
        of an output file.
        """
        indicator_dict = {'Aquarius': 'Q', 'CZCS': 'C', 'GOCI': 'G',
                          'HICO': 'H',
                          'MERIS': 'M',
                          'MODIS Aqua':  'A', 'MODIS Terra': 'T',
                          'MOS': 'M', 'OCM2': 'O2_', 'OCTS': 'O',
                          'OLI': 'L', 'OSMI': 'K',
                          'SeaWiFS': 'S',
                          'VIIRS': 'V', 'VIIRSN': 'V'}

        if self.data_files[0].sensor in list(indicator_dict.keys()):
            indicator = indicator_dict[self.data_files[0].sensor]
        elif self.data_files[0].sensor == 'MODIS':
            base_file_name = os.path.basename(self.data_files[0].name)
            if base_file_name[0] == 'A':
                indicator = 'A'
            elif base_file_name[0] == 'T':
                indicator = 'T'
            elif base_file_name[0] == 'X':
                indicator = 'X'
            else:
                err_msg = 'Error!  Could not determine platform indicator for MODIS file {0}.'.\
                          format(self.data_files[0].name)
                sys.exit(err_msg)
        else:
            err_msg = 'Error!  Platform indicator, {0}, for {1} is not known.'.\
                      format(self.data_files[0].sensor, self.data_files[0].name)
            sys.exit(err_msg)
        for dfile in self.data_files[1:]:
            if dfile.sensor in list(indicator_dict.keys()):
                if indicator != indicator_dict[dfile.sensor]:
                    indicator = 'X'
                    break
            else:
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

    def _get_l3mapgen_name(self):
        """
        Returns the output name from smigen for an L3 Binned file or group
        of files.
        """
        # if not self.suite:
        #     err_msg = 'Error! A suite must be defined for {0}.'.\
        #               format(self.user_next_level)
        #     sys.exit(err_msg)
        first_char = self.get_platform_indicator()
        if self.data_files[0].metadata:
            sday, syear = get_start_day_year(self.data_files[0].metadata)
            eday, eyear = get_end_day_year(self.data_files[0].metadata)

            if 'Input Parameters' in self.data_files[0].metadata and\
               'SUITE' in self.data_files[0].metadata['Input Parameters'] and\
               self.data_files[0].metadata['Input Parameters']['SUITE'].strip() != '':
                suite = '_' + self.data_files[0].metadata['Input Parameters']['SUITE'].strip()
            else:
                suite = ''
        else:
            sday, syear = self._get_start_doy_year()
            eday, eyear = self._get_end_doy_year()
            suite = ''

        sdate = datetime.datetime.strptime(str(syear)+'-'+str(sday), '%Y-%j')
        edate = datetime.datetime.strptime(str(eyear)+'-'+str(eday), '%Y-%j')

        days_diff = (edate - sdate).days
        if days_diff == 0:
            extension = '.L3m_DAY'
            smi_name = '{0}{1:04d}{2:03d}{3}{4}'.format(first_char, syear, sday,
                                                        extension, suite)
        else:
            if days_diff == 7:
                extension = '.L3m_8D'
            else:
                extension = '.L3m_CU'
            smi_name = '{0}{1:04d}{2:03d}{3:04d}{4:03d}{5}{6}'.format(
                first_char, syear, sday, eyear, eday, extension, suite)
        if self.suite:
            if self.suite.startswith('_'):
                smi_name += self.suite
            else:
                smi_name += '_' + self.suite
        if self.resolution:
            if self.resolution.startswith('_'):
                smi_name += self.resolution
            else:
                smi_name += '_' + self.resolution

        return smi_name

    def _get_start_doy_year(self):
        """
        Extract a day of year and year from a file's metadata and return
        them as integer values .
        """
        if self.data_files[0].end_time:
            year = convert_str_to_int(self.data_files[0].start_time[0:4])
            day = convert_str_to_int(self.data_files[0].start_time[4:7])
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

    def _get_transition_functions(self):
        """
        An internal method to set up the "table" of functions to be
        called for each level of processing.  Separated from __init__() so it
        can be overridden.
        """
        return {'Level 1A': {'Level 1B': self._get_l1b_name,
                             'l1mapgen': self._get_l1mapgen_name,
                             'Level 2': self._get_l2_name},
                'Level 1B': {'Level 2': self._get_l2_name,
                             'l1brsgen': self._get_l1brsgen_name,
                             'l1mapgen': self._get_l1mapgen_name},
                'Level 2': {'l2bin': self._get_l3bin_name,
                            'l2extract': self._get_l2extract_name,
                            'l3bin': self._get_l3bin_name,
                            'l2brsgen': self._get_l2brsgen_name,
                            'l2mapgen': self._get_l2mapgen_name},
                'Level 3 Binned': {'l3bin' : self._get_l3bin_name,
                                   'SMI' :   self._get_l3mapgen_name,
                                   'l3gen':  self._get_l3gen_name}
               }

    def _get_transition_sequence(self):
        """
        An internal method to set up the sequence of transitions.  Separated
        from __init__() so it can be overridden.
        """
        return ['L1A', 'L1B', 'L2', 'L3bin']


#########################################

class MerisNextLevelNameFinder(NextLevelNameFinder):
    """
    A class to determine what the standard OBPG filename would be
    for MERIS files when the given input name is run through the next
    level of OBPG processing.
    """

    def __init__(self, data_files_list, next_level, suite=None,
                 resolution=None, oformat=None):
        super(MerisNextLevelNameFinder, self).__init__(data_files_list,
                                                       next_level, suite,
                                                       resolution)

    def _get_l2_extension(self):
        """
        Return the appropriate extension for an L2 file.
        """
        ext = '.BOGUS_MERIS_L2_EXTENSION'
        if 'SPH_DESCRIPTOR' in self.data_files[0].metadata:
            ext = ''.join(['.L2_',
                           self.data_files[0].metadata['SPH_DESCRIPTOR'].\
                                split('_')[1]])
        #for data_file in self.data_files:
        #    if data_file.name.find('GAC') != -1:
        #        ext = '.L2_GAC'
        #        break
        return ext

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
        'level 1a':          'Level 1A',
        'geo':               'GEO',
        'geogen':            'GEO',
        'modis_GEO.py':      'GEO',
        'GEO':               'GEO',
        'l1aextract_modis':  'l1aextract_modis',
        'l1bgen':            'Level 1B',
        'level 1b':          'Level 1B',
        'Level 1B':          'Level 1B',
        'modis_L1B.py':      'Level 1B',
        'l1brsgen':          'l1brsgen',
        'l1mapgen':          'l1mapgen',
        'l2gen':             'Level 2',
        'Level 2':           'Level 2',
        'level 2':           'Level 2',
        'l2bin':             'l2bin',
        'l2brsgen':          'l2brsgen',
        'l2extract':         'l2extract',
        'l2mapgen':          'l2mapgen',
        'Level 3 Binned':    'l3bin',
        'l3bin':             'l3bin',
        'L3b':               'l3bin',
        'l3gen':             'l3gen',
        'l3mapgen':          'SMI',           # Temporary(?)
        'SMI':               'SMI',
        'smigen':            'SMI'
    }

    def __init__(self, data_files_list, next_level, suite=None,
                 resolution=None, oformat=None):
        super(ModisNextLevelNameFinder, self).__init__(data_files_list,
                                                       next_level, suite,
                                                       resolution, oformat)

    def _extract_l1_time(self, date_str, time_str):
        """
        An internal method to extract the date/time stamp from L1 files.
        """
        year = convert_str_to_int(date_str[0:4])
        mon = convert_str_to_int(date_str[5:7])
        dom = convert_str_to_int(date_str[8:10])
        hour = convert_str_to_int(time_str[0:2])
        mins = convert_str_to_int(time_str[3:5])
        secs = 0
        dt_obj = datetime.datetime(year, mon, dom, hour, mins, secs)
        return dt_obj.strftime('%Y%j%H%M%S')

    def _get_aqua_l0_to_l1a_name(self):
        """
        An internal method to return the L1A name from an Aqua L0 file.
        """
        time_stamp = get_l0_timestamp(self.data_files[0].name)
        time_stamp = ''.join([time_stamp[:-2], '00'])
        l1a_name = ''.join(['A', time_stamp, self._get_l1a_extension()])
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
            time_stamp = self._extract_l1_time(
                self.data_files[0].metadata['RANGEBEGINNINGDATE'],
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
            start_time = ''.join([self.data_files[0].start_time[:-2], '00'])
        elif self.data_files[0].metadata:
            start_time = ''.join([self._extract_l1_time(
                self.data_files[0].metadata['RANGEBEGINNINGDATE'],
                self.data_files[0].metadata['RANGEBEGINNINGTIME'])[:-2], '00'])
        next_lvl_name = ''.join([first_char, start_time,
                                 self._get_l2_extension()])
        if self.suite is None:
            next_lvl_name += '_OC'
        else:
            next_lvl_name += self.suite
        # if self.oformat:
        #     file_formats = read_fileformats()
        #     ext = find_extension(file_formats, self.oformat)
        #     if ext:
        #         next_lvl_name = ''.join([next_lvl_name, '_', ext])
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
        next_level_name = None
        if len(self.data_files) > 0:
            if (self.data_files[0].file_type == 'Level 0'):
                next_level_name = self._get_l1a_name()
            elif self.data_files[0].file_type in self.transition_functions:
                if isinstance(self.transition_functions[self.data_files[0].file_type],
                              types.FunctionType) or \
                     isinstance(self.transition_functions[self.data_files[0].file_type],
                                types.MethodType):
                    next_level_name = self.transition_functions[self.data_files[0].file_type]()

                elif self.next_level in list(self.transition_functions[
                        self.data_files[0].file_type].keys()):
                    next_level_name = self.transition_functions[\
                                      self.data_files[0].file_type]\
                                      [self.next_level]()
        extra_ext = self._get_extra_extensions()
        if extra_ext:
            if extra_ext[0] != '.':
                next_level_name += '.' + extra_ext
            else:
                next_level_name += extra_ext
        if next_level_name:
            return next_level_name
        else:
            err_msg = 'Error! Cannot transition {0} to {1}.'.format(
                self.data_files[0].name, self.next_level)
            sys.exit(err_msg)

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
        elif self.data_files[0].sensor.find('MODIS') != -1:
            if 'platform' in self.data_files[0].metadata:
                if self.data_files[0].metadata['platform'].find('Aqua') != -1:
                    indicator = 'A'
                elif self.data_files[0].metadata['platform'].find('Terra') != \
                        -1:
                    indicator = 'T'
            elif 'Mission' in self.data_files[0].metadata:
                if self.data_files[0].metadata['Mission'].find('Aqua') != -1:
                    indicator = 'A'
                elif self.data_files[0].metadata['Mission'].find('Terra') != -1:
                    indicator = 'T'

        elif self.data_files[0].metadata is not None:
            if 'LONGNAME' in list(self.data_files[0].metadata.keys()):
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

    def _get_transition_sequence(self):
        """
        Returns the sequence of transitions.  Separated from __init__() so
        it can be overridden.
        """
        return ['L1A', 'L1B', 'L2', 'L3bin']

    def _get_next_suffixes(self):
        """
        An internal method to set the dictionary which tells what the
        suffix transitions should be.
        """
        return {'L0': 'L1A', 'L1A' : 'L1B', 'L1B' : 'L2', 'L2' : 'L3b'}

    def _get_transition_functions(self):
        """
        An internal method to set up the "table" of functions to be
        called for each level of processing.
        """
        return {'Level 0': self._get_l1a_name,
                'Level 1A': {'GEO': self._get_geo_name,
                             'Level 1B': self._get_l1b_name,
                             'l1aextract_modis' : self._get_l1aextract_name,
                             'l1bgen' : self._get_l1b_name,
                             'Level 2' : self._get_l2_name},
                'Level 1B': {'Level 2': self._get_l2_name,
                             'l1brsgen': self._get_l1brsgen_name,
                             'l1mapgen': self._get_l1mapgen_name},
                'Level 2': {'l2bin': self._get_l3bin_name,
                            'l2extract': self._get_l2extract_name,
                            'l3bin': self._get_l3bin_name,
                            'l2brsgen': self._get_l2brsgen_name,
                            'l2mapgen': self._get_l2mapgen_name},
                'Level 3 Binned': {'l3bin' : self._get_l3bin_name,
                                   'SMI' : self._get_l3mapgen_name,
                                   'l3gen': self._get_l3gen_name}
               }

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
        'level 1b':     'Level 1B',
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
        'l3gen':        'l3gen',
        'l3mapgen':     'SMI',           # Temporary(?)
        'SMI':          'SMI',
        'smigen':       'SMI'
    }

    def __init__(self, data_files_list, next_level, suite=None,
                 resolution=None, oformat=None):
        super(SeawifsNextLevelNameFinder, self).__init__(data_files_list,
                                                         next_level, suite,
                                                         resolution, oformat)

    def get_platform_indicator(self):
        """
        Returns a character which indicates what platform (instrument) the
        data in the file is from.  This is usually used as the first character
        of an output file.
        """
        return 'S'

    def _get_transition_functions(self):
        """
        An internal method to set up the "table" of functions to be
        called for each level of processing.
        """
        return {'Level 1A': {'Level 1B': self._get_l1b_name,
                             'l1aextract_seawifs' : self._get_l1aextract_name,
                             'l1bgen' : self._get_l1b_name,
                             'l1brsgen': self._get_l1brsgen_name,
                             'l1mapgen': self._get_l1mapgen_name,
                             'Level 2' : self._get_l2_name},
                'Level 1B': {'Level 2': self._get_l2_name,
                             'l1brsgen': self._get_l1brsgen_name,
                             'l1mapgen': self._get_l1mapgen_name},
                'Level 2': {'l2bin': self._get_l3bin_name,
                            'l2extract': self._get_l2extract_name,
                            'l3bin': self._get_l3bin_name,
                            'l2brsgen': self._get_l2brsgen_name,
                            'l2mapgen': self._get_l2mapgen_name},
                'Level 3 Binned': {'l3bin' : self._get_l3bin_name,
                                   'l3gen': self._get_l3gen_name,
                                   'l3mapgen' : self._get_l3mapgen_name,
                                   'SMI' : self._get_l3mapgen_name}
               }
