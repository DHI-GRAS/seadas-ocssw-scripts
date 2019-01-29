#! /usr/bin/env python
"""
update_luts.py

Updates LUTS for the various sensors.
"""

import argparse
import modules.LutUtils as Lut


class CustomFormatter(argparse.ArgumentDefaultsHelpFormatter,
                      argparse.RawTextHelpFormatter):
    pass


if __name__ == '__main__':

    # version = '2.0'
    description = 'Retrieve latest lookup tables for specified sensor.'
    sensors = ['seawifs', 'aquarius', 'modisa', 'modist', 'viirsn', 'viirsj1']
    platforms = ['aqua', 'terra', 'npp', 'j1']

    # Define commandline options

    parser = argparse.ArgumentParser(formatter_class=CustomFormatter,
                                     description=description, add_help=True)

    parser.add_argument('mission', metavar='MISSION',
                        help='sensor or platform to process; one of:\n%(choices)s',
                        choices=sensors + platforms)

    parser.add_argument('-e', '--eval', action='store_true', dest='evalluts',
                        help='also download evaluation LUTs')

    parser.add_argument('-v', '--verbose', action='store_true',
                        help='print status messages')

    parser.add_argument('-n', '--dry-run', action='store_true', dest='dry_run',
                        help='no action; preview files to be downloaded')

    parser.add_argument('--timeout', type=float, default=10,
                        help='network timeout in seconds')

    # parser.add_argument('--version', action='version',
    #                    version='%(prog)s ' + version)

    parser.add_argument('-d', '--debug', action='store_true',
                        help=argparse.SUPPRESS) # hidden option

    # Read options and take action
    args = parser.parse_args()
    if args.debug:
        import logging
        logging.basicConfig(level=logging.DEBUG,
                            format='%(levelname)s:%(message)s')

    luts = Lut.LutUtils(verbose=args.verbose,
                        mission=args.mission.lower(),
                        evalluts=args.evalluts,
                        timeout=args.timeout,
                        dry_run=args.dry_run)

    valid_sensors = ['Aquarius', 'SeaWiFS', 'MODIS', 'VIIRS']
    if (luts.sensor and luts.sensor['instrument'] in valid_sensors):
        luts.get_luts()
    else:
        parser.print_help()
        parser.exit(1)

    parser.exit(luts.status)
