#!/usr/bin/env python


"""
A class for determining the OBPG type of a file.
"""
__version__ = '1.3-2018-12-21'

__author__ = 'melliott'

import calendar
import datetime
import modules.MetaUtils
import optparse
import os
import re
import subprocess
import sys
import tarfile
import time
import modules.time_utils

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

def get_usage_text():
    usage_text = \
        """usage: %prog [options] FILE_NAME [FILE_NAME ...]

  The following file types are recognized:
    Instruments: CZCS, GOCI, HICO, Landsat OLI, MODIS Aqua,
                 MODIS Terra, OCM2, OCTS, SeaWiFS, VIIRSN, VIIRSJ1
    Processing Levels: L0 (MODIS only), L1A, L1B, L2, L3 binned,
                       L3 mapped """
    return usage_text

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
            if tarfile.is_tarfile(fpath):
                # self.file_path = self._extract_viirs_sdr(fpath)
                self._extract_viirs_sdr(fpath)
                if not self.file_path:
                    err_msg = "Error! Cannot process file {0}.".format(fpath)
                    sys.exit(err_msg)
            else:
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

    def _create_timestamp_using_mon_abbr(self, time_str):
        """
        Returns a properly formatted date/time stamp for MERIS L1B files from
        an attribute in the file.
        """
        # Todo: Check that MERIS' and Python's month abbreviations match up ...
        year = int(time_str[7:11])
        mon = int(MONTH_ABBRS[time_str[3:6]])
        dom = int(time_str[0:2])
        hrs = int(time_str[12:14])
        mins = int(time_str[15:17])
        secs = int(time_str[18:20])
        dt_obj = datetime.datetime(year, mon, dom, hrs, mins, secs)
        return dt_obj.strftime('%Y%j%H%M%S')

    def _extract_viirs_sdr(self, tar_path):
        self.file_path = None
        try:
            # orig_path = os.getcwd()
            tar_file = tarfile.TarFile(tar_path)
            tar_members = tar_file.getnames()
            for mbr in tar_members:
                if mbr.startswith('SVM01'):
                    mbr_info = tar_file.getmember(mbr)
                    tar_file.extractall(members=[mbr_info], path='/tmp')
                    self.file_path = os.path.join('/tmp', mbr)
                    break
            tar_file.close()
        except:
            exc_info = sys.exc_info()
            for item in exc_info:
                print(str(item))

    def get_attributes(self):
        return self.attributes

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
            else:
                # found = False
                for ks in KNOWN_SENSORS:
                    if part.find(ks) != -1:
                        instrument = ks
                        # found = True
                        break
            if part in possible_levels:
                file_type = possible_levels[part]
        if title.find('Browse Data') != -1:
            file_type += ' Browse Data'
        return file_type, instrument

    def _get_data_from_l2_attributes(self):
        """
        Get the instrument and file type from the attributes for an 20 file.
        """
        file_type = 'Level 2'
        if 'Title' in self.attributes:
            title_parts = self.attributes['Title'].split()
            if self.attributes['Title'].find('Browse Data') != -1:
                file_type += ' Browse Data'
        elif 'title' in self.attributes:
            title_parts = self.attributes['title'].split()
            if self.attributes['title'].find('Browse Data') != -1:
                file_type += ' Browse Data'
        instrument = title_parts[0].strip()
        return file_type, instrument

    def _get_data_from_l3_attributes(self):
        """
        Get the instrument and file type from the attributes for an L3 file.
        """
        file_type = 'unknown'
        if 'Title' in self.attributes:
            working_title = self.attributes['Title']
        elif 'title' in self.attributes:
            working_title = self.attributes['title']
        elif 'instrument' in self.attributes:
            pass
        if (working_title.find('Level-3 Binned') != -1) or \
           (working_title.find('level-3_binned') != -1):
            file_type = 'Level 3 Binned'
        elif working_title.find('Level-3 Standard Mapped Image') != -1:
            file_type = 'Level 3 SMI'
        instrument = self._get_instrument()
        return file_type, instrument

    def _get_instrument(self):
        """
        Get the instrument from the attributes.
        """
        instrument = 'unknown'
        if 'Title' in self.attributes or 'title' in self.attributes:
            if 'Title' in self.attributes:
                title_parts = self.attributes['Title'].split()
            else:
                title_parts = self.attributes['title'].split()
            if title_parts[0].find('Level') == -1:
                instrument = title_parts[0].strip()
        elif 'instrument' in self.attributes:
            instrument = self.attributes['instrument']
        if not (instrument in KNOWN_SENSORS):
            if instrument != 'unknown':
                if 'platform' in self.attributes:
                    instrument = ' '.join([instrument,
                                           self.attributes['platform']])
            else:
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
            out_lines = l0_out.decode('utf-8').split('\n')
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
        except Exception:
            l0cnst_results = None
        return l0cnst_results

    def _get_l0_times(self):
        """
        Returns the start and end times for L0 data files.
        """
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

    def _get_landsat_end_time(self, start_yr, start_doy, start_hr, start_min,
                              start_sec):
        """
        Compute and return the end time for a Landsat OLI data file, given the
        start year, day of year, hour, mine, and second.
        """
        end_yr = start_yr
        end_doy = start_doy
        end_hr = int(start_hr)
        end_min = int(start_min)
        end_sec = int(start_sec) + 1
        if end_sec >= 60:
            end_sec = 0
            end_min += 1
            if end_min >= 60:
                end_min = 0
                end_hr += 1
                if end_hr >= 24:
                    end_hr = 0
                    end_doy += 1
                    if end_yr % 4 == 0:
                        if end_doy > 366:
                            end_doy = 1
                            end_yr += 1
                    elif end_doy > 365:
                        end_doy = 1
                        end_yr += 1
        end_time = '{0:4d}{1:03d}{2:02d}{3:02d}{4:02d}'.format(end_yr,
                                                                   end_doy,
                                                                   end_hr,
                                                                   end_min,
                                                                   end_sec)
        return end_time

    def _get_landsat_times(self):
        """
        Computes and returns the start and end times for a Landsat OLI
        data file.
        """
        # The Landsat OLI metadata only contains an acquisition date and
        # scene center time.  (For now) It is assumed that the scene center
        # time is the start time and the end time is one second later.
        acquisition_date = self.attributes['DATE_ACQUIRED'].strip('"')
        center_time = self.attributes['SCENE_CENTER_TIME'].strip('"')

        start_yr = int(acquisition_date[0:4])
        start_mon = int(acquisition_date[5:7])
        start_dom = int(acquisition_date[8:10])
        start_doy =modules.time_utils.convert_month_day_to_doy(start_mon, start_dom,
                                                        start_yr)
        start_date_str = '{0:04d}{1:03d}'.format(start_yr, start_doy)
        start_hr = center_time[0:2]
        start_min = center_time[3:5]
        start_sec = center_time[6:8]
        start_time =  ''.join([start_date_str, start_hr, start_min,
                               start_sec])
        end_time = self._get_landsat_end_time(start_yr, start_doy,
                                              start_hr, start_min, start_sec)
        return start_time, end_time

    def _get_time_from_coverage_field(self, coverage_time):
        """
        Returns the stamp computed from the coverage_time
        """
        if coverage_time[0:4] == '':
            yr = '0000'
        else:
            yr = '{0:04d}'.format(int(coverage_time[0:4]))
        doy = '{0:03d}'.format(
                        modules.time_utils.convert_month_day_to_doy(coverage_time[5:7],
                                                            coverage_time[8:10],
                                                            coverage_time[0:4]))
        if coverage_time[11:13] == '':
            hr = '00'
        else:
            hr = '{0:02d}'.format(int(coverage_time[11:13]))
        if coverage_time[14:16] == '':
            min = '00'
        else:
            min = '{0:02d}'.format(int(coverage_time[14:16]))
        if coverage_time[17:19] == '':
            sec = '00'
        else:
            sec = '{0:02d}'.format(int(coverage_time[17:19]))
        time_stamp = ''.join([yr, str(doy), hr, min, sec])
        return time_stamp


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
        if 'VIIRS' in self.instrument and self.file_type == 'SDR':
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
                if 'time_coverage_start' in self.attributes:
                    start_time = self._get_time_from_coverage_field(self.attributes['time_coverage_start'])
                    end_time = self._get_time_from_coverage_field(self.attributes['time_coverage_end'])
                elif 'RANGEBEGINNINGDATE' in self.attributes:
                    start_time, end_time = self._get_l1_modis_times()
                elif 'Start Time' in self.attributes:
                    start_time = self.attributes['Start Time'][0:13]
                elif 'time_coverage_start' in self.attributes:
                    start_time = self._get_time_from_coverage_field(
                                      self.attributes['time_coverage_start'])
                elif 'Start Day' in self.attributes:
                    start_time = get_timestamp_from_year_day_mil(
                        int(self.attributes['Start Year']),
                        int(self.attributes['Start Day']),
                        int(self.attributes['Start Millisec'])
                    )
                if 'End Time' in self.attributes:
                    end_time = self.attributes['End Time'][0:13]
                elif 'time_coverage_end' in self.attributes:
                    end_time = self._get_time_from_coverage_field(
                                     self.attributes['time_coverage_end'])
                elif 'End Day' in self.attributes:
                    end_time = get_timestamp_from_year_day_mil(
                        int(self.attributes['End Year']),
                        int(self.attributes['End Day']),
                        int(self.attributes['End Millisec'])
                    )
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
            start_time, end_time = self._get_l0_times()
        return start_time, end_time

    def _get_type_using_platform(self):
        levelMap = {'L0':'Level 0',
                    'L1A':'Level 1A',
                    'GEO':'GEO',
                    'L1B':'Level 1B',
                    'L2':'Level 2',
                    'L3 Binned':'Level 3 Binned',
                    'L3 Mapped':'Level 3 SMI'
                    }
        instrumentMap = {'SEAWIFS': "SeaWiFS",
                         "MOS": "MOS",
                         "OCTS": "OCTS",
                         "AVHRR":"AVHRR",
                         "OSMI": "OSMI",
                         "CZCS": "CZCS",
                         "OCM1": "OCM1",
                         "OCM2": "OCM2",
                         "MERIS":"MERIS",
                         "OCRVC":"OCRVC",
                         "HICO": "HICO",
                         "GOCI": "GOCI",
                         "OLI": "OLI",
                         "AQUARIUS": "Aquarius" ,
                         "OCIA": "OCIA",
                         "AVIRIS": "AVIRIS",
                         "PRISM": "PRISM",
                         "SGLI": "SGLI",
                         "L5TM": "L5TM",
                         "L7ETM": "L7ETM",
                         "HAWKEYE": "HAWKEYE",
                         "MISR": "MISR",
                         "OCI": "OCI"
                         }
        
        if self.attributes['processing_level'] in levelMap:
            self.file_type = levelMap[self.attributes['processing_level']]
            if self.file_type == 'Level 3 SMI':
                if self.attributes['title'].find('Standard Mapped Image') == -1:
                    self.file_type == 'Level 3 Mapped'
            inst = self.attributes['instrument'].upper()
            if inst in instrumentMap:
                self.instrument = instrumentMap[inst]
                return True
            plat = self.attributes['platform'].upper()
            if inst.find('MODIS') != -1:
                if plat.find('AQUA') != -1:
                    self.instrument = "MODIS Aqua"
                    return True
                elif plat.find('TERRA') != -1:
                    self.instrument = "MODIS Terra"
                    return True
            elif inst.find('VIIRS') != -1:
                if plat.find('SUOMI-NPP') != -1:
                    self.instrument = "VIIRS NPP"
                    return True
                elif plat.find('JPSS-1') != -1:
                    self.instrument = "VIIRS J1"
                    return True
            elif inst.find('OLCI') != -1:
                if plat == 'SENTINEL-3' or plat.find('3A') != -1:
                    self.instrument = "OLCI S3A"
                    return True
                elif plat.find('3B') != -1:
                    self.instrument = "OLCI S3B"
                    return True
            elif inst.find('MSI') != -1:
                if plat == 'SENTINEL-2' or plat.find('2A') != -1:
                    self.instrument = "MSI S2A"
                    return True
                elif plat.find('2B') != -1:
                    self.instrument = "MSI S2B"
                    return True
        return False

    def _get_file_type_from_attributes(self):
        """
        Determines the file type and instrument from the file attributes and
        sets those values in the object.
        """

        if ('platform' in self.attributes) and ('instrument' in self.attributes) and ('processing_level' in self.attributes):
            if self._get_type_using_platform():
                return
            
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
                if 'Mission_Name' in self.attributes:
                    mission = self.attributes['Mission_Name']
                    if mission == 'NPP':
                        self.instrument = 'VIIRS NPP'
                    elif mission == 'JPSS-1':
                        self.instrument = 'VIIRS J1'
                if 'N_Dataset_Type_Tag' in self.attributes:
                    self.file_type = self.attributes['N_Dataset_Type_Tag']
        elif 'Product Level' in self.attributes:
            if 'Sensor name' in self.attributes:
                self.instrument = self.attributes['Sensor name']
                self.file_type = self.attributes['Product Level']
                if not self.file_type.startswith('Level'):
                    self.file_type = 'Level ' + self.file_type
        elif 'SENSOR_ID' in self.attributes:
            self._get_file_type_landsat()

    def get_file_type(self):
        """
        Returns what type (L1A, L2, etc.) a file is and what
        platform/sensor/instrument made the observations.
        """
        orig_path = None
        self._read_metadata()
        if self.attributes:
            self._get_file_type_from_attributes()
        else:
            self._get_type_using_l0_cnst()
        if self.instrument.find('MODISA') != -1:
            self.instrument = 'MODIS Aqua'
        if self.instrument.find('MODIST') != -1:
            self.instrument = 'MODIS Terra'
        if orig_path:
            self.file_path = orig_path
        return self.file_type, self.instrument

    def _get_file_type_landsat(self):
        """
        Sets the file type and instrument for Landsat OLI data files
        """
        # Landsat 8 OLI
        if self.attributes['SENSOR_ID'].find('OLI_TIRS') != -1:
            self.instrument = 'OLI'
        else:
            self.instrument = self.attributes['SENSOR_ID'].\
                                   strip().strip('"')
        if self.attributes['DATA_TYPE'].find('L1G') != -1 or \
           self.attributes['DATA_TYPE'].find('L1GT') != -1 or \
           self.attributes['DATA_TYPE'].find('L1P') != -1 or \
           self.attributes['DATA_TYPE'].find('L1T') != -1:
            self.file_type = 'Level 1B'
        else:
            self.file_type = 'Level ' + self.attributes['DATA_TYPE'].\
                                              strip().strip('"')


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

    def _get_l1_goci_times(self):
        """
        Finds and returns timestamps for GOCI L1 data files.
        """
        if 'Scene Start time' in self.attributes and self.attributes['Scene Start time'] != 'unknown':
            # start_time = self.attributes['Scene Start time']
            start_time = self._create_timestamp_using_mon_abbr(self.attributes['Scene Start time'])
        elif 'start_time' in self.attributes and self.attributes['start_time'] != 'unknown':
            start_time = self.attributes['start_time']
        elif 'processing start time' in self.attributes:
            st_yr = int(self.attributes['processing start time'][7:11])
            mon = time.strptime(self.attributes['processing start time']\
                                               [3:6], '%b').tm_mon
            dom = int(self.attributes['processing start time'][0:2])
            doy =modules.time_utils.convert_month_day_to_doy(mon, dom, st_yr)
            start_time = '{0:04d}{1:03d}{2:02d}{3}{4}'.format(st_yr, doy,
                int(self.attributes['processing start time'][12:14]),
                self.attributes['processing start time'][15:17],
                self.attributes['processing start time'][18:20])
        if 'Scene end time' in self.attributes and self.attributes['Scene end time'] != 'unknown':
            end_time = self._create_timestamp_using_mon_abbr(self.attributes['Scene end time'])
        elif 'end_time' in self.attributes and self.attributes['end_time'] != 'unknown':
            end_time = self.attributes['end_time']
        elif 'processing end time' in self.attributes:
            end_yr = int(self.attributes['processing end time'][7:11])
            mon = time.strptime(self.attributes['processing end time']\
                                               [3:6], '%b').tm_mon
            dom = int(self.attributes['processing end time'][0:2])
            doy =modules.time_utils.convert_month_day_to_doy(mon, dom, end_yr)
            end_time = '{0:04d}{1:03d}{2:02d}{3}{4}'.format(end_yr, doy,
                int(self.attributes['processing end time'][12:14]),
                self.attributes['processing end time'][15:17],
                self.attributes['processing end time'][18:20])
        return start_time, end_time

    def _get_l1_hico_times(self):
        """
        Finds and returns timestamps for HICO L1 data files.
        """
        start_time = get_timestamp_from_month_day(\
                        self.attributes['Beginning_Date'],
                        self.attributes['Beginning_Time'])
        end_time = get_timestamp_from_month_day(
                        self.attributes['Ending_Date'],
                        self.attributes['Ending_Time'])
        return start_time, end_time

    def _get_l1_meris_times(self):
        """
        Finds and returns timestamps for MERIS L1 data files.
        """
        if 'FIRST_LINE_TIME' in self.attributes:
            start_time = self._create_timestamp_using_mon_abbr(
                self.attributes['FIRST_LINE_TIME'])
            end_time = self._create_timestamp_using_mon_abbr(
                self.attributes['LAST_LINE_TIME'])
        else:
            start_time = self._create_timestamp_using_mon_abbr(
                self.attributes['start_date'].strip('"'))
            end_time = self._create_timestamp_using_mon_abbr(
                self.attributes['stop_date'].strip('"'))
        return start_time, end_time

    def _get_l1_modis_times(self):
        """
        Finds and returns timestamps for MODIS L1 data files.
        """
        start_time = self._create_modis_l1_timestamp(
            self.attributes['RANGEBEGINNINGDATE'],
            self.attributes['RANGEBEGINNINGTIME'])
        end_time = self._create_modis_l1_timestamp(
            self.attributes['RANGEENDINGDATE'],
            self.attributes['RANGEENDINGTIME'])
        return start_time, end_time

    def _get_l1_ocm2_times(self):
        """
        Finds and returns timestamps for OCM2 L1 data files.
        """
        #yr, doy, millisecs
        if 'Start Year' in self.attributes:
            start_time = get_timestamp_from_year_day_mil(\
                self.attributes['Start Year'],
                self.attributes['Start Day'],
                self.attributes['Start Millisec'])
        elif 'time_coverage_start' in self.attributes:
            start_time = self._get_time_from_coverage_field(
                  self.attributes['time_coverage_start'])
        if 'End Year' in self.attributes:
            end_time = get_timestamp_from_year_day_mil(\
                self.attributes['End Year'],
                self.attributes['End Day'],
                self.attributes['End Millisec'])
        elif 'time_coverage_end' in self.attributes:
            end_time = self._get_time_from_coverage_field(
                  self.attributes['time_coverage_end'])
        return start_time, end_time

    def _get_l1_octs_times(self):
        """
        Finds and returns timestamps for OCTS L1 data files.
        """
        if 'Start Time' in self.attributes:
            start_time = self._create_octs_l1_timestamp(
                self.attributes['Start Time'])
            end_time = self._create_octs_l1_timestamp(
                self.attributes['End Time'])
        else:
            start_time = get_timestamp_from_month_day(''.join([
                            self.attributes['time_coverage_start'][0:4],
                            self.attributes['time_coverage_start'][5:7],
                            self.attributes['time_coverage_start'][8:10]
                            ]), ''.join([
                            self.attributes['time_coverage_start'][11:13],
                            self.attributes['time_coverage_start'][14:16],
                            self.attributes['time_coverage_start'][17:19]
            ]))
            end_time = get_timestamp_from_month_day(''.join([
                            self.attributes['time_coverage_end'][0:4],
                            self.attributes['time_coverage_end'][5:7],
                            self.attributes['time_coverage_end'][8:10]
                            ]), ''.join([
                            self.attributes['time_coverage_end'][11:13],
                            self.attributes['time_coverage_end'][14:16],
                            self.attributes['time_coverage_end'][17:19]
            ]))
        return start_time, end_time

    def _get_l1_times(self):
        """
        Determines the times for Level 1 files.
        """
        start_time = None
        end_time = None
        if self.instrument.find('SeaWiFS')!= -1 or \
           self.instrument.find('Aquarius') != -1 or \
           self.instrument.find('CZCS') != -1 or \
           self.instrument.find('MOS') != -1 or \
           self.instrument.find('OSMI') != -1 or \
           self.instrument.find('VIIRS') != -1:
            if 'Start Time' in self.attributes:
                start_time = self.attributes['Start Time'][0:13]
            elif 'time_coverage_start' in self.attributes:
                start_time = get_timestamp_from_month_day(''.join([
                                self.attributes['time_coverage_start'][0:4],
                                self.attributes['time_coverage_start'][5:7],
                                self.attributes['time_coverage_start'][8:10]
                                ]), ''.join([
                                self.attributes['time_coverage_start'][11:13],
                                self.attributes['time_coverage_start'][14:16],
                                self.attributes['time_coverage_start'][17:19]
                ]))
            if 'End Time' in self.attributes:
                end_time = self.attributes['End Time'][0:13]
            elif 'time_coverage_end' in self.attributes:
                end_time = get_timestamp_from_month_day(''.join([
                                self.attributes['time_coverage_end'][0:4],
                                self.attributes['time_coverage_end'][5:7],
                                self.attributes['time_coverage_end'][8:10]
                                ]), ''.join([
                                self.attributes['time_coverage_end'][11:13],
                                self.attributes['time_coverage_end'][14:16],
                                self.attributes['time_coverage_end'][17:19]
                ]))
        elif self.instrument.find('MODIS') != -1:
            start_time, end_time = self._get_l1_modis_times()
        elif self.instrument.find('OCTS') != -1:
            start_time, end_time = self._get_l1_octs_times()
        elif self.instrument.find('MERIS') != -1:
            start_time, end_time = self._get_l1_meris_times()
        elif self.instrument.find('OCM2') != -1:
            start_time, end_time = self._get_l1_ocm2_times()
        elif self.instrument.find('HICO') != -1:
            start_time, end_time = self._get_l1_hico_times()
        elif self.instrument.find('GOCI') != -1:
            start_time, end_time = self._get_l1_goci_times()
        elif self.instrument.find('OLI') != -1:
            start_time, end_time = self._get_landsat_times()
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
        elif (title.find('Level-3') != -1) or (title.find('level-3') != -1):
            self.file_type, self.instrument = \
            self._get_data_from_l3_attributes()
        elif title.find('Level-0') != -1:
            self.file_type, self.instrument = \
            self._get_data_from_l0_attributes()
        elif title.find('Ancillary') != -1:
            self.file_type, self.instrument = \
            self._get_data_from_anc_attributes()
        elif title.find('VIIRS') != -1:
            self.instrument = 'VIIRS'
            if 'processing_level' in self.attributes:
                if self.attributes['processing_level'].upper().find('L1A') != -1:
                    self.file_type = 'Level 1A'
                elif self.attributes['processing_level'].upper().find('L1B') != -1:
                    self.file_type = 'Level 1B'
                elif self.attributes['processing_level'].upper().find('GEO') != -1:
                    self.file_type = 'GEO'
            elif title.find('L1A') != -1:
                self.file_type = 'Level 1A'
            elif title.find('L1B') != -1:
                self.file_type = 'Level 1B'

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
    use_msg = get_usage_text()
    ver_msg = ' '.join(['%prog', __version__])
    cl_parser = optparse.OptionParser(usage=use_msg, version=ver_msg)
    (opts, args) = process_command_line(cl_parser)

    if len(args) > 0:
        for arg in args:
            fname = arg
            file_typer = ObpgFileTyper(fname)
            (obpg_file_type, instrument) = file_typer.get_file_type()
            output = ''
            if obpg_file_type == 'unknown':
                if instrument != 'unknown':
                    output = '{0}: {1}: unknown'.format(
                                            os.path.basename(fname), instrument)
                else:
                    output = '{0}: unknown: unknown'.format(
                                os.path.basename(fname))
            else:
                if instrument != 'unknown':
                    output = '{0}: {1}: {2}'.format(os.path.basename(fname),
                                                    instrument, obpg_file_type)
                else:
                    output = '{0}: unknown: {1}'.format(
                                        os.path.basename(fname), obpg_file_type)
            if opts.times:
                if obpg_file_type != 'unknown' and instrument != 'unknown':
                    start_time, end_time = file_typer.get_file_times()
                    output += ': {0} : {1}'.format(start_time, end_time)
                else:
                    output += ': unable to determine file start and end times'
            print(output)
    else:
        print('\nError!  No file specified for type identification.\n')
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
                 'OSMI','SeaWiFS', 'VIIRSN', 'VIIRSJ1']

MONTH_ABBRS = dict((v.upper(), k) for k, v in enumerate(calendar.month_abbr))

if __name__ == '__main__':
    sys.exit(main())
