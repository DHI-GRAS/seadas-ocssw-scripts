from MetaUtils import readMetadata
import ProcUtils

def viirs_timestamp(arg):
    """
        Determine the start time, stop time, and platform of a VIIRS hdf5 file.
    """

    meta = readMetadata(arg)
    if 'Instrument_Short_Name' in meta:
        sat_name = meta['Instrument_Short_Name'].lower()
        sdate = meta['Beginning_Date']
        edate = meta['Ending_Date']
        stime = meta['Beginning_Time']
        etime = meta['Ending_Time']
        start_time = '-'.join([sdate[0:4],sdate[4:6],sdate[6:8]]) + 'T' + ':'.join([stime[0:2],stime[2:4],stime[4:len(stime)]])
        end_time = '-'.join([edate[0:4],edate[4:6],edate[6:8]]) + 'T' + ':'.join([etime[0:2],etime[2:4],etime[4:len(etime)]])
    elif 'instrument' in meta:
        sat_name = meta['instrument'].lower()
        start_time = meta['time_coverage_start']
        end_time = meta['time_coverage_end']
    # at this point datetimes are formatted as YYYY-MM-DD HH:MM:SS.uuuuuu

    # return values formatted as YYYYDDDHHMMSS
    return ( ProcUtils.date_convert(start_time, 't', 'j'),
             ProcUtils.date_convert(end_time, 't', 'j'),
             sat_name )