#!/usr/bin/env python
import modules.MetaUtils as MetaUtils
from modules.ParamUtils import ParamProcessing
import subprocess
from os import remove

def getBinRes(resolution):
    resvalue = 2000

    if "km" in resolution:
        resvalue = float(resolution.strip('km')) * 1000.
    elif "m" in resolution:
        resvalue = float(resolution.strip('m'))
    elif "deg" in resolution:
        resvalue = float(resolution.strip('deg')) * 111312.

    # NOTE: values below are set higher than desired as l3mapgen currently
    #       does not support interp=area and fudge parameters for non-SMI
    #       projections.  Revisit once l3mapgen has been so modified.
    if resvalue <= 300. :
        return 'HQ' # make HQ when using l2bin64
    elif resvalue < 1000.  :
        return '2'
    elif resvalue < 2500.  :
        return '4'
    elif resvalue < 5000.  :
        return '9'
    else:
        return '9'

def getGeoExtent(ifile):
    geoExtent = {'northernmost_latitude':-90.0,
        'southernmost_latitude':90.0,
        'westernmost_longitude':180.0,
        'easternmost_longitude':-180.0,
        'center_latitude':0.}
    if 'text' in MetaUtils.get_mime_data(ifile):
        with open(ifile) as input_files:
            for inputfile in input_files:
                inputfile = inputfile.strip()
                print(inputfile)
                fileGeo = getFileExtent(inputfile)
                for key in geoExtent:
                    if key == 'northernmost_latitude':
                        if (fileGeo[key] > geoExtent[key]):
                            geoExtent[key] = fileGeo[key]
                    if key == 'easternmost_longitude':
                        geoExtent[key] = easternmost(geoExtent['easternmost_longitude'], fileGeo['easternmost_longitude'])
                    if key == 'southernmost_latitude':
                        print(fileGeo[key], geoExtent[key])
                        if (fileGeo[key] < geoExtent[key]):
                            geoExtent[key] = fileGeo[key]
                    if key == 'westernmost_longitude':
                        geoExtent[key] = westernmost(geoExtent['westernmost_longitude'], fileGeo['westernmost_longitude'])
    else:
        geoExtent = getFileExtent(ifile)

    geoExtent['center_latitude'] = (geoExtent['northernmost_latitude'] + geoExtent['southernmost_latitude']) / 2.0
    if abs(geoExtent['easternmost_longitude'] - geoExtent['westernmost_longitude']) > 180:
        geoExtent['center_longitude'] = 180.0 + (geoExtent['easternmost_longitude'] + geoExtent['westernmost_longitude']) / 2.0
    else:
        geoExtent['center_longitude'] = (geoExtent['easternmost_longitude'] + geoExtent['westernmost_longitude']) / 2.0
    return geoExtent


def getFileExtent(ifile):
    cmd = ' '.join(['ncdump', '-h', ifile,'|','grep','most'])
    nswe = subprocess.Popen(cmd, shell=True,
                                   stdout=subprocess.PIPE).communicate()[0]
    fileExtent = {}
    for line in nswe.splitlines():
        (key,value) = line.strip().rstrip('f ;').lstrip(':').split(' = ')
        fileExtent[key] = float(value)

    return fileExtent

def westernmost( lon1, lon2 ):
    if (lon1 == 180.):
         lon1 = lon2
    if ( abs(lon1 - lon2) < 190.0 ):
        return ( min(lon1,lon2) )
    else:
        return ( max(lon1,lon2) )

def easternmost( lon1, lon2 ):
    if (lon1 == -180.):
         lon1 = lon2
    if ( abs(lon1 - lon2) < 190.0 ):
        return ( max(lon1,lon2) )
    else:
        return ( min(lon1,lon2) )


