#! /usr/bin/env python

from setupenv import env
import os
import subprocess
import sys


class pixlin:

    def __init__(self, geofile=None,
                 north=None, south=None, west=None, east=None,
                 verbose=False):
        # defaults
        self.geofile = geofile
        self.ancdir = None
        self.curdir = False
        self.verbose = verbose
        self.dirs = {}
        self.north = north
        self.south = south
        self.west = west
        self.east = east
        self.spixl = None
        self.epixl = None
        self.sline = None
        self.eline = None
        self.status = None
        env(self)

    def __setitem__(self, index, item):
        self.__dict__[index] = item

    def __getitem__(self, index):
        return self.__dict__[index]

    def chk(self):
        """
        Check parameters
        """
        if not os.path.exists(self.geofile):
            print("ERROR: File '" + self.geofile + "' does not exist. Exiting.")
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

    def lonlat2pixline(self, zero=False):
        """
        Run lonlat2pixline
        """
        self.chk()

        if self.verbose:
            print("")
            print("Locating pixel/line range ...")
        exe = os.path.join(self.dirs['bin'], 'lonlat2pixline')
        pixlincmd = [exe, '-F', self.geofile,
                     str(self.west), str(self.south),
                     str(self.east), str(self.north)]
        p = subprocess.Popen(pixlincmd, stdout=subprocess.PIPE)
        line = p.communicate()[0].decode("utf-8")

        if p.returncode in (0, 110):

            # get pixel/line endpoints
            pixlin = line.splitlines()[-5][2:].split()  # [spixl,epixl,sline,eline]
            pixlin = [int(p) for p in pixlin]  # bytestring -> int
            if zero:
                pixlin = [p - 1 for p in pixlin]  # convert to zero-based index
            self.spixl = pixlin[0]
            self.epixl = pixlin[1]
            self.sline = pixlin[2]
            self.eline = pixlin[3]

        elif p.returncode == 120:
            print("No extract necessary:",
                  "entire scene contained within specified region of interest.")
        else:
            print("Error locating pixel/line range to extract.")

        self.status = p.returncode
