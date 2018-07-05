#!/usr/bin/env python
from __future__ import print_function

################################################################################
# script for spawning OCSSW processing commands
# Usage: seadasProcessor.py -p (--parfile=parfile), -o (--ocproc=procssor)
#    -s (--sensor)
# parfile options:
#   ocproc - processor
#   ocsen  - sensor
#
################################################################################
__author__ = "Sean Bailey, Futuretech Corporation"
__date__ = "$Oct 8, 2010 02:00:00 PM$"



# TODO Error checking!


import sys

from optparse import OptionParser
import os
from modules.ParamUtils import ParamProcessing
from ProcessWrapper import ProcWrap
import subprocess


ver = sys.version

version = "%prog 1.0"
#global verbose
#verbose = False
parfile = None
processor = None
sensor = None
getanc = False

proc_cmd = {
    'l1agen':{
        'seawifs':'l1agen_seawifs',
        'modis':'modis_L0_to_L1A.py',
        'czcs':'l1agen_czcs',
        },
    'l1bgen':{
        'seawifs':'l1bgen',
        'modis':'modis_L1A_to_L1B.py',
        },
    'geogen':{
        'modis':'modis_L1A_to_GEO.py',
        },
    'l1aextract':{
        'seawifs':'l1aextract_seawifs',
        'modisa':'l1aextract_modis',
        'modist':'l1aextract_modis',
        },
    }

nonpar = ['l1agen_seawifs', 'l1agen_czcs', 'l1aextract_seawifs',
    'l1aextract_modis', 'l2extract', 'l2brsgen', 'smitoppm']

def processParFile(parfile=None, params=None, processor=None, sensor=None,
    getanc=False,phash=None,verbose=False):
    """Execute processing for a given parameter file"""

    if phash is None:
        phash = ParamProcessing(params=params, parfile=parfile)
    if parfile:
        phash.parseParFile()
    pkeys = phash.params.keys()
    phash.genOutputFilename(processor)

    if processor is None:
        try:
            processor = phash.params['main']['ocproc']
        except  Exception:
            try:
                pkeys.remove('main')
                if len(pkeys) == 1:
                    processor = pkeys[0]
                else:
                    print ("Error! More than 1 processor found.... ")
#                    sys.exit(1)
                    status = 1
            except Exception:
                print ("Error! Need to know what process to run.... Exiting")
#                sys.exit(1)
                status = 1


    if sensor is None:
        try:
            sensor = phash.params['main']['ocproc_sensor']
        except Exception:
            pass
#    Check for getanc requirement...
    try:
        getanc = int(phash.params['main']['ocproc_getanc'])
    except Exception:
        pass

    try:
        runproc = proc_cmd[processor][sensor]
    except Exception:
        runproc = processor

    try:
        nonparcode = nonpar.index(runproc)
    except Exception:
        nonparcode = -1

    # Run getanc if necessary...
    if processor in ('l2gen') and getanc:
        if verbose:
            print ("Retrieving ancillary files...")
        fcmd = ''.join(['--file=', phash.params[processor]['ifile']])
        anccmd = ['/Users/Shared/seadas7/trunk/python/getanc.py', fcmd]
        ancstat = subprocess.call(anccmd)
        if ancstat not in (1, 99):
            ancparfile = phash.params[processor]['ifile'] + '.anc'
            phash.parseParFile(ancparfile)
        else:
            print ("Ancillary file retreival failed. Exiting...")
            status = 1
#            sys.exit(1)

    print (phash.params[processor])
    # Set up process command
    if nonparcode >= 0:
        w = ProcWrap(phash.params[processor])
        w.procSelect(runproc)
        cmd = w.procmd
    else:
        parfilename = phash.params[processor]['ifile'] + '.par'
        phash.parfile = parfilename
        phash.buildParameterFile(processor)
        cmd = ['/Users/Shared/OCSSW/run/bin/' + runproc, 'par=' + parfilename]

    print (cmd)
    print ('V',verbose)
    if verbose:
#        print p.parstr
        rstr = ' '.join(cmd)
        print ("Running:\n  ", rstr)
        print (phash.params[processor])
    # Create output and error log files
    try:
        ix = cmd.index('>')
        outFile = cmd[ix+1]
        cmd.remove('>')
        cmd.remove(outFile)
    except Exception:
        outlog = phash.params[processor]['ifile'] + '.log'
        outFile = os.path.join(os.curdir, outlog)

    print (outlog)
    errlog = phash.params[processor]['ifile'] + '.err'
    errFile = os.path.join(os.curdir,errlog)
    outptr = open(outFile, 'w')
    errptr = open(errFile, 'w')

    # Call the subprocess using convenience method
    status = subprocess.call(cmd, 0, None, None, outptr, errptr)
    print ('S', status)
    # Close log handles
    outptr.close()
    errptr.close()


    statptr = open(errFile, 'r')
    statData = statptr.read()
    statptr.close()
    # Check the process exit code
    if not status == 0:
        print ('Error (%s) executing command:\n' % status)
        print ('\t', ' '. join(cmd))
        print ('\n' + statData)
        sys.exit(1)
    else:
        if verbose:
            print (statData)
            print ('Processing successful.')

    return status #phash.params[processor]['ofile']


if __name__ == "__main__":

# Read commandline options...
    usage = "usage: %prog [options] parfile"
    parser = OptionParser(usage=usage, version=version)

    parser.add_option("-o", "--ocproc", dest=processor,
                      help="processor code", metavar="OCPROC")
    parser.add_option("-s", "--sensor", dest=sensor,
                      help="sensor to process", metavar="OCSEN")
    parser.add_option("-q", "--quiet",
                      action="store_false", dest='verbose', default=True,
                      help="don't print status messages to stdout")

    (options, args) = parser.parse_args()

    parfile = args[0]
    processor = options.ocproc
    sensor = options.sensor
    verbose = options.verbose

    if processor:
        prog = processor
    else:
        prog = 'main'

    params = {prog:{}}

    if len(args) > 1:
        for p in args:

            try:
                key, value = p.split('=')
                params[prog][key] = value

            except Exception:
                pass

    if parfile:

        if verbose:
            print ('parfile :', parfile)
            print ('params: ', params)

        processParFile(parfile, params=params, processor=processor, sensor=sensor)

    else:
        print (parser.print_help())
        sys.exit(1)
