#!/usr/bin/env python3

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
    parser.add_argument('ifile', nargs=1, type=str, help=' input file (L2 file or file with list) ')
    parser.add_argument('-ofile', nargs=1, type=str, default=(["l3mapgen_output.png"]),help=' output file name ')
    parser.add_argument('-ofile2', nargs=1, type=str, default=(["DEFAULT"]),help=' output file name ')
    parser.add_argument('-product', nargs=1, type=str, default=(["DEFAULT"]),help=" bin products [default=all products]")
    parser.add_argument('-pversion', nargs=1, type=str, default=(["DEFAULT"]),help=" processing version string")
    parser.add_argument('-product_rgb', nargs=1, type=str, default=(["DEFAULT"]),help=" 3 products to use for RGB.  Default is sensor specific")
    parser.add_argument('-prodtype', nargs=1, choices=['regional'],default=(['regional']), help=' product type (Set to "day" to bin day scans.)')
    parser.add_argument('-flaguse', nargs=1, type=str, default=(["'LAND,CLDICE,HILT,HIGLINT'"]), help=' flags masked [see /SENSOR/l2bin_defaults.par')
    parser.add_argument('-bin_res', nargs=1, type=str, choices=['H', '1', '2', '4', '9','18','QD','36','HD','1D'],default=(['2']), help='''\
    
    bin resolution 
    -----------------
    H = 0.5km 
    1 = 1.1km 
    2 = 2.3km 
    4 = 4.6km
    9 = 9.2km
    18 = 18.5km
    QD = 0.25 degree
    36 = 36km
    HD = 0.5 degree
    1D = 1 degree
    ''')
    parser.add_argument('-map_res', nargs=1, type=str, choices=['H', '1', '2', '4', '9','18','QD','36','HD','1D'],default=(['2']), help='''\
    
    map resolution 
    -----------------
    H = 0.5km 
    1 = 1.1km 
    2 = 2.3km 
    4 = 4.6km
    9 = 9.2km
    18 = 18.5km
    QD = 0.25 degree
    36 = 36km
    HD = 0.5 degree
    1D = 1 degree
    ''')
    parser.add_argument('-oformat', nargs=1, choices=['netcdf','hdf4','png','ppm','tiff'],type=str, default=(["png"]), help=('''\
     output file format
     --------------------------------------------------------
     netcdf4: netCDF4 file, can contain more than one product
     hdf4:    HDF4 file (old SMI format)
     png:     PNG image file
     ppm:     PPM image file 
     tiff:    TIFF file with georeference tags
     '''))
    parser.add_argument('-oformat2', nargs=1, choices=['netcdf','hdf4','png','ppm','tiff'],type=str, default=(["png"]), help=('''\
     second output file format
     --------------------------------------------------------
     netcdf4: netCDF4 file, can contain more than one product
     hdf4:    HDF4 file (old SMI format)
     png:     PNG image file
     ppm:     PPM image file 
     tiff:    TIFF file with georeference tags
     '''))
    parser.add_argument('-interp', nargs=1, type=str, choices=['nearest','bin','area'],default=(['area']), help='''\
    interpolation method:
    -----------------------------
        nearest: Nearest Neighbor
        bin:     bin all of the pixels that intersect the area of the
                  output pixel
        area:    bin weighted by area all of the pixels that intersect
                  the area of the output pixel
    ''')
    parser.add_argument('-north', nargs=1, type=float,default=([-999]), help=('Northern most Latitude (-999=file north)'))
    parser.add_argument('-south', nargs=1, type=float,default=([-999]), help=('Southern most Latitude (-999=file south)'))
    parser.add_argument('-east', nargs=1, type=float,default=([-999]), help=('Eastern most Latitude (-999=file east)'))
    parser.add_argument('-west', nargs=1, type=float,default=([-999]), help=('Western most Latitude (-999=file west)'))
    parser.add_argument('-central_meridian', nargs=1, type=float,default=([-999]), help=('central meridian for projection in deg east.  Only used for smi, mollweide and raw projection'))
    parser.add_argument('-projection', nargs=1, choices=['smi','platecarree','mollweide','lambert','albersconic','mercator','ease2','raw'],type=str,default=(['platecarree']),  help='''\
        choose one of the following predefined projections:
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
        raw:       raw dump of the bin file
    ''')
    parser.add_argument('-quiet', nargs=1, type=int,choices=[0,1],default=([0]), help=('stop the status printing'))
    parser.add_argument('-apply_pal', nargs=1, type=bool,default=([1]), help=('apply color A palette: true=color image, false=grayscale image'))
    parser.add_argument('-use_quality', nargs=1, type=int,choices=[0,1],default=([0]), help=('should we do quality factor processing'))
    parser.add_argument('-use_rgb', nargs=1, type=int,choices=[0,1],default=([0]), help=('should we use product_rgb to make a psudo-true color image'))
    parser.add_argument('-palfile', nargs=1, type=str, default=(["DEFAULT"]),help=('palette filename. Default uses file for product in product.xml'))
    parser.add_argument('-deflate', nargs=1, type=int, default=([4]),help=('deflation level'))
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
         
    #args=parser.parse_args('/home/rhealy/ocsswn/test/l2gen/aqua/A2008080220000.L2_LAC_OC.subpix_500m.nc -ofile blah.png -projection mercator -product chlor_a -resolution 2 -flaguse LAND,CLDICE,HILT,HIGLINT'.split())
    args=parser.parse_args()
    if not args.ifile or not args.ofile:
        parser.error("you must specify an input file and an output file")
    default_opts=["product","datamin", "datamax","scaletype","palfile"]
    l2bin_mapclo = {"ifile" : "infile", "ofile": "ofile", "product": "l3bprod", "prodtype": "prodtype", "bin_res":"resolve", "flaguse":"flaguse"}
    resbin2map_arg = {"H":"hkm","1":"1km", "2":"2km","4":"4km","9":"9km", "18":"18km","QD":"0.25deg","36":"36km","HD":"0.5deg","1D":"1.0deg"}
    tmpfile = "tmp.l3bin"

