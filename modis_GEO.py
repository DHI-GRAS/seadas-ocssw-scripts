#! /usr/bin/env python
import anc_utils
from modules.modis_utils import buildpcf, modis_env

import modules.modis_GEO_utils as modisGEO
import resource
from optparse import OptionParser
from modules.setupenv import env


if __name__ == "__main__":
    file = None
    parfile = None
    geofile = None
    att1 = None
    att2 = None
    eph1 = None
    eph2 = None
    entrained = False
    dem = False
    refreshDB = False
    download = True
    ancdir = None
    ancdb = 'ancillary_data.db'
    geothresh = 95
    log = False
    verbose = False
    version = "%prog 1.0"

    # Read commandline options...
    usage = '''
    %prog [OPTIONS] MODIS_L1A_file
            or
    %prog --parfile=parameter_file [OPTIONS]
    '''

    parser = OptionParser(usage=usage, version=version)

    parser.add_option("-p", "--parfile", dest='par',
        help="Parameter file containing program inputs", metavar="PARFILE")
    parser.add_option("-o", "--output", dest='geofile',
        help="Output filename", metavar="GEOFILE")
    parser.add_option("-a", "--att1", dest='att1',
        help="Input attitude  file 1 (chronological)", metavar="ATT1")
    parser.add_option("-A", "--att2", dest='att2',
        help="Input attitude  file 2 (chronological)", metavar="ATT2")
    parser.add_option("-e", "--eph1", dest='eph1',
        help="Input ephemeris file 1 (chronological)", metavar="EPH1")
    parser.add_option("-E", "--eph2", dest='eph2',
        help="Input ephemeris file 2 (chronological)", metavar="EPH2")
    parser.add_option("--ancdir", dest='ancdir',
        help="Use a custom directory tree for ancillary files", metavar="ANCDIR")
    ancdb_help_text = "Use a custom file for ancillary database. If " \
                      "full path not given, ANCDB is assumed to exist " \
                      "(or will be created) under " \
                      + anc_utils.DEFAULT_ANC_DIR_TEXT + \
                      "/log/. If " + anc_utils.DEFAULT_ANC_DIR_TEXT + \
                      "/log/ does not exist,  " \
                      "ANCDB is assumed (or will be created) under the " \
                      "current working directory"
    parser.add_option("--ancdb", dest='ancdb', help=ancdb_help_text, metavar="ANCDB")
    parser.add_option("--threshold", dest='geothresh',
        help="% of geo-populated pixels required to pass geocheck validation test", metavar="THRESHOLD")
    parser.add_option("-r", "--refreshDB", action="store_true", dest='refreshDB',
        default=False, help="Remove existing database records and re-query for ancillary files")
    parser.add_option("--disable-download", action="store_false", dest='download',
        default=True, help="Disable download of ancillary files not found on hard disk")
    parser.add_option("-d", "--enable-dem", action="store_true", dest='dem',
        default=False, help="Enable MODIS terrain elevation correction")
    parser.add_option("-v", "--verbose", action="store_true", dest='verbose',
        default=False, help="print status messages")
    parser.add_option("-n", "--entrained", action="store_true", dest='entrained',
        default=False, help="Use entrained attitude for Terra")
    parser.add_option("--log", action="store_true", dest='log',
        default=False, help="Save processing log file(s)")

    options, args = parser.parse_args()

    if args:
        file = args[0]
    if options.geofile:
        geofile = options.geofile
    if options.verbose:
        verbose = options.verbose
    if options.att1:
        att1 = options.att1
    if options.att2:
        att2 = options.att2
    if options.eph1:
        eph1 = options.eph1
    if options.eph2:
        eph2 = options.eph2
    if options.dem:
        dem = options.dem
    if options.geothresh:
        geothresh = options.geothresh
    if options.log:
        log = options.log
    if options.par:
        parfile = options.par
    if options.ancdir:
        ancdir = options.ancdir
    if options.ancdb:
        ancdb = options.ancdb
    if options.refreshDB:
        refreshDB = options.refreshDB
    if options.download is False:
        download = options.download
    if options.entrained:
        entrained = options.entrained

    if file is None and parfile is None:
        parser.print_help()
        exit(0)

    # Set stacksize - if able to (Mac can't, but code is compiled to use a
    # larger stack on the Mac...)
    try:
        resource.setrlimit(3, [-1,-1])
    except Exception:
        pass

    m = modisGEO.modis_geo(file=file,
        parfile=parfile,
        geofile=geofile,
        a1=att1,
        a2=att2,
        e1=eph1,
        e2=eph2,
        terrain=dem,
        geothresh=geothresh,
        ancdir=ancdir,
        ancdb=ancdb,
        refreshDB=refreshDB,
        download=download,
        entrained=entrained,
        log=log,
        verbose=verbose
    )

    env(m)
    modis_env(m)
    m.chk()
    m.utcleap()
    if entrained is False:
        try:
            m.atteph()
        except SystemExit:
            print "Cannot create geolocation from %s; exiting." % file
            raise
    buildpcf(m)
    m.run()
