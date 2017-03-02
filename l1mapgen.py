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

    if resvalue <= 300. :
        return 'HQ' # make HQ when using l2bin64
    elif resvalue < 1000.  :
        return '1'
    elif resvalue < 2500.  :
        return '2'
    elif resvalue < 5000.  :
        return '4'
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

def get_rhots(binfile):
    rhot = {'MODIS':'rhot_645,rhot_555,rhot_469',
            'SeaWiFS':'rhot_670,rhot_555,rhot_412',
            'OCTS':'rhot_670,rhot_565,rhot_412',
            'VIIRS':'rhot_671,rhot_551,rhot_486',
            'MERIS':'rhot_665,rhot_560,rhot_412',
            'OLCI':'rhot_665,rhot_560,rhot_412',
            'CZCS':'rhot_670,rhot_550,rhot_443',
            'OLI':'rhot_655,rhot_561,rhot_442',
            }
    cmd = ' '.join(['ncdump', '-h', binfile,'|','grep','instrument'])
    result = subprocess.Popen(cmd, shell=True,
                                   stdout=subprocess.PIPE).communicate()[0]
    sensor = ((((result.splitlines()[0]).strip()).rstrip(' ;').split('= "'))[1]).strip('"')
    return rhot[sensor]

def main():

    import argparse
    import sys, re
    from subprocess import check_call,check_output,CalledProcessError

    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,description='''\
      This program takes a product_rgb (rhos by default) from a L1 file (or list of files), bins them
      then maps the L2 binned file using a Plate Carree cylindrical projection,
      and produces a faux-color png file.

      The argument-list is a set of keyword=value pairs.
      The arguments can be specified on the commandline, or put into a parameter file,
      or the two methods can be used together, with commandline over-riding.''',add_help=True)
    parser.add_argument('parfile', nargs='?', type=str, help=' input parameter file ')
    parser.add_argument('-ifile', nargs=1, type=str, help=' input file (L1A/B file or file with list) ')
    parser.add_argument('-geofile', nargs='?', type=str,help=' input file geolocation file name ')
    parser.add_argument('-ofile', nargs=1, type=str, default=(["l3mapgen_output.png"]),help=' output file name ')