def main():

    import argparse
    import sys
    from subprocess import call

    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,description='''\
      This program takes a product from a L2 file, maps it using a Plate Carree cylindrical projection,
      and produces a gray scale PGM or color PPM file.

      The argument-list is a set of keyword=value pairs.
      The arguments can be specified on the commandline, or put into a parameter file,
      or the two methods can be used together, with commandline over-riding.''',add_help=True)
    parser.add_argument('parfile', nargs='?', type=str, help=' input file (L2 file or file with list) ')
    parser.add_argument('-ifile', nargs=1, type=str, help=' input file (L2 file or file with list) ')
    parser.add_argument('-ofile', nargs=1, type=str, default=(["l3mapgen_output.png"]),help=' output file name ')
    parser.add_argument('-product', nargs=1, type=str, default=(["chlor_a"]),help=" product [default=chlor_a]")
    parser.add_argument('-resolution', nargs=1, type=str, default=(['2.0km']), help='''\

    resolution
    -----------------
         #.#:  width of a pixel in meters
       #.#km:  width of a pixel in kilometers
               integer value (e.g. 9km) will result in SMI nominal dimensions
               (9km == 9.2km pixels, 4km == 4.6km pixels, etc.)
      #.#deg:  width of a pixel in degrees
    ''')
    parser.add_argument('-oformat', nargs=1, choices=['netcdf4','hdf4','png','ppm','tiff'],type=str, default=(["png"]), help=('''\
     output file format
     --------------------------------------------------------
     netcdf4: netCDF4 file, can contain more than one product
     hdf4:    HDF4 file (old SMI format)
     png:     PNG image file
     ppm:     PPM image file
     tiff:    TIFF file with georeference tags
     '''))

    parser.add_argument('-north', nargs=1, type=float,default=(["DEFAULT"]), help=('Northern most Latitude (-999=file north)'))
    parser.add_argument('-south', nargs=1, type=float,default=(["DEFAULT"]), help=('Southern most Latitude (-999=file south)'))
    parser.add_argument('-east', nargs=1, type=float,default=(["DEFAULT"]), help=('Eastern most Latitude (-999=file east)'))
    parser.add_argument('-west', nargs=1, type=float,default=(["DEFAULT"]), help=('Western most Latitude (-999=file west)'))
    parser.add_argument('-fullrange', action="store_true", help=('set geographic extent to the maximum range of the files input'))
    #parser.add_argument('-projection', nargs=1, choices=['smi','platecarree','mollweide','lambert','albersconic','mercator','ease2'],type=str,default=(['platecarree']),  help='''\
    parser.add_argument('-projection', nargs=1, type=str,default=(['platecarree']),  help='''\
        enter a proj.4 projection string or choose one of the following
        predefined projections:
        --------------------------------------------------------------
        smi:       Standard Mapped image, cylindrical projection, uses
                   central_meridian.  n,s,e,w default to whole globe.
                   projection="+proj=eqc +lat_0=<central_meridian>"
        platecarree: Plate Carree image, cylindrical projection, uses
                   central_meridian
                   projection="+proj=eqc +lat_0=<central_meridian>"
        mollweide: Mollweide projection
                   projection="+proj=moll +lat_0=<central_meridian>"
        lambert:   Lambert conformal conic projection
                   projection="+proj=lcc +lat_0=<central_meridian>"
        albersconic: Albers equal-area conic projection
                   projection="+proj=aea +lat_0=<central_meridian>"
        mercator:  Mercator cylindrical map projection
                   projection="+proj=merc +lat_0=<central_meridian>"
        ease2:     Ease Grid 2 projection
                   projection="+proj=cea +lon_0=0 +lat_ts=30 +ellps=WGS84
                         +datum=WGS84 +units=m +lat_0=<central_meridian>"
        conus:     USA Contiguous Albers Equal Area-Conic projection, USGS"
                   projection="+proj=aea +lat_1=29.5 +lat_2=45.5
                         +lat_0=23.0 +lon_0=-96 +x_0=0 +y_0=0
                         +ellps=GRS80 +datum=NAD83 +units=m +no_defs"
    ''')
    parser.add_argument('-central_meridian', nargs=1, type=float,default=(["DEFAULT"]), help=('central meridian for projection in deg east.  Only used for smi, mollweide and raw projection'))
    parser.add_argument('-quiet', action="store_true", help=('stop the status printing'))
    parser.add_argument('-gibs', action="store_true", help=('set projection based on scene center latitude to support GIBS'))
    parser.add_argument('-apply_pal', action="store_true", help=('apply color A palette: true=color image, false=grayscale image'))
    parser.add_argument('-palfile', nargs=1, type=str, default=(["DEFAULT"]),help=('palette filename. Default uses file for product in product.xml'))
    parser.add_argument('-fudge', nargs=1, type=float,default=([1.0]), help=('fudge factor used to modify size of L3 pixels'))
    parser.add_argument('-threshold', nargs=1, type=float,default=([0]), help=('minimum percentage of filled pixels before an image is generated'))
    parser.add_argument('-datamin', nargs=1, type=float,default=(["DEFAULT"]), help=('minimum value for scaling (default from product.xml)'))
    parser.add_argument('-datamax', nargs=1, type=float,default=(["DEFAULT"]), help=('maximum value for scaling (default from product.xml)'))
    parser.add_argument('-scaletype', nargs=1, choices=['linear','log','arctan','DEFAULT'],type=float,default=(["DEFAULT"]), help='''\
        data scaling type (default from product.xml)
        ---------------------------------------------
        linear:  linear scaling
        log:     logarithmic scaling
        arctan:  arc tangent scaling

    ''')

    args=parser.parse_args()
    dict_args=vars(args)

    if args.parfile:
        param_proc = ParamProcessing(parfile=args.parfile)
        param_proc.parseParFile()
        for param in (param_proc.params['main'].keys()):
            value = param_proc.params['main'][param]
            if param == 'file':
                dict_args['ifile'] = [value]
            else:
                dict_args[param] = [value]

    if not dict_args['ifile'] or not dict_args['ofile']:
        parser.error("you must specify an input file and an output file")

    default_opts=["product","datamin", "datamax","scaletype","palfile","north","south","east","west","central_meridian"]
    l2bin_mapclo = {"ifile" : "infile", "product": "l3bprod", "resolution":"resolve"}
    script_opts=["gibs","parfile","fullrange"]
    tmpfile = "tmp.l3bin"

    if not dict_args['quiet']:
        print(dict_args)

    # Build the l2bin command line
    clo = ["l2bin"]
    clo.append( 'flaguse=ATMFAIL,CLDICE,BOWTIEDEL' )
    clo.append( 'prodtype=regional' )
    clo.append("ofile"+"="+tmpfile)
    l2opt={}
    for co in l2bin_mapclo:
        if co in default_opts and "DEFAULT" in dict_args[co]:
            continue

        if co in dict_args:
            for op in dict_args[co]:

                if co == 'resolution':
                    val = getBinRes(op)
                    clo.append('resolve'+"="+val)
                elif type(op) is not str :
                    clo.append(l2bin_mapclo[co]+"="+str(op))
                    l2opt[co] = str(op)
                else:
                    clo.append(l2bin_mapclo[co]+"="+op)
                    l2opt[co] = op

    if not dict_args['quiet']:
        print(clo)

    call(clo)

    # Build the l3mapgen command line
    geoExtent = getGeoExtent(dict_args['ifile'][0])
    clo = ["l3mapgen"]
    clo.append('interp=area')
    for co in dict_args:
        # Skip values left as default
        if co in default_opts and "DEFAULT" in dict_args[co]:
            continue
        # ignore script options that are not l3mapgen options
        if any(option in co for option in script_opts):
            continue
        # handle boolean options
        if type(dict_args[co]) is bool and dict_args[co]:
            clo.append(co + "=1" )
            continue
        elif type(dict_args[co]) is bool and not dict_args[co]:
            clo.append(co + "=0" )
            continue
        # handle non-boolean options
        for op in dict_args[co]:
            if co == 'ifile':
                if dict_args['fullrange']:
                    clo.append('north'+"="+str(geoExtent['northernmost_latitude']))
                    clo.append('south'+"="+str(geoExtent['southernmost_latitude']))
                    clo.append('west'+"="+str(geoExtent['westernmost_longitude']))
                    clo.append('east'+"="+str(geoExtent['easternmost_longitude']))
                clo.append(co + "=" + tmpfile)
            elif co == 'projection':
                if op in 'platecarree':
                    proj4 = "+proj=eqc +lat_ts=0 +lat_0={} +lon_0={} +x_0=0 +y_0=0 +ellps=WGS84 +datum=WGS84 +units=m +no_defs".format(str(geoExtent['center_latitude']),str(geoExtent['center_longitude']))
                else:
                    proj4 = op
                if dict_args['gibs']:
                    print(geoExtent['center_latitude'])
                    if (geoExtent['center_latitude'] < -60):
                        proj4 = "+proj=stere +lat_0=-90 +lat_ts=-71 +lon_0={} +k=1 +x_0=0 +y_0=0 +ellps=WGS84 +datum=WGS84 +units=m +no_defs".format(str(geoExtent['center_longitude']))
                    elif (geoExtent['center_latitude'] > 60):
                        proj4 = "+proj=stere +lat_0=90 +lat_ts=70 +lon_0={} +k=1 +x_0=0 +y_0=0 +ellps=WGS84 +datum=WGS84 +units=m +no_defs".format(str(geoExtent['center_longitude']))

                clo.append(co + "=" + proj4)

            elif type(op) is not str :
                clo.append(co + "=" + str(op))
            else:
                clo.append(co + "=" + op)

    if not dict_args['quiet']:
        print(clo)

    call(clo)
    remove(tmpfile)

if __name__ == "__main__": main()
