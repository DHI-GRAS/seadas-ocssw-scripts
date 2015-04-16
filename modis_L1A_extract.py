#! /usr/bin/env python

import anc_utils
from optparse import OptionParser
import resource
from modules.modis_utils import buildpcf, modis_env
import modules.modis_l1aextract_utils as ex
import modules.modis_GEO_utils as ga
from modules.setupenv import env
import modules.ParamUtils
import sys

if __name__ == "__main__":
    file = None
    parfile = None
    sub_l1a = None
    geofile = None
    log = False
    north = None
    south = None
    west = None
    east = None
    extract_geo = None
    ancdb = 'ancillary_data.db'
    ancdir = None
    dirs = {}
    verbose = False
    version = "%prog 1.0"
    att1 = None
    att2 = None
    eph1 = None
    eph2 = None

    # Read commandline options...
    #Usage: modis_L1A_extract.csh L1A_file GEO_file SWlon SWlat NElon NElat Output_L1A_file [Output_GEO_file]

    usage = '''
    %prog [OPTIONS] L1AFILE [-g GEOFILE] [-o EXTRACTFILE] -n NORTH -s SOUTH -w WEST -e EAST
        if GEOFILE is not provided, assumed to be basename of L1AFILE + '.GEO'
            or
    %prog --par parameter_file [OPTIONS]
    '''

    parser = OptionParser(usage=usage, version=version)

    parser.add_option("-p", "--parfile", dest='par',
                      help="Parameter file containing program inputs", metavar="PARFILE")
    parser.add_option("-o", "--output", dest='sub_l1a',
                      help="Output L1A extract filename - defaults to L1AFILE.sub", metavar="EXTRACTFILE")
    parser.add_option("-g", "--geofile", dest='geofile',
                      help="INPUT L1A GEOFILE filename - defaults to basename of L1AFILE +'.GEO'", metavar="GEOFILE")
    parser.add_option("-n", "--north", dest='north',
                      help="Northernmost desired latitude", metavar="NORTH")
    parser.add_option("-s", "--south", dest='south',
                      help="Southernmost desired latitude", metavar="SOUTH")
    parser.add_option("-w", "--west", dest='west',
                      help="Westernmost desired longitude", metavar="WEST")
    parser.add_option("-e", "--east", dest='east',
                      help="Easternmost desired longitude", metavar="EAST")
    parser.add_option("--extract_geo", dest="extract_geo",
                      help="extract geolocation filename", metavar="EXGEO")
    parser.add_option("--att1", dest='att1',
        help="Input attitude  file 1 (chronological)", metavar="ATT1")
    parser.add_option("--att2", dest='att2',
        help="Input attitude  file 2 (chronological)", metavar="ATT2")
    parser.add_option("--eph1", dest='eph1',
        help="Input ephemeris file 1 (chronological)", metavar="EPH1")
    parser.add_option("--eph2", dest='eph2',
        help="Input ephemeris file 2 (chronological)", metavar="EPH2")
    ancdb_help_text = "Use a custom file for ancillary database. If " \
                      "full path not given, ANCDB is assumed to exist "\
                      "(or will be created) under " + \
                      anc_utils.DEFAULT_ANC_DIR_TEXT + "/log/. If " + \
                      anc_utils.DEFAULT_ANC_DIR_TEXT + "/log/ does not " \
                      "exist, ANCDB is assumed (or will be created) " \
                      "under the current working directory"
    parser.add_option("--ancdb", dest='ancdb',
        help=ancdb_help_text, metavar="ANCDB")
    parser.add_option("--ancdir", dest='ancdir',
        help="Use a custom directory tree for ancillary files", metavar="ANCDIR")
    parser.add_option("-v", "--verbose", action="store_true", dest='verbose',
                      default=False, help="print status messages")
    parser.add_option("--log", action="store_true", dest='log',
                      default=False, help="Save processing log file(s)")

    options, args = parser.parse_args()

    if options.par is None and ((isinstance(args, list) and len(args) == 0) or
                                args is None):
        parser.print_help()
        sys.exit(0)

    if args:
        file = args[0]

    if options.sub_l1a:
        sub_l1a = options.sub_l1a
    else:
        sub_l1a = "%s.sub" % file
    if options.geofile:
        geofile = options.geofile
    if options.north:
        north = float(options.north)
    if options.south:
        south = float(options.south)
    if options.west:
        west = float(options.west)
    if options.east:
        east = float(options.east)
    if options.verbose:
        verbose = options.verbose
    if options.log:
        log = options.log
    if options.extract_geo:
        extract_geo = options.extract_geo
    if options.ancdb:
        ancdb = options.ancdb
    if options.ancdir:
        ancdir = options.ancdir
    if options.par:
        parfile = options.par
    if options.att1:
        att1 = options.att1
    if options.att2:
        att2 = options.att2
    if options.eph1:
        eph1 = options.eph1
    if options.eph2:
        eph2 = options.eph2


    # Set stacksize - if able to (Mac can't, but code is compiled to use a
    # larger stack on the Mac...)
    try:
        resource.setrlimit(resource.RLIMIT_STACK, (resource.RLIM_INFINITY, resource.RLIM_INFINITY))
    except Exception:
        pass

    m = ex.extract(file=file,
                   parfile=parfile,
                   geofile=geofile,
                   outfile=sub_l1a,
                   log=log,
                   north=north,
                   south=south,
                   west=west,
                   east=east,
                   verbose=verbose)

    env(m)
    modis_env(m)
    m.chk()
    status = m.run()
    if not status:
    # Create geolocation file for extract
        g = ga.modis_geo(file=sub_l1a,
                         geofile=extract_geo,
                         ancdb=ancdb,
                         ancdir=ancdir,
                         a1=att1,
                         a2=att2,
                         e1=eph1,
                         e2=eph2,
                         log=log,
                         verbose=verbose)

        env(g)
        modis_env(g)
        g.atteph()
        buildpcf(g)

        g.run()
    else:
        exit(status)
