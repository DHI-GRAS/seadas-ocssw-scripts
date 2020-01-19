#! /usr/bin/env python
import argparse
import sys
from modules.modis_utils import buildpcf, modis_env
import modules.modis_L1A_utils as modisL1A
from modules.setupenv import env

if __name__ == "__main__":

    version = "1.09"

    # Read commandline options...

    parser = argparse.ArgumentParser(prog="modis_L1A")
    parser.add_argument('--version', action='version', version='%(prog)s ' + version)
    parser.add_argument("filename", nargs='?',
                      help="Input L0 file", metavar="L0FILE")
    parser.add_argument("-p", "--parfile",
                      help="Parameter file containing program inputs", metavar="PARFILE")
    parser.add_argument("-o", "--output",
                      help="Output L1A filename - defaults to '(A|T)YYYYDDDHHMMSS.L1A_LAC'", metavar="L1AFILE")
    parser.add_argument("-m", "--mission",
                      help="MODIS mission - A(qua) or T(erra)", metavar="MISSION")
    parser.add_argument("-s", "--startnudge", type=float,
                      default=0, help="Level-0 start-time offset (seconds)", metavar="STARTNUDGE")
    parser.add_argument("-e", "--stopnudge", type=float,
                      default=0, help="Level-0 stop-time offset (seconds)", metavar="STOPNUDGE")
    parser.add_argument("-n", "--nextgranule",
                      help="Next L0 granule (for geolocation of last scan; sets stopnudge=0)",
                      metavar="NEXT")
    parser.add_argument("-v", "--verbose", action="store_true",
                      default=False, help="print status messages")
    parser.add_argument("--log", action="store_true",
                      default=False, help="Save processing log file(s)")
    parser.add_argument("-d", "--disableL0fix", action="store_false",
                      default=True, help="Disable use of l0fix_modis utility for corrupt packets")
    parser.add_argument("-t", "--disablerounding", action="store_false",
                      default=True, help="Disable rounding of granule end time to 5-min boundary")

    args = parser.parse_args()

    if args.parfile is None and args.filename is None:
        parser.print_help()
        sys.exit(1)

    m = modisL1A.modis_l1a(file=args.filename,
                           parfile=args.parfile,
                           l1a=args.output,
                           nextgranule=args.nextgranule,
                           startnudge=args.startnudge,
                           stopnudge=args.stopnudge,
                           satellite=args.mission,
                           fix=args.disableL0fix,
                           rounding=args.disablerounding,
                           log=args.log,
                           verbose=args.verbose
    )

    env(m)
    modis_env(m)
    m.chk()
    m.l0()
    buildpcf(m)
    m.run()
    sys.exit(0)
