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

class ObpgFileTyper(object):

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
        else:
            err_msg = "Error! File {0} could not be found.".format(fpath)
            sys.exit(err_msg)

    def _create_meris_l1b_timestamp(self, time_str):
        """
        Returns a properly formatted date/time stamp for MERIS L1B files from
        an attribute in the file.
        """
        # Todo: Check that MERIS' and Python's month abbreviations match up ...
        month_abbrs = dict((v.upper(), k) for k, v in enumerate(calendar.month_abbr))
        yr = int(time_str[7:11])
        mon = int(month_abbrs[time_str[3:6]])
        dom = int(time_str[0:2])
        hrs = int(time_str[12:14])
        mins = int(time_str[15:17])
        secs = int(time_str[18:20])
        dt_obj = datetime.datetime(yr, mon, dom, hrs, mins, secs)
        return dt_obj.strftime('%Y%j%H%M%S')

    def _create_modis_l1_timestamp(self, rng_date, rng_time):
        """
        Returns a date/time stamp for a MODIS L1 file from the appropriate
        RANGINGDATE and RANGINGTIME attributes.  The returned date/time stamp
        is of form YYYYDDDHHMMSS, where YYYY = year, DDD = day of year,
        HH = hour, MM = minute, and SS = second.
        """
        yr = int(rng_date[0:4])
        mon = int(rng_date[5:7])
        dom = int(rng_date[8:10])
        hrs = int(rng_time[0:2])
        mins = int(rng_time[3:5])
        secs = int(rng_time[6:8])
        dt_obj = datetime.datetime(yr, mon, dom, hrs, mins, secs)
        return dt_obj.strftime('%Y%j%H%M%S')

    def _create_octs_l1_timestamp(self, dt_str):
        """
        Creates a timestamp for an OCTS L1.
        """
        yr = int(dt_str[0:4])
        mon = int(dt_str[4:6])
        dom = int(dt_str[6:8])
        hrs = int(dt_str[9:11])
        mins = int(dt_str[12:14])
        secs = int(dt_str[15:17])
        dt_obj = datetime.datetime(yr, mon, dom, hrs, mins, secs)
        return dt_obj.strftime('%Y%j%H%M%S')

    def _create_viirs_l1_timestamp(self, sdate, stime):
        """
        Creates timestamp for VIIRS L1.
        """
        yr = int(sdate[0:4])
        mon = int(sdate[4:6])
        dom = int(sdate[6:8])
        hrs = int(stime[0:2])
        mins = int(stime[2:4])
        secs = int(stime[4:6])
        dt_obj = datetime.datetime(yr, mon, dom, hrs, mins, secs)
        return dt_obj.strftime('%Y%j%H%M%S')
