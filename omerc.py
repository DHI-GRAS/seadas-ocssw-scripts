#!/usr/bin/env python3
import argparse
from math import cos, sin, atan2, radians, degrees
import netCDF4 as nc
import os

def main():

    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter, description='''\
    This program returns the projection definition information for an 
    Oblique Mercator projection for the given input L2 file.  The default 
    output is a set of keyword=value pairs for input to l3mapgen.''', add_help=True)
    parser.add_argument('ifile', nargs=1, type=str, help=' input file')
    parser.add_argument('--oformat', nargs=1, choices=['l3mapgen','proj4','gmt'],type=str, 
        default=['l3mapgen'],help='return l3mapgen, proj4 or gmt projection parameters')

    args = parser.parse_args()
    if not args.ifile:
        parser.error("You must specify a Level 2 input file")

    phi_c = None  # proj4 +lat_1 (single standard parallel)
    phi_0 = None  # proj4 +lat_0 (central latitude of origin)
    lambda_0 = None  # proj4 +lonc (central meridian)
    lambda_1 = None

    # Grab the necessary geolocation bits from the L2 file...
    if os.path.exists(args.ifile[0]):
        with nc.Dataset(args.ifile[0]) as dataset:
            nlines = len(dataset.dimensions['number_of_lines'])
            scan = dataset.groups['scan_line_attributes'].variables
            mid = nlines / 2

            # Scene center coordinates
            clon = scan['clon'][mid]
            clat = scan['clat'][mid]

            # Starting (i.e. first scan line) mid-scan coordinates
            slon = scan['clon'][0]
            slat = scan['clat'][0]

            # Ending (i.e. last scan line) mid-scan coordinates
            elon = scan['clon'][-1]
            elat = scan['clat'][-1]

            # Use the above coordinates to define a projection.
            phi_0 = radians(slat)
            phi_c = radians(clat)
            lambda_1 = radians(slon)
            lambda_0 = radians(clon)

            y = sin(lambda_1 - lambda_0) * cos(phi_c)
            x = cos(phi_0) * sin(phi_c) - sin(phi_0)*cos(phi_c)*cos(lambda_1 - lambda_0)
            alpha = degrees(atan2(y,x))

            # might need to adjust gamma when azimuth points south?
            if args.oformat[0] == 'gmt':
                    prj = "gmt mapproject -Job{:f}/{:f}/{:f}/{:f}/1:1 -C -F -R-1/1/-1/1".format(clon,clat,slon,slat)
                    print("GMT def:")
                    print(prj)
            elif args.oformat[0] == 'proj4':
                    print("proj4 def:")
                    print("+proj=omerc +lat_0=%.9f +lonc=%.9f +alpha=%.9f +gamma=0" %
                         (degrees(phi_c), degrees(lambda_0), alpha-90))
            else:
                print("lat_0=%.6f" % degrees(phi_c))
                print("central_meridian=%.6f" % degrees(lambda_0))
                print("azimuth=%.6f" % (alpha-90.))

    else:
        err_msg = 'Could not find {0} to open'.format(ifile)
        sys.exit(err_msg)


if __name__ == "__main__": main()
