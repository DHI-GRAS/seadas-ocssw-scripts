#!/usr/bin/env python

"""
A class for determining the OBPG type of a file.
"""

__author__ = 'melliott'

import calendar
import datetime
import modules.MetaUtils
import optparse
import os
import re
import subprocess
import sys

def convert_millisecs_to_time_str(millisecs):
    """
    Converts a number of milliseconds to a string representing the time of day.
    """
    secs = millisecs / 1000
    hrs = secs / 3600
    secs = secs - (hrs * 3600)
    mins = secs / 60
    secs = secs - (mins * 60)
    tm_str = '{0:02}{1:02}{2:02}'.format(hrs, mins, secs)
    return tm_str

def get_timestamp_from_month_day(sdate, stime):
    """
    Creates timestamp for VIIRS L1.
    """
    year = int(sdate[0:4])
    mon = int(sdate[4:6])
    dom = int(sdate[6:8])
    hrs = int(stime[0:2])
    mins = int(stime[2:4])
    secs = int(stime[4:6])
    dt_obj = datetime.datetime(year, mon, dom, hrs, mins, secs)
    return dt_obj.strftime('%Y%j%H%M%S')

def get_timestamp_from_year_day_mil(year, doy, millisecs):
    """
    Return a timestamp in the YYYYDDDHHMMSS form from a given year (yr), day
    of year (doy) and milliseconds (after 00:00 - millisecs).
    """
    time_str = convert_millisecs_to_time_str(millisecs)
    timestamp = '{0:04}{1:03}{2}'.format(year, doy, time_str)
    return timestamp

class ObpgFileTyper(object):
    """
    A class containing methods for finding the type of an OBPG file (e.g.
    MODIS L2b, SeaWiFS L1A, Aquarius L3m, etc.
    """

    def __init__(self, fpath):
        """
        Save the path of the file in question and set up default
        values for several thing still to be found.
        """
        if os.path.exists(fpath):
            self.file_path = fpath
            self.file_type = 'unknown'
            self.instrument = 'unknown'
            self.start_time = 'unknown'
            self.end_time = 'unknown'
            self.attributes = None
            self.l0_data = None
        else:
            err_msg = "Error! File {0} could not be found.".format(fpath)
            sys.exit(err_msg)

#    def _convert_month_day_to_doy(self, sdate, stime):
#        """
#        Creates timestamp for VIIRS L1.
#        """
#        year = int(sdate[0:4])
#        mon = int(sdate[4:6])
#        dom = int(sdate[6:8])
#        hrs = int(stime[0:2])
#        mins = int(stime[2:4])
#        secs = int(stime[4:6])
#        dt_obj = datetime.datetime(year, mon, dom, hrs, mins, secs)
#        return dt_obj.strftime('%Y%j%H%M%S')

    def _create_meris_l1b_timestamp(self, time_str):
        """
        Returns a properly formatted date/time stamp for MERIS L1B files from
        an attribute in the file.
        """
        # Todo: Check that MERIS' and Python's month abbreviations match up ...
        month_abbrs = dict((v.upper(), k) for k, v in
                            enumerate(calendar.month_abbr))
        year = int(time_str[7:11])
        mon = int(month_abbrs[time_str[3:6]])
        dom = int(time_str[0:2])
        hrs = int(time_str[12:14])
        mins = int(time_str[15:17])
        secs = int(time_str[18:20])
        dt_obj = datetime.datetime(year, mon, dom, hrs, mins, secs)
        return dt_obj.strftime('%Y%j%H%M%S')

    def _create_modis_l1_timestamp(self, rng_date, rng_time):
        """
        Returns a date/time stamp for a MODIS L1 file from the appropriate
        RANGINGDATE and RANGINGTIME attributes.  The returned date/time stamp
        is of form YYYYDDDHHMMSS, where YYYY = year, DDD = day of year,
        HH = hour, MM = minute, and SS = second.
        """
        year = int(rng_date[0:4])
        mon = int(rng_date[5:7])
        dom = int(rng_date[8:10])
        hrs = int(rng_time[0:2])
        mins = int(rng_time[3:5])
        secs = int(rng_time[6:8])
        dt_obj = datetime.datetime(year, mon, dom, hrs, mins, secs)
        return dt_obj.strftime('%Y%j%H%M%S')

    def _create_octs_l1_timestamp(self, dt_str):
        """
        Creates a timestamp for an OCTS L1.
        """
        year = int(dt_str[0:4])
        mon = int(dt_str[4:6])
        dom = int(dt_str[6:8])
        hrs = int(dt_str[9:11])
        mins = int(dt_str[12:14])
        secs = int(dt_str[15:17])
        dt_obj = datetime.datetime(year, mon, dom, hrs, mins, secs)
        return dt_obj.strftime('%Y%j%H%M%S')

    def _get_data_from_anc_attributes(self):
        """
        Processes Ancillary data files.
        """
        instrument = 'Ancillary'
        file_type = self.attributes['Data Type']
        return file_type, instrument

    def _get_data_from_l0_attributes(self):
        """
        Get the instrument and file type from the attributes for an L0 file.
        """
        file_type = 'unknown'
    #    instrument = 'unknown'
        title_parts = self.attributes['Title'].split()
        if title_parts[1].find('Level-0') != -1:
            file_type = 'Level 0'
        instrument = title_parts[0].strip()
        return file_type, instrument

    def _get_data_from_l1_attributes(self, title):
        """
        Get the instrument and file type from the attributes for an L1 file.
        """
        file_type = 'Level 1'
        instrument = 'unknown'
        possible_levels = {'Level 1A': 'Level 1A', 'Level-1A': 'Level 1A',
                           'L1A': 'Level 1A', 'L1a': 'Level 1A',
                           'Level 1B': 'Level 1B', 'Level-1B': 'Level 1B',
                           'L1B': 'Level 1B', 'L1b': 'Level 1B'}