#        return '-'.join([sdate[0:4],sdate[4:6],sdate[6:8]]) + 'T' + ':'.join([stime[0:2],stime[2:4],stime[4:len(stime)]])

    def _get_data_from_ancillary_attributes(self):
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
        file_type = 'unknown'
        instrument = 'unknown'
        if title.find('Level 1') != -1:
            working_title = title.replace('Level 1', 'Level-1')
        else:
            working_title = title
        title_parts = working_title.split()
        if title_parts[1].find('Level-1') != -1 or \
           title_parts[1].find('Level 1') != -1:
            if title_parts[1].find('Level-1A') != -1 or \
               title_parts[1].find('Level 1A') != -1:
                file_type = 'Level 1A'
            elif title_parts[1].find('Level-1B') != -1:
                file_type = 'Level 1B'
            else:
                file_type = 'Level 1'
            instrument = title_parts[0].strip()
        else:
            for title_pos, part in enumerate(title_parts):
                if part.find('L1') != -1:
                    break
            if title_parts[title_pos].upper().find('L1A') != -1:
                file_type = 'Level 1A'
            elif title_parts[title_pos].upper().find('L1B') != -1:
                file_type = 'Level 1B'
            else:
                file_type = 'Level 1'
            for inst_pos, part in enumerate(title_parts):
                for sensor in known_sensors:
                    if part.find(sensor) != -1:
                        instrument = sensor
                        break
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
    #    title_parts = attributes['Title'].split()
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
        if not (instrument in known_sensors):
            if 'Sensor Name' in self.attributes:
                instrument = self.attributes['Sensor Name'].strip()
            if ('Sensor' in self.attributes) and not (instrument in known_sensors):
                instrument = self.attributes['Sensor'].strip()
        return instrument

    def _get_l0_constructor_data(self):
        """
        Try to get data from the MODIS L0 constructor for this file.
        """
        l0cnst_results = None
        constr_file = os.path.join('/tmp', os.path.basename(self.file_path) + '.constr')
        constr_out_base = os.path.basename(self.file_path) + '_l0cnst_out'
        constr_err_base = os.path.basename(self.file_path) + '_l0cnst_err'
        constr_out = os.path.join('/tmp', constr_out_base)
        constr_err = os.path.join('/tmp', constr_err_base)
        out_hndl = open(constr_out, 'wt')
        err_hndl = open(constr_err, 'wt')
        cmd = ' '.join(['l0cnst_write_modis', '-f', constr_file,
                        self.file_path])
        try:
            status = subprocess.call(cmd, shell=True, stdout=out_hndl,
                                     stderr=err_hndl)
            if not status:
                with open(constr_out, 'rt') as l0_file:
                    l0cnst_results_str = l0_file.read()
                l0cnst_results = l0cnst_results_str.split('\n')
        except:
            l0cnst_results = None
        finally:
            out_hndl.close()
            err_hndl.close()
            if os.path.exists(constr_file) and os.access(constr_file, os.W_OK):
                os.remove(constr_file)
            if os.path.exists(constr_out) and os.access(constr_out, os.W_OK):
                os.remove(constr_out)
            if os.path.exists(constr_err) and os.access(constr_err, os.W_OK):
                os.remove(constr_err)

        return l0cnst_results

    def get_file_times(self):
        """
        Returns the start and end time for a file.
        """
        start_time = ''
        end_time = ''
        if self.instrument == 'VIIRS' and self.file_type == 'SDR':
            start_time = self._create_viirs_l1_timestamp(self.attributes['Beginning_Date'],
                                                         self.attributes['Beginning_Time'])
            end_time = self._create_viirs_l1_timestamp(self.attributes['Ending_Date'],
                                                       self.attributes['Ending_Time'])
        if self.file_type.find('Level 1') != -1:
            start_time = "L1 time"
            end_time = "L1 time"
            if self.instrument.find('SeaWiFS')!= -1 or \
               self.instrument.find('Aquarius') != -1 or \
               self.instrument.find('CZCS') != -1 or \
               self.instrument.find('MOS') != -1 or \
               self.instrument.find('OSMI') != -1:
                start_time = self.attributes['Start Time'][0:13]
                end_time = self.attributes['End Time'][0:13]
            elif self.instrument.find('MODIS') != -1:
                start_time = self._create_modis_l1_timestamp(self.attributes['RANGEBEGINNINGDATE'],
                                                             self.attributes['RANGEBEGINNINGTIME'])
                end_time = self._create_modis_l1_timestamp(self.attributes['RANGEENDINGDATE'],
                                                           self.attributes['RANGEENDINGTIME'])
            elif self.instrument.find('OCTS') != -1:
                start_time = self._create_octs_l1_timestamp(self.attributes['Start Time'])
                end_time = self._create_octs_l1_timestamp(self.attributes['End Time'])
            elif self.instrument.find('MERIS') != -1:
                if 'FIRST_LINE_TIME' in self.attributes:
                    start_time = self._create_meris_l1b_timestamp(self.attributes['FIRST_LINE_TIME'])
                    end_time = self._create_meris_l1b_timestamp(self.attributes['LAST_LINE_TIME'])
                else:
                    start_time = self._create_meris_l1b_timestamp(self.attributes['start_date'].strip('"'))
                    end_time = self._create_meris_l1b_timestamp(self.attributes['stop_date'].strip('"'))
        if self.file_type.find('Level 2') != -1 or \
           self.file_type.find('Level 3') != -1:
            start_time = self.attributes['Start Time'][0:13]
            end_time = self.attributes['End Time'][0:13]
        if self.file_type.find('Level 0') != -1:
            for line in self.l0_data:
                if line.find('starttime') != -1:
                    time_part = line.split('=')[1]
                    start_time = time_part[0:4] + time_part[5:7] + \
                                 time_part[8:10] + time_part[11:13] + \
                                 time_part[14:16] + time_part[17:19]
                if line.find('stoptime') != -1:
                    time_part = line.split('=')[1]
                    end_time = time_part[0:4] + time_part[5:7] +\
                               time_part[8:10] + time_part[11:13] +\
                               time_part[14:16] + time_part[17:19]
        return start_time, end_time

    def get_file_type(self):
        """
        Returns what type (L1A, L2, etc.) a file is and what
        platform/sensor/instrument made the observations.
        """
        orig_path = None
        try:
            if os.path.islink(self.file_path):
                orig_path = self.file_path
                self.file_path = os.path.realpath(self.file_path)
            attrs = modules.MetaUtils.readMetadata(self.file_path)
            if not attrs is None:
                self.attributes = attrs
                if 'Title' in self.attributes or 'title' in self.attributes:
                    if 'Title' in self.attributes:
                        title = self.attributes['Title']
                    else:
                        title = self.attributes['title']
                    if (title.find('Level-1') != -1) or \
                       (title.find('Level 1') != -1) or \
                       (title.find('L1') != -1):
                        self.file_type, self.instrument = self._get_data_from_l1_attributes(title)
                    elif title.find('Level-2') != -1:
                        self.file_type, self.instrument = self._get_data_from_l2_attributes()
                    elif title.find('Level-3') != -1:
                        self.file_type, self.instrument = self._get_data_from_l3_attributes()
                    elif title.find('Level-0') != -1:
                        self.file_type, self.instrument = self._get_data_from_l0_attributes()
                    elif title.find('Ancillary') != -1:
                        self.file_type, self.instrument = self._get_data_from_ancillary_attributes()
                elif 'ASSOCIATEDINSTRUMENTSHORTNAME' in self.attributes:
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
                l0cnst_results = self._get_l0_constructor_data()
                if l0cnst_results is not None:
                    self.l0_data = l0cnst_results
                    is_modis_l0 = False
                    for line in self.l0_data:
                        if line.find('granule length') != -1:
                            parts = line.split('=')
                            try:
                                granule_length = float(parts[1])
                                if granule_length > 0:
                                    is_modis_l0 = True
                            except:
                                pass
                            break
                    if is_modis_l0:
                        self.file_type = 'Level 0'
                        self.instrument = 'MODIS'
                        if re.search('^[aA]|^MOD00.P|^MYD\S+.A|^P1540064',
                                     os.path.basename(self.file_path)):
                            self.instrument = ' '.join([self.instrument,
                                                        'Aqua'])
                        elif re.search('^[tT]|^MOD\S+.A|^P0420064',
                                       os.path.basename(self.file_path)):
                            self.instrument = ' '.join([self.instrument, 
                                                        'Terra'])
        except SystemExit:
            # readMetadata calls sys.exit() when it can't find attributes
            # to process, but we don't want to exit here.
            pass
        except TypeError:
            pass

        if self.instrument.find('MODISA') != -1:
            self.instrument = 'MODIS Aqua'
        if self.instrument.find('MODIST') != -1:
            self.instrument = 'MODIS Terra'
        if orig_path:
            self.file_path = orig_path
        return self.file_type, self.instrument


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
                    output = '{0}: {1}: unknown'.format(os.path.basename(arg), instrument)
                else:
                    output = '{0}: unknown: unknown'.format(os.path.basename(arg))
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

known_sensors = ['Aquarius', 'CZCS', 'HMODISA', 'HMODIST', 'MERIS', 'MODISA',
                 'MODIS Aqua', 'MODIST', 'MODIS Terra', 'MOS', 'OCTS', 'OSMI',
                 'SeaWiFS']

if __name__ == '__main__':
    sys.exit(main())