#     for clo in l2bin_mapclo:
#         print(l2bin_mapclo[clo])     
#    args=parser.parse_args()
    print ("usequality="+str(args.use_quality))
    dict_args=vars(args)
    print(dict_args)
    
    # Build the l2bin command line
    clo = ["l2bin"]
    l2opt={}
    for co in l2bin_mapclo:
        if co in default_opts and "DEFAULT" in dict_args[co]:
            continue

        if co in dict_args:
            for op in dict_args[co]:
                if type(op) is not str :
                    clo.append(l2bin_mapclo[co]+"="+str(op))
                    l2opt[co] = str(op)     
                else:
                    clo.append(l2bin_mapclo[co]+"="+op)     
                    l2opt[co] = op     
    print('---')
    print(clo)
#    call(["l2bin",'infile={}'.format(ifile),"ofile=tmp.l3b",'l3bprod={}'.format(l3bprod),'prodtype={}'.format(prodtype),'resolve={}'.format(reslv),'flaguse={}'.format(flaguse)])
    call(clo)
    call(["mv", l2opt['ofile'],tmpfile])

    clo = ["l3mapgen"]
    l3opt={}
    print(dict_args)
    for co in dict_args:
        print(co)
        
        if co in default_opts and "DEFAULT" in dict_args[co]:
            continue

        for op in dict_args[co]:
            if type(op) is not str :
                clo.append(co + "=" + str(op))
                l3opt[co] = str(op)     
            else:
                if co == "map_res":
                    clo.append("resolution" + "=" + resbin2map_arg[op])     
                elif co == "ifile":
                    clo.append(co + "=" + tmpfile)                
                else:
                    clo.append(co + "=" + op)
                if co == "ofile":
                    ofile = op
                l3opt[co] = op     
    print('---')
    print(clo)
    call(clo)
    #call(["ls", "-l"])
    #call(["display",ofile])
if __name__ == "__main__": main()
    