#        ks = known_sensors
        if title.find('Level 1') != -1:
            working_title = title.replace('Level 1', 'Level-1')
        else:
            working_title = title
        working_title = re.sub("""^['"](.*)['"].*;$""", '\g<1>', working_title)
        title_parts = working_title.split()
        for part in title_parts:
            if part in KNOWN_SENSORS:
                instrument = part
            if part in possible_levels:
                file_type = possible_levels[part]
        if title.find('Browse Data') != -1:
            file_type += ' Browse Data'
        return file_type, instrument

    def _get_data_from_l2_attributes(self):
        """
        Get the instrument and file type from the attributes for an 20 file.
        """
        title_parts = self.attributes['Title'].split()
        file_type = 'Level 2'
        if self.attributes['Title'].find('Browse Data') != -1:
            file_type += ' Browse Data'
        instrument = title_parts[0].strip()
        return file_type, instrument

    def _get_data_from_l3_attributes(self):
        """
        Get the instrument and file type from the attributes for an L3 file.
        """
        file_type = 'unknown'
        if self.attributes['Title'].find('Level-3 Binned') != -1:
            file_type = 'Level 3 Binned'
        elif self.attributes['Title'].find('Level-3 Standard Mapped Image') != -1:
            file_type = 'Level 3 SMI'
        instrument = self._get_instrument()
        return file_type, instrument

    def _get_instrument(self):
        """
        Get the instrument from the attributes.
        """
        instrument = 'unknown'
        title_parts = self.attributes['Title'].split()
        if title_parts[0].find('Level') == -1:
            instrument = title_parts[0].strip()
        if not (instrument in KNOWN_SENSORS):
            if 'Sensor Name' in self.attributes:
                instrument = self.attributes['Sensor Name'].strip()
            if ('Sensor' in self.attributes) and not \
               (instrument in KNOWN_SENSORS):
                instrument = self.attributes['Sensor'].strip()
        return instrument

    def _get_l0_constructor_data(self):
        """
        Try to get data from the MODIS L0 constructor for this file.
        """
        l0cnst_results = None
        cmd = ' '.join(['l0cnst_write_modis', '-n', self.file_path])
        try:
            l0_out = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE).communicate()[0]
            out_lines = l0_out.split('\n')
            is_l0 = False
            for line in out_lines:
                if line.find('Total packets') != -1:
                    parts = line.split()
                    packets_read = float(parts[0])
                    if packets_read > 0.0:
                        is_l0 = True
                    break
            if is_l0:
                starttime, stoptime = self._get_l0_start_stop_times(out_lines)
                if starttime and stoptime:
                    l0cnst_results = {'starttime' : starttime,
                                      'stoptime' : stoptime}
        except:
            l0cnst_results = None
        return l0cnst_results

    def get_file_attributes(self):
        """
        API method to return the file's attributes.
        """
        return self.attributes

    def get_file_times(self):
        """
        Returns the start and end time for a file.
        """
