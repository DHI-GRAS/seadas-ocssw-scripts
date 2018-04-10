#! /usr/bin/env python
from __future__ import print_function

import os
import subprocess
import tarfile
from optparse import OptionParser

from modules.ParamUtils import ParamProcessing
from modules.ProcUtils import date_convert, addsecs, cat
from modules.aquarius_utils import aquarius_timestamp
from modules.setupenv import env


class GetAncAquarius:
    """
    utilities for Aquarius ancillary data
    """

    def __init__(self, filename=None,
                 start=None,
                 stop=None,
                 ancdir=None,
                 ancdb='ancillary_data.db',
                 curdir=False,
                 verbose=False,
                 printlist=True,
                 download=True,
                 refreshDB=False):

        self.filename = filename
        self.start = start
        self.stop = stop
        self.printlist = printlist
        self.verbose = verbose
        self.curdir = curdir
        self.ancdir = ancdir
        self.ancdb = ancdb
        self.dl = download
        self.refreshDB = refreshDB
        self.dirs = {}
        self.ancfiles = {}

    def parse_anc(self, anc_filelist):
        anc = ParamProcessing(parfile=anc_filelist)
        anc.parseParFile()
        self.ancfiles = anc.params['main']

    def write_anc(self, anc_filelist):
        anc = ParamProcessing(parfile=anc_filelist)
        anc.params['main'] = self.ancfiles
        anc.buildParameterFile('main')

    def run_mk_anc(self, count):
        """
        Run mk_aquarius_ancillary_data to create the "y" files
        """

        dt = self.start
        atm = 'atm1'
        met = 'met1'

        if count == 2:
            dt = self.stop
            atm = 'atm2'
            met = 'met2'

        hour = os.path.basename(self.ancfiles[met])[8:10]

        sdt = date_convert(dt, 'j', 'd')
        edt = date_convert(addsecs(dt, 86500, 'j'), 'j', 'd')

        yancfilename = ''.join(['y', sdt, hour, '.h5'])

        # Make the yancfile
        if self.verbose:
            print("")
            print("Creating Aquarius yancfile%s %s..." % (count, yancfilename))
        mk_anc = os.path.join(self.dirs['bin'], 'mk_aquarius_ancillary_data')
        mk_anc_cmd = ' '.join([mk_anc,
                               self.ancfiles['sstfile1'],
                               self.ancfiles['sstfile2'],
                               self.ancfiles[atm],
                               self.ancfiles[met],
                               self.ancfiles['swhfile'],
                               self.ancfiles['frozenfile'],
                               self.ancfiles['icefile1'],
                               self.ancfiles['icefile2'],
                               self.ancfiles['sssfile1'],
                               self.ancfiles['sssfile2'],
                               self.ancfiles['argosfile1'],
                               self.ancfiles['argosfile2'],
                               sdt, edt])
        status = subprocess.call(mk_anc_cmd, shell=True)
        if status:
            if self.verbose:
                print("mk_aquarius_ancillary_data returned with exit status: "
                      + str(status))
                print('command: ' + mk_anc_cmd)
            return None

        # add info from MERRA file
        geos = os.path.join(self.dirs['bin'], 'geos')
        geos_cmd = ' '.join([geos, yancfilename, self.ancfiles['geosfile']])
        status = subprocess.call(geos_cmd, shell=True)
        if status:
            if self.verbose:
                print('geos returned with exit status: ' + str(status))
                print('command: ' + geos_cmd)
            return None

        # success!
        if self.verbose:
            print("yancfile %s created successfully!" % yancfilename)
        return yancfilename


