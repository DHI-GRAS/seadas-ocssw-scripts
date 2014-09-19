#! /usr/bin/env python

"""
Wrapper program for running the l1bgen program on MODIS L1A files.
"""

from modules.modis_utils import buildpcf, modis_env

import modules.modis_L1B_utils as modisL1B
from optparse import OptionParser
from modules.setupenv import env
import resource
import sys

def main():
    """
    This is the primary driver function for the modis_L1B.py program.
    """
    l1a_file = None
    parfile = None
    geofile = None
    okm = None
    hkm = None
    qkm = None
    obc = None
    lutver = None
    lutdir = None
    delfiles = 0
    log = False
    verbose = False
    version = "%prog 1.0"

    delfilekey = {'1KM':1, 'HKM':2, 'QKM':4, 'OBC':8}
    # Read commandline options...
    usage = '''
    %prog [OPTIONS] L1AFILE [GEOFILE]
        if GEOFILE is not provided, assumed to be basename of L1AFILE + '.GEO'
            or
    %prog --parfile=parameter_file [OPTIONS]
    '''

    parser = OptionParser(usage=usage, version=version)

    parser.add_option("-p", "--parfile", dest='par',
        help="Parameter file containing program inputs", metavar="PARFILE")

    parser.add_option("-o", "--okm", dest='okm',
        help="Output MODIS L1B 1KM HDF filename", metavar="1KMFILE")
    parser.add_option("-k", "--hkm", dest='hkm',
        help="Output MODIS L1B HKM HDF filename", metavar="HKMFILE")
    parser.add_option("-q", "--qkm", dest='qkm',
        help="Output MODIS L1B QKM HDF filename", metavar="QKMFILE")
    parser.add_option("-c", "--obc", dest='obc',
        help="Output MODIS L1B OBC HDF filename", metavar="OBCFILE")

    parser.add_option("-l", "--lutver", dest='lutver',
        help="L1B LUT version number", metavar="LUTVER")
    parser.add_option("-d", "--lutdir", dest='lutdir',
        help="Path of directory containing LUT files", metavar="LUTDIR")

    parser.add_option("-x", "--del-okm", action="store_true", dest='okmdel',
        default=False, help="Delete 1km  resolution L1B file")
    parser.add_option("-y", "--del-hkm", action="store_true", dest='hkmdel',
        default=False, help="Delete 500m resolution L1B file")
    parser.add_option("-z", "--del-qkm", action="store_true", dest='qkmdel',
        default=False, help="Delete 250m resolution L1B file")
    parser.add_option("--keep-obc", action="store_false", dest='obcdel',
        default=True, help="Save onboard calibration file")

    parser.add_option("-v", "--verbose", action="store_true", dest='verbose',
        default=False, help="print status messages")
    parser.add_option("--log", action="store_true", dest='log',
        default=False, help="Save processing log file(s)")

    (options, args) = parser.parse_args()

    if args:
        l1a_file = args[0]
        if len(args) == 2:
            geofile = args[1]

    if options.okm:
        okm = options.okm
    elif options.okmdel:
        delfiles = delfiles + delfilekey['1KM']
    if options.hkm:
        hkm = options.hkm
    elif options.hkmdel:
        delfiles = delfiles + delfilekey['HKM']
    if options.qkm:
        qkm = options.qkm
    elif options.qkmdel:
        delfiles = delfiles + delfilekey['QKM']
    if options.obc:
        obc = options.obc
    elif options.obcdel:
        delfiles = delfiles + delfilekey['OBC']

    if options.lutver:
        lutver = options.lutver
    if options.lutdir:
        lutdir = options.lutdir

    if options.verbose:
        verbose = options.verbose
    if options.log:
        log = options.log
    if options.par:
        parfile = options.par

    if l1a_file is None and parfile is None:
        parser.print_help()
        exit(0)

    # Set stacksize - if able to (Mac can't, but code is compiled to use a
    # larger stack on the Mac...)
    try:
        resource.setrlimit(resource.RLIMIT_STACK, (resource.RLIM_INFINITY, resource.RLIM_INFINITY))
    except Exception:
        pass


    l1b_instance = modisL1B.ModisL1B(inp_file=l1a_file,
                                   parfile=parfile,
                                   geofile=geofile,
                                   okm=okm,
                                   hkm=hkm,
                                   qkm=qkm,
                                   obc=obc,
                                   lutver=lutver,
                                   lutdir=lutdir,
                                   delfiles=delfiles,
                                   log=log,
                                   verbose=verbose
    )
    env(l1b_instance)
    modis_env(l1b_instance)
    l1b_instance.chk()
    buildpcf(l1b_instance)
    l1b_instance.run()
    return 0

if __name__ == "__main__":
    sys.exit(main())
