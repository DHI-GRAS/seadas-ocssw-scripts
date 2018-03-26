#! /usr/bin/python
from __future__ import print_function

# Processing control script

__author__="sbailey"
__date__ ="$Sep 27, 2010 3:29:48 PM$"

from optparse import OptionParser
import os
import sys
global verbose
verbose = False

from modules.ParamUtils import ParamProcessing
from ProcessParFile import processParFile


procmds = ['l1agen', 'l1aextract', 'l1brsgen', 'l1bgen', 'l1mapgen', 'l2gen',
'l2brsgen', 'l2extract', 'l2mapgen', 'l2bin', 'l3bin', 'l3gen', 'smigen',
'smitoppm']

if __name__ == "__main__":

    version = "%prog 1.0"
    sensor = None
# Read commandline options...
    usage = "usage: %prog [options] parfile"
    parser = OptionParser(usage=usage, version=version)

    parser.add_option("-s", "--sensor", dest=sensor,
                      help="sensor to process", metavar="OCSEN")
    parser.add_option("-v", "--verbose",
                      action="store_true", dest='verbose', default=False,
                      help="don't print status messages to stdout")

    (options, args) = parser.parse_args()

    parfile = args[0]
    sensor = options.sensor
    verbose = options.verbose

    print (verbose)
    prog = 'main'
    OCSSWROOT = os.getenv('OCSSWROOT')
    print (OCSSWROOT)

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
            print ('test')

        p = ParamProcessing(params=params, parfile=parfile)
        p.parseParFile()
        filelst = p.params['main']['ocproc_ifile'].split(',')
        procs = p.params.keys()
        print (procs)
        r = ParamProcessing(params=params)

        procpool = {}
        for prog in procmds:
            stat = 0
            try:
                ix = procs.index(prog)
                print (filelst)
                if ix >= 0:
                    print (prog)
#                    try:
#                        procpool[prog]
#                    except:
#                        progfiles[prog]={'ifiles'}
                    #print r.params[prog]
                    #params = r.params[prog]
                    #print 'R',params

                    #r.params.update(p.params['main'])
                    for ifile in filelst:
                        progfiles[prog]
                        params['ifile'] = ifile
                        r.params[prog]['ifile'] = ifile
                        r.genOutputFilename(prog)
                        ofile = r.params[prog]['ofile']
                        print (ifile, ofile)
                        stat = processParFile(phash=r,params=params, processor=prog, sensor=sensor,verbose=verbose)
                        filelst.remove(ifile)
                        filelst.append(ofile)
                        print ('O',stat)

            except Exception:
                pass
            if stat > 0:
                sys.exit(1)
    else:
        print (parser.print_help())
        sys.exit(1)
