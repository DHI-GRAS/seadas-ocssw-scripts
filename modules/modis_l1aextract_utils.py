#! /usr/bin/env python

from modules.ParamUtils import ParamProcessing

class extract:
    def __init__(self, file=file, parfile=None, outfile=None, geofile=None, north=None, south=None, west=None, east=None
    ,
                 log=False, sensor=None, verbose=False):
        # defaults
        self.file = file
        self.parfile = parfile
        self.geofile = geofile
        self.outfile = outfile
        self.log = log
        self.proctype = 'modisGEO'
        self.ancdir = None
        self.curdir = False
        self.pcf_file = None
        self.verbose = verbose
        self.dirs = {}
        self.sensor = sensor
        self.north = north
        self.south = south
        self.west = west
        self.east = east
        # version-specific variables
        self.collection_id = '061'
        self.pgeversion = '6.1.1'
        self.lutversion = None

        if self.parfile:
            print(self.parfile)
            p = ParamProcessing(parfile=self.parfile)
            p.parseParFile(prog='geogen')
            print(p.params)
            phash = p.params['geogen']
            for param in (list(phash.keys())):
                print(phash[param])
                if not self[param]:
                    self[param] = phash[param]

    def __setitem__(self, index, item):
        self.__dict__[index] = item

    def __getitem__(self, index):
        return self.__dict__[index]

    def chk(self):
        """
        Check parameters
        """
        import os
        import sys

        if self.file is None:
            print("ERROR: No MODIS_L1A_file was specified in either the parameter file or in the argument list. Exiting")
            sys.exit(1)
        if not os.path.exists(self.file):
            print("ERROR: File '" + self.file + "' does not exist. Exiting.")
            sys.exit(1)
        if self.sensor.find('modis') < 0 and not os.path.exists(self.geofile):
            print("ERROR: Geolocation file (%s) not found!" % self.geofile)
            sys.exit(1)
        if (0 != self.north and not self.north) or \
           (0 != self.south and not self.south) or \
           (0 != self.west and not self.west) or \
           (0 != self.east and not self.east):
            print("Error: All four NSWE coordinates required!")
            sys.exit(1)
        try:
            north = float(self.north)
        except ValueError:
            err_msg = 'Error! North value "{0}" non-numeric.'.format(self.north)
        try:
            south = float(self.south)
        except ValueError:
            err_msg = 'Error! South value "{0}" non-numeric.'.format(self.south)
        try:
            east = float(self.east)
        except ValueError:
            err_msg = 'Error! East value "{0}" non-numeric.'.format(self.east)
        try:
            west = float(self.west)
        except ValueError:
            err_msg = 'Error! West value "{0}" non-numeric.'.format(self.west)

        if north <= south:
            print("Error: North must be greater than South!")
            sys.exit(1)
        if (north > 90.0) or (south < -90.0):
            print("Latitude range outside realistic bounds!")
            sys.exit(1)
        if west < -180 or west > 180. or east < -180. or east > 180:
            print("Longitudes must be between -180.0 and 180.0")
            sys.exit(1)

    def run(self):
        """
        Run lonlat2pixline and l1aextract
        """
        import subprocess
        import os

        if self.verbose:
            print("")
            print("Locating pixel/line range ...")
        lonlat2pixline = os.path.join(self.dirs['bin'], 'lonlat2pixline')
        pixlincmd = [lonlat2pixline, self.geofile, str(self.west), str(self.south), str(self.east), str(self.north)]
        p = subprocess.Popen(pixlincmd, stdout=subprocess.PIPE)
        line = p.communicate()[0]
        if not p.returncode:
            pixlin = line.splitlines()[0][2:].split()

            l1extract = os.path.join(self.dirs['bin'], 'l1aextract_modis')
            extractcmd = ' '.join([' ', self.file, pixlin[0], pixlin[1], pixlin[2], pixlin[3], self.outfile])
            retcode = subprocess.call(l1extract + extractcmd, shell=True)
            if retcode:
                print("Error extracting file %s" % self.file)
                return 1

        else:
            if p.returncode == 120:
                print("No extract necessary, entire scene contained within the selected region of interest.")
                return 120
            else:
                print("Error locating pixel/line range to extract.")
                return 1

        return 0



      
