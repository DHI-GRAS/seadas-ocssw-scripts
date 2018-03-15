from __future__ import print_function
import os

"""
Utility functions for determining directories for each sensor.
"""

SensorList = []


def load_sensorlist(filename=None):
    """
    Read list of sensor definitions from file
    """
    global SensorList
    SensorList = []
    keys = ['sensor', 'instrument', 'platform', 'dir', 'subdir']
    try:
        if not filename:
            filename = os.path.join(os.getenv('OCDATAROOT'),
                                    'common', 'SensorInfo.txt')
        with open(filename) as infile:
            for line in infile:
                line = line.strip()
                if (len(line) > 0) and (not line.startswith("#")):
                    values = line.rsplit()
                    SensorList.append(dict(zip(keys, values)))
    except Exception as e:
        print(e)


def by_sensor(name):
    """
    Get sensor defs from unique sensor name
    """
    global SensorList
    if len(SensorList) == 0:
        load_sensorlist()
    try:
        return next(d for d in SensorList if d['sensor'].lower() == name.lower())
    except StopIteration:
        return None


def by_instplat(inst, plat):
    """
    Get sensor defs given the instrument and platform
    """
    global SensorList
    if len(SensorList) == 0:
        load_sensorlist()
    try:
        return next(d for d in SensorList if
                    (d['instrument'].lower() == inst.lower()) &
                    (d['platform'].lower() == plat.lower()))
    except StopIteration:
        return None


def by_desc(name):
    """
    Get sensor defs given any useful information
    """
    global SensorList
    if len(SensorList) == 0:
        load_sensorlist()
    try:
        return next(d for d in SensorList if
                    name.lower() in (d['sensor'].lower(),
                                     d['platform'].lower(),
                                     d.get('subdir'),
                                     d['dir'].lower(),
                                     d['instrument'].lower()))
    except StopIteration:
        return None


# end of class SensorUtils

# test routines below
if __name__ == '__main__':
    if len(SensorList) == 0:

        print("\nby sensor:")
        namelist = ['modisa', 'seawifs', 'bogus']
        for sensor in namelist:
            print(sensor, ':\t', by_sensor(sensor))

        print("\nby inst/plat:")
        instlist = ['modis', 'VIIRS', 'modis', 'bogus', 'Aquarius']
        platlist = ['Terra', 'JPSS-1', 'bogus', 'Aqua', 'SAC-D']
        for inst, plat in zip(instlist, platlist):
            print(inst, plat, ':\t', by_instplat(inst, plat))

        print("\nby any name:")
        namelist = ['seawifs', 'aquarius', 'modisa', 'modist', 'viirsn', 'viirsj1', 'aqua', 'terra', 'npp', 'j1',
                    'bogus']
        for name in namelist:
            print(name, ':\t', by_desc(name))
