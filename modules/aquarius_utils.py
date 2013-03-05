from MetaUtils import readMetadata
import ProcUtils

def aquarius_timestamp(arg):
    """
        Determine the start time, stop time, and platform of a VIIRS hdf5 file.
    """

    meta = readMetadata(arg)

    sat_name = meta['Sensor'].lower()
    stime = meta['Orbit Start Time'][0:13]
    etime = meta['Orbit Stop Time'][0:13]

    return ( stime,
             etime,
             sat_name )
             
if __name__ == "__main__":
    file = "/Users/Shared/testing/Q2012300002900.L1A_SCI"
    start, stop, sensor = aquarius_timestamp(file)
    print start, stop, sensor
