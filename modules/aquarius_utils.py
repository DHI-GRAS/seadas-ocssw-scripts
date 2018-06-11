from __future__ import print_function

from MetaUtils import readMetadata


def aquarius_timestamp(arg):
    """
        Determine the start time, stop time, and platform of an aquarius L1A file.
    """

    meta = readMetadata(arg)

    sat_name = meta['Sensor'].lower()
    stime = meta['Start Time'][0:13]
    etime = meta['End Time'][0:13]

    return (stime,
            etime,
            sat_name)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        filename = sys.argv[1]
    else:
        filename = "/Users/Shared/testing/Q2012300002900.L1A_SCI"
    start, stop, sensor = aquarius_timestamp(filename)
    print(start, stop, sensor)
