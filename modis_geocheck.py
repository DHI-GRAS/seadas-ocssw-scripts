#! /usr/bin/env python
from __future__ import print_function

import sys
from modis_utils import modis_env

import modules.modis_GEO_utils as modisGEO
from modules.setupenv import env
from optparse import OptionParser
import os

if __name__ == "__main__":
    geofile = None
    thresh = None
    verbose = False
    geothresh = 95
    version = "%prog 1.0"

    # Read commandline options...
    usage = '''%prog GEOFILE THRESHOLD'''

    parser = OptionParser(usage=usage, version=version)

    parser.add_option("--threshold", dest='geothresh',
                      help="% of geo-populated pixels required to pass geocheck validation test", metavar="THRESHOLD")
    parser.add_option("-v", "--verbose", action="store_true", dest='verbose',
                      default=False, help="print status messages")

    (options, args) = parser.parse_args()

    if args:
        geofile = args[0]
        if not os.path.exists(geofile):
            print ("*** ERROR: Provided geolocation file does not exist.")
            print ("*** Validation test failed for geolocation file:", geofile)
            sys.exit(1)

    else:
        parser.print_help()
        sys.exit(0)

    if options.geothresh:
        geothresh = options.geothresh
    if options.verbose:
        verbose = options.verbose

    # kluge: use geofile as l1afile for setup
    m = modisGEO.modis_geo(file=geofile, geofile=geofile,
                           geothresh=geothresh,
                           verbose=verbose
    )
    env(m)
    modis_env(m)
    m.geochk()