#    parser.add_argument('-product', nargs=1, type=str, default=(["chlor_a"]),help=" product [default=chlor_a]")
    parser.add_argument('-product_rgb', nargs=1, type=str, default=(["DEFAULT"]),help=" 3 products (e.g.,product_rgb=rhos_645,rhos_555,rhos_469) to use for RGB.  Default is sensor specific")
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
    parser.add_argument('-atmocor', action="store_true", help=('apply Rayleigh correction'))
    parser.add_argument('-palfile', nargs=1, type=str, default=(["DEFAULT"]),help=('palette filename. Default uses file for product in product.xml'))
    parser.add_argument('-fudge', nargs=1, type=float,default=([1.0]), help=('fudge factor used to modify size of L3 pixels'))
    parser.add_argument('-threshold', nargs=1, type=float,default=([0]), help=('minimum percentage of filled pixels before an image is generated'))


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

    default_opts=["product_rgb","palfile","north","south","east","west","central_meridian"]
    geo_opts = ["north","south","east","west"]
    l2bin_mapclo = {"ifile" : "infile", "resolution":"resolve"}
    script_opts=["atmocor","gibs","parfile","fullrange","geofile"]
    tmpfile_l2gen = "tmp.l2gen"
    tmpfile_l2bin = "tmp.l2bin"

    if not dict_args['quiet']:
        print(dict_args)

    nfiles = enumerate(dict_args['ifile'])
    geofiles = [dict_args['geofile']]
    print(geofiles)
    if 'ASCII' in MetaUtils.get_mime_data(dict_args['ifile'][0]):
        print("here")
        lstfile = open(dict_args['ifile'][0],'r')
        nfiles = enumerate(lstfile.readlines())
        lstfile.close()
        if geofiles[0]:
            gfiles = open(dict_args['geofile'],'r')
            i = 0
            for gfile in gfiles.readlines():
                print(gfile)
                if i == 0:
                    geofiles[i] = gfile.strip()
                else:
                    geofiles.append(gfile.strip())
                i = i+1


    l2filelst = open(tmpfile_l2gen,'w')
    for i, l1file in nfiles:
        print(i,l1file)
        # Build the l2gen command
        l1file = l1file.strip()
        clo = ["l2gen"]
        clo.append('ifile='+l1file)
        if dict_args['geofile']:
            clo.append("geofile="+geofiles[i])

        ofile = tmpfile_l2gen + '_'+str(i)
        clo.append("ofile"+"="+ofile)

        if dict_args['atmocor']:
            clo.append('l2prod=rhos_nnn')
        else:
            clo.append('l2prod=rhot_nnn')

        clo.append("atmocor=0")
        for co in geo_opts:
            for op in dict_args[co]:
                print(co,op)
                if op != "DEFAULT":
                    clo.append(co+"="+str(op))

        if not dict_args['quiet']:
            print(clo)

        try:
            check_call(clo)
        except CalledProcessError as e:
            print("Process error ({0}): message:{1}".format(str(e.returncode), e.output))
            sys.exit()

        l2filelst.write(ofile+'\n')
    l2filelst.close()
    # Build the l2bin command line
    clo = ["l2bin"]

    clo.append( 'flaguse=ATMFAIL,BOWTIEDEL' )
    clo.append( 'prodtype=regional' )
    clo.append('ifile='+tmpfile_l2gen)
    clo.append("ofile="+tmpfile_l2bin)
    for co in l2bin_mapclo:
        if co in default_opts and "DEFAULT" in dict_args[co]:
            continue
        if co in ['ifile','ofile']:
            continue
        if co in dict_args:
            for op in dict_args[co]:
                if co == 'resolution':
                    val = getBinRes(op)
                    clo.append('resolve'+"="+val)
                elif type(op) is not str :
                    clo.append(l2bin_mapclo[co]+"="+str(op))
                else:
                    clo.append(l2bin_mapclo[co]+"="+op)

    if not dict_args['quiet']:
        print(clo)

    try:
        check_call(clo)
    except CalledProcessError as e:
        print("Process error ({0}): message:{1}".format(str(e.returncode), e.output))
        sys.exit()

    # Build the l3mapgen command line
    geoExtent = getGeoExtent(tmpfile_l2bin)
    clo = ["l3mapgen"]
    clo.append('interp=area')
    clo.append('use_rgb=1')
    l3opt={}
    print(dict_args)
    for co in dict_args:
        # Skip values left as default
        if co in default_opts and "DEFAULT" in dict_args[co]:
            continue
        # ignore script options that are not l3mapgen options
        if any(option in co for option in script_opts):
            if co == 'atmocor' and not dict_args[co]:
                clo.append('product_rgb='+get_rhots(tmpfile_l2bin))
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
                clo.append(co + "=" + tmpfile_l2bin)
            elif co == 'projection':
                if op in 'platecarree':
                    proj4 = "+proj=eqc +lat_ts=0 +lat_0={} +lon_0={} +x_0=0 +y_0=0 +ellps=WGS84 +datum=WGS84 +units=m +no_defs".format(str(geoExtent['center_latitude']),str(geoExtent['center_longitude']))
                else:
                    proj4 = op

                clo.append(co + "=" + proj4)

            elif type(op) is not str :
                clo.append(co + "=" + str(op))
            else:
                clo.append(co + "=" + op)
    if not dict_args['quiet']:
        print(clo)
    try:
        check_call(clo)
    except CalledProcessError as e:
        print("Process error ({0}): message:{1}".format(str(e.returncode), e.output))
        sys.exit()

    for f in [tmpfile_l2bin,tmpfile_l2gen]:
        if f == tmpfile_l2gen:
            l2filelst = open(tmpfile_l2gen,'r')
            for l2f in l2filelst.readlines():
                l2f = l2f.strip()
                if not dict_args['quiet']:
                    print("removing: "+l2f)
                remove(l2f)
        if not dict_args['quiet']:
            print("removing: "+f)
        remove(f)

if __name__ == "__main__": main()
