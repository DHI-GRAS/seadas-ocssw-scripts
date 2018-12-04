#! /usr/bin/env python

"""
Program to check for updated ancillary data files and download them
as appropriate.
"""

from optparse import OptionParser

import modules.anc_utils as ga
from modules.setupenv import env

def main():
    """
    The main function for the program. Gets and checks command line options, instantiates 
    a getanc object (from the class defined in anc_utils) and then calls the methods to 
    get the ancillary data.
    """

    filename = None
    start = None
    stop = None
    ancdir = None
    ancdb = 'ancillary_data.db'
    curdir = False
    opt_flag = 5  # defaults to retrieving met, ozone, sst, and ice data
    download = True
    force = False
    refreshDB = False
    verbose = False
    printlist = True
    sensor = None
    timeout = 10.

    version = "%prog 2.1"

    # Read commandline options...
    usage = """
    %prog [OPTIONS] FILE
          or
    -s,--start YYYYDDDHHMMSS [-e,--end YYYDDDHHMMSS]  [OPTIONS]

      FILE  Input L1A or L1B file

    NOTE: Currently NO2 climatological data is used for OBPG operational
          processing, so to match OBPG distributed data products, the default
          behaviour disables NO2 searching.

    This program queries an OBPG server and optionally downloads the optimal
    ancillary data files for Level-1 to Level-2 processing. If an input file
    is specified the start and end times are determined automatically, otherwise
    a start time must be provided by the user.

    A text file (with the extension '.anc') is created containing parameters
    that can be directly used as input to the l2gen program for optimal Level-1
    to Level-2 processing, e.g.:

         l2gen ifile=<infile> ofile=<outfile> par=<the *.anc text file>

    EXIT STATUS:
        0  : all optimal ancillary files exist and are present on the locally
        99 : an error was encountered; no .anc parameter text file was created
        31 : no ancillary files currently exist corresponding to the start
             time and therefore no .anc parameter text file was created
      1-30 : bitwise value indicating one or more files are not optimal:

             bit 0 set = missing one or more MET files
             bit 1 set = missing one or more OZONE files
             bit 2 set = no SST file found
             bit 3 set = no NO2 file found
             bit 4 set = no ICE file found

    e.g. STATUS=11 indicates there are missing optimal MET, OZONE, and NO2 files

    """

    parser = OptionParser(usage=usage, version=version)

    parser.add_option("-s", "--start", dest='start',
                      help="Time of the first scanline (if used, no input file is required)",
                      metavar="START")
    parser.add_option("-e", "--stop", dest='stop',
                      help="Time of last scanline", metavar="STOP")
    parser.add_option("--ancdir", dest='ancdir',
                      help="Use a custom directory tree for ancillary files",
                      metavar="ANCDIR")

    ancdb_help_text = "Use a custom file for ancillary database. If full " \
                      "path not given, ANCDB is assumed to exist (or " \
                      "will be created) under " + ga.DEFAULT_ANC_DIR_TEXT + \
                      "/log/. If " + ga.DEFAULT_ANC_DIR_TEXT + "/log/ does " \
                                                               "not exist, ANCDB is assumed (or will be created) " \
                                                               " under the current working directory"

    parser.add_option("--ancdb", dest='ancdb',
                      help=ancdb_help_text, metavar="ANCDB")

    parser.add_option("-c", "--curdir", action="store_true", dest='curdir',
                      default=False,
                      help="Download ancillary files directly into current working directory")
    parser.add_option("-m", "--mission", dest="sensor", help="Mission name",
                      metavar="MISSION")
    parser.add_option("-d", "--disable-download", action="store_false",
                      dest='download',
                      default=True,
                      help="Disable download of ancillary files not found on hard disk")
    parser.add_option("-f", "--force-download", action="store_true",
                      dest='force', default=False,
                      help="Force download of ancillary files, even if found on hard disk")
    parser.add_option("-r", "--refreshDB", action="store_true",
                      dest='refreshDB', default=False,
                      help="Remove existing database records and re-query for ancillary files")
    parser.add_option("-i", "--ice", action="store_false", dest='ice',
                      default=True,
                      help="Do not search for sea-ice ancillary data")
    parser.add_option("-n", "--no2", action="store_true", dest='no2',
                      default=False, help="Search for NO2 ancillary data")
    parser.add_option("-t", "--sst", action="store_false", dest='sst',
                      default=True,
                      help="Do not search for SST ancillary data")
    parser.add_option("-v", "--verbose", action="store_true", dest='verbose',
                      default=False, help="print status messages")
    parser.add_option("--noprint", action="store_false", dest='printlist',
                      default=True,
                      help="Suppress printing the resulting list of files to the screen")
    parser.add_option("--timeout", dest='timeout', metavar="TIMEOUT",
                      help="set the network timeout in seconds")

    (options, args) = parser.parse_args()

    if args:
        filename = args[0]
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
    if options.sensor:
        sensor = options.sensor
    if options.download is False:
        download = options.download
    if options.force:
        force = options.force
    if options.refreshDB:
        refreshDB = options.refreshDB
    if options.printlist is False:
        printlist = options.printlist
    if options.timeout:
        timeout = float(options.timeout)

    if filename is None and start is None:
        parser.print_help()
        exit(0)

    g = ga.getanc(file=filename,
                  start=start,
                  stop=stop,
                  ancdir=ancdir,
                  ancdb=ancdb,
                  curdir=curdir,
                  sensor=sensor,
                  opt_flag=opt_flag,
                  verbose=verbose,
                  printlist=printlist,
                  download=download,
                  timeout=timeout,
                  refreshDB=refreshDB)

    if options.sst is False:
        g.set_opt_flag('sst', off=True)
    if options.no2:
        g.set_opt_flag('no2')
    if options.ice is False:
        g.set_opt_flag('ice', off=True)

    env(g)
    g.chk()
    if filename and g.finddb():
        g.setup()
    else:
        g.setup()
        g.findweb()
    g.locate(forcedl=force)
    g.write_anc_par()
    g.cleanup()
    return(g.db_status)

if __name__ == "__main__":
    exit(main())
