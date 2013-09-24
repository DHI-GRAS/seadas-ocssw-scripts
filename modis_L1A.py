#! /usr/bin/env python
from modules.modis_utils import buildpcf, modis_env

import modules.modis_L1A_utils as modisL1A
from optparse import OptionParser
from modules.setupenv import env

if __name__ == "__main__":
    file = None
    parfile = None
    l1a = None
    nextgranule = None
    startnudge = 0
    stopnudge = 0
    mission = None
    fix = True
    log = False
    verbose = False
    version = "%prog 1.0"

    # Read commandline options...
    usage = '''
    %prog [OPTIONS] MODIS_L0_file
            or
    %prog --parfile=parameter_file [OPTIONS]
    '''

    parser = OptionParser(usage=usage, version=version)

    parser.add_option("-p", "--parfile", dest='par',
                      help="Parameter file containing program inputs", metavar="PARFILE")
    parser.add_option("-o", "--output", dest='l1a',
                      help="Output L1A filename - defaults to '(A|T)YYYYDDDHHMMSS.L1A_LAC'", metavar="L1AFILE")
    parser.add_option("-m", "--mission", dest='mission',
                      help="MODIS mission - A(qua) or T(erra)", metavar="MISSION")
    parser.add_option("-s", "--startnudge", dest='startnudge',
                      help="Level-0 start-time offset (seconds)", metavar="STARTNUDGE")
    parser.add_option("-e", "--stopnudge", dest='stopnudge',
                      help="Level-0 stop-time offset (seconds)", metavar="STOPNUDGE")
    parser.add_option("-n", "--nextgranule", dest='nextgranule',
                      help="Next L0 granule (for geolocation of last scan; sets stopnudge=0)",
                      metavar="NEXT")
    parser.add_option("-v", "--verbose", action="store_true", dest='verbose',
                      default=False, help="print status messages")
    parser.add_option("--log", action="store_true", dest='log',
                      default=False, help="Save processing log file(s)")
    parser.add_option("-d", "--disableL0fix", action="store_false", dest='fix',
                      default=True, help="Disable use of l0fix_modis utility for corrupt packets")

    options, args = parser.parse_args()

    if args:
        file = args[0]
    if options.mission:
        mission = options.mission
    if options.verbose:
        verbose = options.verbose
    if options.startnudge:
        startnudge = options.startnudge
    if options.stopnudge:
        stopnudge = options.stopnudge
    if options.nextgranule:
        nextgranule = options.nextgranule
    if options.fix:
        fix = options.fix
    if options.log:
        log = options.log
    if options.par:
        parfile = options.par
    if options.l1a:
        l1a = options.l1a

    if file is None and parfile is None:
        parser.print_help()
        exit(0)

    m = modisL1A.modis_l1a(file=file,
                           parfile=parfile,
                           l1a=l1a,
                           nextgranule=nextgranule,
                           startnudge=float(startnudge),
                           stopnudge=float(stopnudge),
                           satellite=mission,
                           fix=fix,
                           log=log,
                           verbose=verbose
    )

    env(m)
    modis_env(m)
    m.chk()
    m.l0()
    buildpcf(m)
    m.run()
