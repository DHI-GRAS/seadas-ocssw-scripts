#! /usr/bin/env python

# Extractor for OLCI Sentinel 3A L1B files

import argparse
from datetime import datetime, timedelta
import os
import sys
import time
from shutil import copy as cp

from modules.netcdf_utils import ncsubset_vars
from modules.pixlin_utils import pixlin
from modules.setupenv import env
import netCDF4

radfiles = ["Oa{:02d}_radiance.nc".format(i) for i in range(1, 22)]
engfiles = ["geo_coordinates.nc",
            "instrument_data.nc",
            "qualityFlags.nc",
            "removed_pixels.nc",
            "time_coordinates.nc"]
tiefiles = ["tie_geo_coordinates.nc",
            "tie_geometries.nc",
            "tie_meteo.nc"]


def minmax(arr):
    return arr.min(), arr.max()


def epoch2000(usec):
    # format Epoch 2000 time (microseconds since 2000-01-01)
    base = datetime(2000, 1, 1, 0, 0, 0)
    t = base + timedelta(microseconds=int(usec))
    return t.strftime('%Y-%m-%dT%H:%M:%S.%fZ')


class extract:

    def __init__(self, idir, odir=None,
                 north=None, south=None, west=None, east=None,
                 verbose=False):
        # inputs
        self.idir = idir
        self.odir = odir
        self.north = north
        self.south = south
        self.west = west
        self.east = east
        self.verbose = verbose
        self.geofile = os.path.join(idir, 'geo_coordinates.nc')
        self.timefile = os.path.join(idir, 'time_coordinates.nc')
        self.tiefile = os.path.join(idir, 'tie_geo_coordinates.nc')

        # defaults
        self.runtime = None
        self.attrs = None

        # unused, but needed by setupenv.py
        self.dirs = {}
        self.ancdir = None
        self.curdir = False
        self.sensor = None
        env(self)  # run setupenv

    def runextract(self, files, subset):
        # subset each file
        for filename in files:
            srcfile = os.path.join(self.idir, filename)
            if os.path.exists(srcfile):
                dstfile = os.path.join(self.odir, filename)
                if self.verbose:
                    print('Extracting', srcfile)
                retcode = ncsubset_vars(srcfile, dstfile, subset,
                                        timestamp=self.runtime)
                if retcode:
                    print("Error extracting file %s" % srcfile)
                    return 1

                # update global attributes
                with netCDF4.Dataset(dstfile, mode='a') as dst:
                    dst.setncatts(self.attrs)
        return 0

    def run(self):

        # run lonlat2pixline
        pl = pixlin(geofile=self.geofile,
                    north=self.north, south=self.south,
                    west=self.west, east=self.east,
                    verbose=self.verbose)
        pl.lonlat2pixline(zero=True)  # using 0-based indices

        if pl.status in (0, 110):

            # check/create output directory
            if not self.odir:
                self.odir = '.'.join([self.idir, 'subset'])
            if not os.path.exists(self.odir):
                os.makedirs(os.path.abspath(self.odir))

            # adjust endpoints to align with tie files
            with netCDF4.Dataset(self.tiefile, 'r') as src:
                dpixl = getattr(src, 'ac_subsampling_factor', 1)  # tie_col_pts
                dline = getattr(src, 'al_subsampling_factor', 1)  # tie_row_pts
            # TODO: make sure tie files have num points needed in each
            # dim for meaningful spline interpolation.

            spixl, epixl = [pl.spixl, pl.epixl + dpixl - 1] // dpixl * dpixl
            sline, eline = [pl.sline, pl.eline + dline - 1] // dline * dline
            if self.verbose:
                print("spixl={} epixl={} sline={} eline={}".
                      format(spixl, epixl, sline, eline))

            # find new start, stop times
            with netCDF4.Dataset(self.timefile, 'r') as src:
                ts = src['time_stamp'][[sline, eline]]
                start_time = epoch2000(ts[0])
                stop_time  = epoch2000(ts[1])

            # find new lat/lon ranges
            with netCDF4.Dataset(self.geofile, 'r') as src:
                lat_min, lat_max = minmax(src['latitude']
                                        [sline:eline, spixl:epixl])
                lon_min, lon_max = minmax(src['longitude']
                                        [sline:eline, spixl:epixl])

            # define global attributes
            self.attrs = {'start_time': start_time,
                          'stop_time':  stop_time,
                          'geospatial_lat_min': lat_min,
                          'geospatial_lat_max': lat_max,
                          'geospatial_lon_min': lon_min,
                          'geospatial_lon_max': lon_max }
            self.runtime = time.gmtime()  # same for all files

            # extract full-resolution files
            subset = {'columns':[spixl, epixl],
                      'rows':   [sline, eline]}
            status = self.runextract(radfiles + engfiles, subset)

            # extract lower-resolution (tie) files
            subset = {'tie_columns':[spixl, epixl] // dpixl,
                      'tie_rows':   [sline, eline] // dline}
            status = self.runextract(tiefiles, subset)

        return status


if __name__ == "__main__":

    # parse command line
    parser = argparse.ArgumentParser(
        description="Extract specified area from OLCI Level 1B files")
    parser.add_argument("idir",
                        help="directory containing OLCI Level 1B files")
    parser.add_argument("-v", "--verbose", help="print status messages",
                        action="store_true")
    parser.add_argument("-o", "--odir",
                        help="output directory (defaults to [idir].subset)")
    parser.add_argument("-n", "--north", type=float, default=90,
                        help="northernmost latitude")
    parser.add_argument("-s", "--south", type=float, default=-90,
                        help="southernmost latitude")
    parser.add_argument("-w", "--west", type=float, default=-180,
                        help="westernmost longitude")
    parser.add_argument("-e", "--east", type=float, default=180,
                        help="easternmost longitude")
    args = parser.parse_args()

    # initialize
    this = extract(idir=args.idir,
                   odir=args.odir,
                   north=args.north,
                   south=args.south,
                   west=args.west,
                   east=args.east,
                   verbose=args.verbose)

    # check
    if not os.path.exists(this.idir):
        print("ERROR: Directory '" + this.idir + "' does not exist. Exiting.")
        sys.exit(1)
    if not os.path.exists(this.timefile):
        print("ERROR: Timestamp file (%s) not found!" % this.timefile)
        sys.exit(1)
    if not os.path.exists(this.tiefile):
        print("ERROR: Tie file (%s) not found!" % this.tiefile)
        sys.exit(1)
    # pixlin() checks for missing self.geofile

    # run
    status = this.run()

    # copy the manifest in case we ever need it
    cp(os.path.join(this.idir, 'xfdumanifest.xml'), this.odir)

    exit(status)