if __name__ == "__main__":
    filename = None
    start = None
    stop = None
    ancdir = None
    ancdb = 'ancillary_data.db'
    curdir = False
    download = True
    force = False
    refreshDB = False
    verbose = False
    printlist = True
    anc_filelist = None

    version = "%prog 1.0"

    # Read commandline options...
    usage = '''
        %prog [OPTIONS] FILE

        This program does the following:

        1) executes getanc.py for Aquarius L1 files. If an input file is
        specified the start and end times are determined automatically,
        otherwise a start time must be provided by the user.

        2) runs the mk_aquarius_ancillary_data program to create the "y-files"
        required as input to l2gen_aquarius.

        3) retrieves and un-tars the scatterometer files
    '''

    parser = OptionParser(usage=usage, version=version)

    parser.add_option("-s", "--start", dest='start',
                      help="Start time of the orbit (if used, no input file is required)", metavar="START")
    parser.add_option("-e", "--stop", dest='stop',
                      help="Stop time of the orbit", metavar="STOP")
    parser.add_option("--ancdir", dest='ancdir',
                      help="Use a custom directory tree for ancillary files", metavar="ANCDIR")
    parser.add_option("--ancdb", dest='ancdb',
                      help="Use a custom file for ancillary database. If full path not given, ANCDB is assumed to "
                           "exist (or will be created) under $OCSSWROOT/log/. If $OCSSWROOT/log/ does not exist, "
                           "ANCDB is assumed (or will be created) under the current working directory", metavar="ANCDB")
    parser.add_option("-c", "--curdir", action="store_true", dest='curdir',
                      default=False, help="Download ancillary files directly into current working directory")
    parser.add_option("-d", "--disable-download", action="store_false", dest='download',
                      default=True, help="Disable download of ancillary files not found on hard disk")
    parser.add_option("-f", "--force-download", action="store_true", dest='force',
                      default=False, help="Force download of ancillary files, even if found on hard disk")
    parser.add_option("-r", "--refreshDB", action="store_true", dest='refreshDB',
                      default=False, help="Remove existing database records and re-query for ancillary files")

    parser.add_option("-v", "--verbose", action="store_true", dest='verbose',
                      default=False, help="print status messages")
    parser.add_option("--noprint", action="store_false", dest='printlist',
                      default=True, help="Supress printing the resulting list of files to the screen")

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

    if options.download is False:
        download = options.download
    if options.force:
        force = options.force
    if options.refreshDB:
        refreshDB = options.refreshDB
    if options.printlist is False:
        printlist = options.printlist

    if file is None and start is None:
        parser.print_help()
        exit(0)

    g = GetAncAquarius(filename=filename,
                       start=start,
                       stop=stop,
                       curdir=curdir,
                       ancdir=ancdir,
                       ancdb=ancdb,
                       verbose=verbose,
                       printlist=printlist,
                       download=download,
                       refreshDB=refreshDB)

    env(g)
    if not g.start:
        (g.start, g.stop, sensor) = aquarius_timestamp(filename)

    # Run getanc.py
    getanc = os.path.join(g.dirs['scripts'], 'getanc.py')
    if filename:
        getanc_cmd = ' '.join([getanc, '--mission=aquarius --noprint', filename])
    else:
        getanc_cmd = ' '.join([getanc, '--mission=aquarius --noprint', '-s', start])
        if stop:
            getanc_cmd += ' -e ' + stop

    if verbose:
        getanc_cmd += ' --verbose'
    if refreshDB:
        getanc_cmd += ' --refreshDB'
    if force:
        getanc_cmd += ' --force'

    # print(getanc_cmd)
    status = subprocess.call(getanc_cmd, shell=True)

    if status and self.verbose:
        print('getanc returned with exit status: ' + str(status))
        print('command: ' + getanc_cmd)

    if filename is None:
        anc_filelist = start + ".anc"
    else:
        anc_filelist = '.'.join([os.path.basename(filename), 'anc'])

    g.parse_anc(anc_filelist)
    anclist = g.ancfiles.keys()

    # create yancfiles
    g.ancfiles['yancfile1'] = g.run_mk_anc(1)
    g.ancfiles['yancfile2'] = g.run_mk_anc(2)
    if not (g.ancfiles['yancfile1'] and g.ancfiles['yancfile2']):
        print('ERROR in making yancfiles!')
        exit(1)

    # extract scatterometer files
    if 'scat' in g.ancfiles:
        tar = tarfile.open(g.ancfiles['scat'])
        tar.extractall()
        tar.close()

    # clean up anc_filelist to remove files contained in the yancfiles
    for key in anclist:
        if key not in ('xrayfile1', 'xrayfile2',
                       'l2_uncertainties_file', 'sif_file'):
            del (g.ancfiles[key])

    # save original
    os.rename(anc_filelist, anc_filelist + '.orig')

    # write out the cleaned .anc file
    g.write_anc(anc_filelist)
    if verbose or printlist:
        cat(anc_filelist)