#        print 'self.instrument: "' + self.instrument + '"'
        start_time = 'unable to determine start time'
        end_time = 'unable to determine end time'
        if self.instrument == 'VIIRS' and self.file_type == 'SDR':
            start_time = get_timestamp_from_month_day(
                                    self.attributes['Beginning_Date'],
                                    self.attributes['Beginning_Time'])
            end_time = get_timestamp_from_month_day(
                                    self.attributes['Ending_Date'],
                                    self.attributes['Ending_Time'])
        elif self.file_type.find('Level 1') != -1:
            start_time, end_time = self._get_l1_times()
        elif self.file_type.find('Level 2') != -1 or \
           self.file_type.find('Level 3') != -1:
            try:
                start_time = self.attributes['Start Time'][0:13]
                end_time = self.attributes['End Time'][0:13]
            except KeyError:
                if self.instrument.find('Aquarius') != -1:
                    stime_str = convert_millisecs_to_time_str(
                                      int(self.attributes['Start Millisec']))
                    start_time = '{0:04}{1:03}{2}'.format(
                                         int(self.attributes['Start Year']),
                                         int(self.attributes['Start Day']),
                                         stime_str)
                    etime_str = convert_millisecs_to_time_str(
                        int(self.attributes['Start Millisec']))
                    end_time = '{0:04}{1:03}{2}'.format(
                        int(self.attributes['End Year']),
                        int(self.attributes['End Day']),
                        etime_str)
                else:
                    raise
        elif self.file_type.find('Level 0') != -1:
            if isinstance(self.l0_data, dict):
                start_time = self.l0_data['starttime']
                end_time = self.l0_data['stoptime']
            else:
                for line in self.l0_data:
                    if line.find('starttime') != -1:
                        time_part = line.split('=')[1]
                        start_time = time_part[0:4] + time_part[5:7] + \
                                     time_part[8:10] + time_part[11:13] + \
                                     time_part[14:16] + time_part[17:19]
                    if line.find('stoptime') != -1:
                        time_part = line.split('=')[1]
                        end_time = time_part[0:4] + time_part[5:7] + \
                                   time_part[8:10] + time_part[11:13] +\
                                   time_part[14:16] + time_part[17:19]
        return start_time, end_time

    def get_file_type(self):
        """
        Returns what type (L1A, L2, etc.) a file is and what
        platform/sensor/instrument made the observations.
        """
        orig_path = None
        self._read_metadata()
        if self.attributes:
            if 'Title' in self.attributes or 'title' in self.attributes:
                self._get_type_using_title()
            elif 'ASSOCIATEDINSTRUMENTSHORTNAME' in self.attributes:
                self._get_type_using_short_name()
            elif 'PRODUCT' in self.attributes:
                if self.attributes['PRODUCT'].find('MER_') != -1:
                    self.instrument = 'MERIS'
                    self.file_type = 'Level 1B'
            elif 'Instrument_Short_Name' in self.attributes:
                self.instrument = self.attributes['Instrument_Short_Name']
                if self.instrument == 'VIIRS':
                    if 'N_Dataset_Type_Tag' in self.attributes:
                        self.file_type = self.attributes['N_Dataset_Type_Tag']
        else:
            self._get_type_using_l0_cnst()
        if self.instrument.find('MODISA') != -1:
            self.instrument = 'MODIS Aqua'
        if self.instrument.find('MODIST') != -1:
            self.instrument = 'MODIS Terra'
        if orig_path:
            self.file_path = orig_path
        return self.file_type, self.instrument

    def _get_l0_start_stop_times(self, l0_lines):
        """
        Returns the start time and stop time if found in l0_lines.
        """
        starttime = None
        stoptime = None
        for line in l0_lines:
            if line.find('starttime') != -1:
                starttime = line.strip().split('=')[1]
            if line.find('stoptime') != -1:
                stoptime = line.strip().split('=')[1]
        return starttime, stoptime

    def _get_l1_times(self):
        """
        Determines the times for Level 1 files.
        """
        start_time = None
        end_time = None
        if self.instrument.find('SeaWiFS')!= -1 or\
           self.instrument.find('Aquarius') != -1 or\
           self.instrument.find('CZCS') != -1 or\
           self.instrument.find('MOS') != -1 or\
           self.instrument.find('OSMI') != -1:
            start_time = self.attributes['Start Time'][0:13]
            end_time = self.attributes['End Time'][0:13]
        elif self.instrument.find('MODIS') != -1:
            start_time = self._create_modis_l1_timestamp(
                self.attributes['RANGEBEGINNINGDATE'],
                self.attributes['RANGEBEGINNINGTIME'])
            end_time = self._create_modis_l1_timestamp(
                self.attributes['RANGEENDINGDATE'],
                self.attributes['RANGEENDINGTIME'])
        elif self.instrument.find('OCTS') != -1:
            start_time = self._create_octs_l1_timestamp(
                self.attributes['Start Time'])
            end_time = self._create_octs_l1_timestamp(
                self.attributes['End Time'])
        elif self.instrument.find('MERIS') != -1:
            if 'FIRST_LINE_TIME' in self.attributes:
                start_time = self._create_meris_l1b_timestamp(
                    self.attributes['FIRST_LINE_TIME'])
                end_time = self._create_meris_l1b_timestamp(
                    self.attributes['LAST_LINE_TIME'])
            else:
                start_time = self._create_meris_l1b_timestamp(
                    self.attributes['start_date'].strip('"'))
                end_time = self._create_meris_l1b_timestamp(
                    self.attributes['stop_date'].strip('"'))
        elif self.instrument.find('OCM2') != -1:
            #yr, doy, millisecs
            start_time = get_timestamp_from_year_day_mil(\
                self.attributes['Start Year'],
                self.attributes['Start Day'],
                self.attributes['Start Millisec'])
            end_time = get_timestamp_from_year_day_mil(\
                self.attributes['End Year'],
                self.attributes['End Day'],
                self.attributes['End Millisec'])
        elif self.instrument.find('HICO') != -1:
            start_time = get_timestamp_from_month_day(\
                self.attributes['Beginning_Date'],
                self.attributes['Beginning_Time'])
            end_time = get_timestamp_from_month_day(\
                self.attributes['Ending_Date'],
                self.attributes['Ending_Time'])
        return start_time, end_time

    def _get_type_using_l0_cnst(self):
        """
        Determines the type info based on results of l0cnst_write_modis.
        """
        l0cnst_results = self._get_l0_constructor_data()
        if l0cnst_results is not None:
            self.l0_data = l0cnst_results
            self.file_type = 'Level 0'
            self.instrument = 'MODIS'
            if re.search(r'^[aA]|^MOD00.P|^MYD\S+.A|^P1540064',
                         os.path.basename(self.file_path)):
                self.instrument = ' '.join([self.instrument, 'Aqua'])
            elif re.search(r'^[tT]|^MOD\S+.A|^P0420064',
                           os.path.basename(self.file_path)):
                self.instrument = ' '.join([self.instrument, 'Terra'])

    def _get_type_using_short_name(self):
        """
        Determines the type based on the short name.
        """
        self.instrument = self.attributes['ASSOCIATEDINSTRUMENTSHORTNAME']
        if 'ASSOCIATEDPLATFORMSHORTNAME' in self.attributes:
            self.instrument = ' '.join([self.instrument,
                             self.attributes['ASSOCIATEDPLATFORMSHORTNAME']])
        if 'LONGNAME' in self.attributes:
            if self.attributes['LONGNAME'].find('Geolocation') != -1:
                self.file_type = 'GEO'
            elif self.attributes['LONGNAME'].find('L1A') != -1:
                self.file_type = 'Level 1A'
            elif self.attributes['LONGNAME'].find('L1B') != -1:
                self.file_type = 'Level 1B'

    def _get_type_using_title(self):
        """
        Determines the type based on the title field.
        """
        if 'Title' in self.attributes:
            title = self.attributes['Title']
        else:
            title = self.attributes['title']
        if (title.find('Level-1') != -1) or (title.find('Level 1') != -1) or \
           (title.find('L1') != -1):
            self.file_type, self.instrument = \
            self._get_data_from_l1_attributes(title)
        elif title.find('Level-2') != -1 or title.find('Level 2') != -1:
            self.file_type, self.instrument = \
            self._get_data_from_l2_attributes()
        elif title.find('Level-3') != -1:
            self.file_type, self.instrument = \
            self._get_data_from_l3_attributes()
        elif title.find('Level-0') != -1:
            self.file_type, self.instrument = \
            self._get_data_from_l0_attributes()
        elif title.find('Ancillary') != -1:
            self.file_type, self.instrument = \
            self._get_data_from_anc_attributes()

    def _read_metadata(self):
        """
        Using the MetaUtils.readMetadata function, reads the metadata and loads
        it into the attributes member variable.
        """
        try:
            if os.path.islink(self.file_path):
                self.file_path = os.path.realpath(self.file_path)
            attrs = modules.MetaUtils.readMetadata(self.file_path)
            if not (attrs is None):
                self.attributes = attrs
        except SystemExit:
            # readMetadata calls sys.exit() when it can't find attributes
            # to process, but we don't want to exit here.
            pass
        except TypeError:
            pass

