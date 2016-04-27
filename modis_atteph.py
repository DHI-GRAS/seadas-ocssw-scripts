#! /usr/bin/env python


import modules.anc_utils as ga
from optparse import OptionParser
from modules.setupenv import env
import os
from modules.ProcUtils import check_sensor

if __name__ == "__main__":
    filename = None
    mission = None
    start = None
    stop = None
    verbose = False
    ancdir = None
    ancdb = 'ancillary_data.db'
    curdir = False
    download = True
    force = False
    refreshDB = False
    version = "%prog 2.1"
    timeout = 10.0
    
    # Read commandline options...
    usage = '''
    %prog L1A_file
             or
    %prog -m a|aqua|t|terra -s YYYYDDDHHMMSS -e YYYYDDDHHMMSS'''

    parser = OptionParser(usage=usage, version=version)

    parser.add_option("-m", "--mission", dest='mission',
                      help="MODIS mission - A(qua) or T(erra)",
                      metavar="MISSION")
    parser.add_option("-s", "--start", dest='start',
                      help="Granule start time (YYYYDDDHHMMSS)",
                      metavar="START")
    parser.add_option("-e", "--stop", dest='stop',
                      help="Granule stop time (YYYYDDDHHMMSS)",
                      metavar="STOP")
    parser.add_option("--ancdir", dest='ancdir',
                      help="Use a custom directory tree for ancillary files",
                      metavar="ANCDIR")
    ancdb_help_text = "Use a custom file for ancillary database. If " \
                      "full path not given, ANCDB is assumed to exist "\
                      "(or will be created) under " + \
                      ga.DEFAULT_ANC_DIR_TEXT + "/log/. If " + \
                      ga.DEFAULT_ANC_DIR_TEXT + "/log/ does not exist, " \
                      "ANCDB is assumed (or will be created) under the " \
                      "current working directory"
    parser.add_option("--ancdb", dest='ancdb',
                      help=ancdb_help_text, metavar="ANCDB")
    parser.add_option("-c", "--curdir", action="store_true", dest='curdir',
                      default=False,
                      help="Download ancillary files directly into current working directory")
    parser.add_option("-d", "--disable-download", action="store_false",
                      dest='download', default=True,
                      help="Disable download of ancillary files not found on hard disk")
    parser.add_option("-f", "--force-download", action="store_true",
                      dest='force', default=False,
                      help="Force download of ancillary files, even if found on hard disk")
    parser.add_option("-r", "--refreshDB", action="store_true",
                      dest='refreshDB', default=False,
                      help="Remove existing database records and re-query for ancillary files")
    parser.add_option("-v", "--verbose", action="store_true", dest='verbose',
                      default=False, help="print status messages")
    parser.add_option("--timeout", dest='timeout', metavar="TIMEOUT",
                      help="set the network timeout in seconds")

    (options, args) = parser.parse_args()

    if args:
        filename = args[0]
    if options.mission:
        mission = options.mission
    if options.verbose:
        verbose = options.verbose
    if options.start:
        start = options.start
    if options.stop:
        stop = options.stop
    if options.ancdir:
        ancdir = options.ancdir
    if options.ancdb:
        ancdb = options.ancdb
    if options.curdir:
        curdir = options.curdir
    if options.download is False:
        download = options.download
    if options.force:
        force = options.force
    if options.refreshDB:
        refreshDB = options.refreshDB
    if options.timeout:
        timeout = options.timeout

    if (filename is None) and (mission is None and start is None):
        parser.print_help()
        exit()

    m = ga.getanc(file=filename,
                  start=start,
                  stop=stop,
                  ancdir=ancdir,
                  curdir=curdir,
                  ancdb=ancdb,
                  sensor=mission,
                  download=download,
                  refreshDB=refreshDB,
                  atteph=True,
                  verbose=verbose,
                  timeout=timeout)

    env(m)
    m.chk()
    if m.sensor is None and os.path.exists(filename):
        m.sensor = check_sensor(filename)
    if filename and m.finddb():
        m.setup()
    else:
        m.setup()
        m.findweb()

    m.locate(forcedl=force)
    m.write_anc_par()
    m.cleanup()

    exit(m.db_status)