#######################################################################

def main():
    """
    Main function to drive the program when invoked as a program.
    """
    ver = '0.5-beta'
    use_msg = 'usage: %prog [options] FILE_NAME [FILE_NAME ...]'
    ver_msg = ' '.join(['%prog', ver])
    cl_parser = optparse.OptionParser(usage=use_msg, version=ver_msg)
    (opts, args) = process_command_line(cl_parser)

    if len(args) > 0:
        for arg in args:
            file_typer = ObpgFileTyper(arg)
            (obpg_file_type, instrument) = file_typer.get_file_type()
            output = ''
            if obpg_file_type == 'unknown':
                if instrument != 'unknown':
                    output = '{0}: {1}: unknown'.format(os.path.basename(arg),
                                                        instrument)
                else:
                    output = '{0}: unknown: unknown'.format(
                                os.path.basename(arg))
            else:
                if instrument != 'unknown':
                    output = '{0}: {1}: {2}'.format(os.path.basename(arg), 
                                                    instrument, obpg_file_type)
                else:
                    output = '{0}: unknown: {1}'.format(os.path.basename(arg), 
                                                        obpg_file_type)
            if opts.times:
                if obpg_file_type != 'unknown' and instrument != 'unknown':
                    start_time, end_time = file_typer.get_file_times()
                    output += ': {0} : {1}'.format(start_time, end_time)
                else:
                    output += ': unable to determine file start and end times'
            print output
    else:
        print '\nError!  No file specified for type identification.\n'
        cl_parser.print_help()
    return 0

def process_command_line(cl_parser):
    """
    Uses optparse to get the command line options & arguments.
    """
    cl_parser.add_option('-t', '--times', action='store_true',
                         dest='times', default=False,
                         help='output start and end times for the file(s)')
    (opts, args) = cl_parser.parse_args()
    return opts, args

#######################################################################

KNOWN_SENSORS = ['Aquarius', 'CZCS', 'HICO',
                 'HMODISA', 'HMODIST', 'MERIS', 'MODISA',
                 'MODIS Aqua', 'MODIST', 'MODIS Terra',
                 'MOS', 'OCM2', 'OCTS',
                 'OSMI','SeaWiFS']

if __name__ == '__main__':
    sys.exit(main())
