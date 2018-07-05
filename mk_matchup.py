#!/usr/bin/env python3
# coding: utf-8

"""
A Perl script to create and output satellite matchups from a SeaBASS file given an 
OB.DAAC L2 (SST, SST4, IOP, or OC) satellite file and a valid SeaBASS file containing
lat, lon, date, and time as /field entries or fixed --slat and --slon coords or a fixed
box bounded by --slat, --slon, --elat, and --elon. NOTE: --slat and --slon will override
lat/lons in --seabass_file.
written by J.Scott on 2016/12/13 (joel.scott@nasa.gov)
"""

def main():

    import argparse
    import os
    import re
    import subprocess
    from datetime import datetime, timedelta
    from statistics import median
    from copy import copy
    from math import isnan
    from collections import OrderedDict
    from SB_support_v35 import readSB

    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,description='''\
      This program create and output satellite matchups from a given SeaBASS file.

      REQUIRED inputs:
          1) --sat_file=        an OB.DAAC L2 (SST, SST4, IOP, or OC) satellite file
          2) --seabass_file=    a valid SeaBASS file with latitude, longitude, and date-time information as field entries.

      Notes on OPTIONAL inputs:
          1) --slat= --slon=    must be used together and will override any lat/lons in --seabass_file
          2) --elat= --elon=    must be used together and with --slon= and --slat=
                                will override any lat/lons in --seabass_file
                                uses a lat/lon bounding box instead of --box_size=

      Outputs:
          1) the original SeaBASS data
          AND
          2) collocated satellite products as additional columns into --out_file 
             OR if --out_file is not specified, matched-up data will be appended to --seabass_file

      Example usage call:
         mk_matchup.py --sat_file=[file name].nc --seabass_file=[file name].sb --out_file=[OPTIONAL, file name].sb
         mk_matchup.py --sat_file=[file name].nc --seabass_file=[file name].sb --slat=45.3 --slon=-157.4
         mk_matchup.py --sat_file=[file name].nc --seabass_file=[file name].sb --slat=45.3 --elat=48.7 --slon=-157.4 --elon=-145.3

      Caveats:
        * This script is designed to work with files that have been properly
          formatted according to SeaBASS guidelines (i.e. Files that passed FCHECK).
          Some error checking is performed, but improperly formatted input files
          could cause this script to error or behave unexpectedly. Files
          downloaded from the SeaBASS database should already be properly formatted, 
          however, please email seabass@seabass.gsfc.nasa.gov and/or the contact listed
          in the metadata header if you identify problems with specific files.

        * It is always HIGHLY recommended that you check for and read any metadata
          header comments and/or documentation accompanying data files. Information 
          from those sources could impact your analysis.

        * Compatibility: This script was developed for Python 3.5.

      License:
        /*=====================================================================*/
                         NASA Goddard Space Flight Center (GSFC) 
                 Software distribution policy for Public Domain Software

         The fd_matchup.py code is in the public domain, available without fee for 
         educational, research, non-commercial and commercial purposes. Users may 
         distribute this code to third parties provided that this statement appears
         on all copies and that no charge is made for such copies.

         NASA GSFC MAKES NO REPRESENTATION ABOUT THE SUITABILITY OF THE SOFTWARE
         FOR ANY PURPOSE. IT IS PROVIDED "AS IS" WITHOUT EXPRESS OR IMPLIED
         WARRANTY. NEITHER NASA GSFC NOR THE U.S. GOVERNMENT SHALL BE LIABLE FOR
         ANY DAMAGE SUFFERED BY THE USER OF THIS SOFTWARE.
        /*=====================================================================*/
      ''',add_help=True)

    parser.add_argument('--sat_file', nargs=1, required=True, type=str, help='''\
      REQUIRED: input OB.DAAC Level-2 satellite netCDF file
      ''')

    parser.add_argument('--seabass_file', nargs=1, required=True, type=str, help='''\
      REQUIRED: input SeaBASS file
      Must be a valid SeaBASS file, passing FHCHECK with no errors.
      Matched-up satellite variables will be appended as additional fields to the data matrix and relevant headers.
      File must contain latitude and longitude and date-time expressed as FIELD entries.
      To save output to a another file, other than --seabass_file, use the --out_file argument.
      ''')

    parser.add_argument('--out_file', nargs=1, type=str, help='''\
      OPTIONAL: output SeaBASS file name
      Use this flag to append the output to a separate file from the input --seabass_file
      Matched-up satellite variables will be appended as additional fields
      to the data matrix and relevant headers.
      ''')

    parser.add_argument('--box_size', nargs=1, default=([5]), type=int, help=('''\
      OPTIONAL: box size of the satellite data extract made around the in situ point
      Valid values are odd numbers between 3 and 11, default = 5
      '''))

    parser.add_argument('--min_valid_sat_pix', nargs=1, default=([50.0]), type=float, help=('''\
      OPTIONAL: percent minimum valid satellite pixels required to create an extract
      Valid value: (0.0 - 100.0), default = 50.0
      '''))

    parser.add_argument('--max_time_diff', nargs=1, default=([3.0]), type=float, help=('''\
      OPTIONAL: maximum time difference between satellite and in situ point
      Valid value: decimal number of hours (0 - 36 hours), default = 3
      '''))

    parser.add_argument('--max_coeff_variation', nargs=1, default=([0.15]), type=float, help=('''\
      OPTIONAL: maximum coefficient of variation of satellite pixels within the satellite extract
      Valid value: (0.0 - 1.0), default = 0.15
      '''))

    parser.add_argument('--slat', nargs=1, type=float, help=('''\
      OPTIONAL: Starting latitude, south-most boundary
      If used with --seabass_file, will override lats in the file
      Valid values: (-90,90N)
      '''))

    parser.add_argument('--elat', nargs=1, type=float, help=('''\
      OPTIONAL: Ending latitude, north-most boundary
      If used with --seabass_file and --slat, will override lats in the file
      Valid values: (-90,90N)
      '''))

    parser.add_argument('--slon', nargs=1, type=float, help=('''\
      OPTIONAL: Starting longitude, west-most boundary
      If used with --seabass_file, will override lons in the file
      Valid values: (-180,180E)
      '''))

    parser.add_argument('--elon', nargs=1, type=float, help=('''\
      OPTIONAL: Ending longitude, east-most boundary
      If used with --seabass_file and --slon, will override lons in the file
      Valid values: (-180,180E)
      '''))

    parser.add_argument('--verbose', default=False, action='store_true', help=('''\
      OPTIONAL: Displays reason for failed matchup for each in situ target called.
      '''))

    parser.add_argument('--no_header_comment', default=False, action='store_true', help=('''\
      OPTIONAL: Flag to NOT append exclusion criteria to the OFILE header. Useful when running script repeatedly. 
      '''))

    # Exclusion criteria; defaults from:
    # S.W. Bailey and P.J. Werdell, "A multi-sensor approach for the on-orbit validation of ocean color satellite data products", Rem. Sens. Environ. 102, 12-23 (2006).
    # with one exception: The maximum allowed solar zenith angle used here is 70-deg vs the paper's recommended 75-deg.

    args=parser.parse_args()
    if not args.sat_file or not args.seabass_file:
        parser.error("please specify a --sat_file AND a --seabass_file")
    else:
        dict_args=vars(args)

    # input verification
    if not dict_args['sat_file'][0] or not re.search('\.nc', dict_args['sat_file'][0].lower()) or not re.search('l2', dict_args['sat_file'][0].lower()):
        parser.error("invalid --sat_file specified, must be a Level-2 (L2) OB.DAAC netCDF (nc) file")
    else:
        #set l2_flags to check for OC/IOP versus SST/SST4 product suites
        if re.search('SST', dict_args['sat_file'][0]):
            flag_arg = ' ignore_flags=LAND\ NAVFAIL\ NAVWARN' + \
                       ' count_flags=LAND\ NAVFAIL'
        else:
            flag_arg = ' ignore_flags=LAND\ HIGLINT\ HILT\ HISATZEN\ HISOLZEN\ STRAYLIGHT\ CLDICE\ ATMFAIL\ LOWLW\ FILTER\ NAVFAIL\ NAVWARN' + \
                       ' count_flags=LAND\ NAVFAIL'

    if ((dict_args["box_size"][0] % 2) == 0) or (dict_args["box_size"][0] > 11) or (dict_args["box_size"][0] < 3):
        parser.error("invalid --box_size specified, must be an ODD integer between 3 and 11")

    if (dict_args["min_valid_sat_pix"][0] > 100.0) or (dict_args["min_valid_sat_pix"][0] < 0.0):
        parser.error("invalid --min_valid_sat_pix specified, must be a percentage expressed as a floating point number between 0.0 and 100.0")

    if (dict_args["max_time_diff"][0] > 36) or (dict_args["max_time_diff"][0] < 0):
        parser.error("invalid --max_time_diff specified, must be a decimal number between 0 and 36")
    else:
        twin_Hmin = -1 * int(dict_args['max_time_diff'][0])
        twin_Mmin = -60 * (dict_args['max_time_diff'][0] - int(dict_args['max_time_diff'][0]))
        twin_Hmax = 1 * int(dict_args['max_time_diff'][0])
        twin_Mmax = 60 * (dict_args['max_time_diff'][0] - int(dict_args['max_time_diff'][0]))

    if (dict_args["max_coeff_variation"][0] > 1.0) or (dict_args["max_coeff_variation"][0] < 0.0):
        parser.error("invalid --max_coeff_variation specified, must be an floating point number between 0.0 and 1.0")

    # read and verify SeaBASS file and required fields
    if os.path.isfile(dict_args['seabass_file'][0]):
        ds = readSB(filename=dict_args['seabass_file'][0], 
                    mask_missing=False, 
                    mask_above_detection_limit=False, 
                    mask_below_detection_limit=False, 
                    no_warn=True)
    else:
        parser.error('ERROR: invalid --seabass_file specified; does ' + dict_args['seabass_file'][0] + ' exist?')

    ds.datetime = ds.fd_datetime()
    if not ds.datetime:
        parser.error('missing fields in SeaBASS file -- file must contain a valid FIELDS combination of date/year/month/day/sdy and time/hour/minute/second')


    print('Looking for satellite/in situ match-ups for',dict_args['seabass_file'][0],'in',dict_args['sat_file'][0])
    write_flag = 0

    ds.out_ls = []
    for i in range(0,len(ds.datetime)):
        ds.out_ls.append(str(ds.missing))

    # loop through input SeaBASS file data rows
    for dt,row in zip(ds.datetime,range(0,len(ds.datetime))):

        # create time range of satellite obs to extract
        tim_min = dt + timedelta(hours=twin_Hmin,minutes=twin_Mmin)
        tim_max = dt + timedelta(hours=twin_Hmax,minutes=twin_Mmax)

        #handle slat/slon/elat/elon from command line
        if args.slat and args.slon and args.elat and args.elon:
            #check lat/lon inputs
            if abs(dict_args['slon'][0]) > 180.0 or abs(dict_args['elon'][0]) > 180.0:
                parser.error('invalid longitude inputs: --slon and --elon MUST be between -180/180E deg. Received --slon = ' + \
                            str(dict_args['slon'][0]) + ' and --elon = ' + str(dict_args['elon'][0]))
            if abs(dict_args['slat'][0]) > 90.0 or abs(dict_args['elat'][0]) > 90.0:
                parser.error('invalid latitude inputs: --slat and --elat MUST be between -90/90N deg. Received --slat = ' + \
                            str(dict_args['slat'][0]) + ' and --elat = ' + str(dict_args['elat'][0]))
            if dict_args['slat'][0] > dict_args['elat'][0]:
                parser.error('invalid latitude inputs: --slat MUST be less than --elat and both MUST be between -90/90N deg. Received --slat = ' + \
                            str(dict_args['slat'][0]) + ' and --elat = ' + str(dict_args['elat'][0]))
            if dict_args['slon'][0] > dict_args['elon'][0]:
                parser.error('invalid longitude inputs: --slon MUST be less than --elon and both MUST be between -180/180E deg. Received --slon = ' + \
                            str(dict_args['slon'][0]) + ' and --elon = ' + str(dict_args['elon'][0]))

            # construct sys call to val_extract
            sys_call_str = 'val_extract' + \
                           ' ifile=' + dict_args['sat_file'][0] + \
                           ' slon=' + str(dict_args['slon'][0]) + \
                           ' slat=' + str(dict_args['slat'][0]) + \
                           ' elon=' + str(dict_args['elon'][0]) + \
                           ' elat=' + str(dict_args['elat'][0]) + \
                           ' global_att=1' + \
                           ' variable_att=1' + flag_arg
            # variable_att flag needed to extract units
            # global_att flag needed to extract sensor/instrument names
            # sunzen=70.0  <---- HISOLZEN threshold
            # satzen=60.0  <---- HISATZEN threshold

            pid = subprocess.run(sys_call_str, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if pid.returncode == 99:
                if dict_args['verbose']:
                    print('No matchup: in situ target not in granule')
                continue #no valid matchup
            elif pid.returncode == 101 or pid.returncode == 102:
                parser.error('val_extract failed -- only accepts Level-2 (L2) satellite files. ' + \
                                dict_args['sat_file'][0] + ' is not a valid L2 file')
            elif pid.returncode != 0:
                parser.error('val_extract failed -- verify that the val_extract binary is compiled and on your PATH and that ' + \
                                dict_args['sat_file'][0] + ' exists')

        #handle slat/slon only from command line
        elif args.slat and args.slon and not args.elat and not args.elon:
            #check lat/lon inputs
            if abs(dict_args['slon'][0]) > 180.0:
                parser.error('invalid longitude inputs: --slon MUST be between -180/180E deg. Received --slon = ' + str(dict_args['slon'][0]))
            if abs(dict_args['slat'][0]) > 90.0:
                parser.error('invalid latitude inputs: --slat MUST be between -90/90N deg. Received --slat = ' + str(dict_args['slat'][0]))

            # construct sys call to val_extract
            sys_call_str = 'val_extract' + \
                           ' ifile=' + dict_args['sat_file'][0] + \
                           ' slon=' + str(dict_args['slon'][0]) + \
                           ' slat=' + str(dict_args['slat'][0]) + \
                           ' global_att=1' + \
                           ' variable_att=1' + \
                           ' boxsize=' + str(dict_args['box_size'][0]) + flag_arg
            # variable_att flag needed to extract units
            # global_att flag needed to extract sensor/instrument names
            # sunzen=70.0  <---- HISOLZEN threshold
            # satzen=60.0  <---- HISATZEN threshold

            pid = subprocess.run(sys_call_str, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if pid.returncode == 99:
                if dict_args['verbose']:
                    print('No matchup: in situ target not in granule')
                continue #no valid matchup
            elif pid.returncode == 101 or pid.returncode == 102:
                parser.error('val_extract failed -- only accepts Level-2 (L2) satellite files. ' + \
                                dict_args['sat_file'][0] + ' is not a valid L2 file')
            elif pid.returncode != 0:
                parser.error('val_extract failed -- verify that the val_extract binary is compiled and on your PATH and that ' + \
                                dict_args['sat_file'][0] + ' exists')

        #handle lat/lon from file
        else:

            # verify lat/lon inputs from file
            try:
                ds.lon = [float(i) for i in ds.data['lon']]
                ds.lat = [float(i) for i in ds.data['lat']]
            except:
                parser.error('Missing fields in SeaBASS file. File must contain lat and lon as fields, or specify --slat and --slon.')

            if isnan(ds.lat[row]) or isnan(ds.lon[row]):
                continue

            if abs(ds.lon[row]) > 180.0:
                parser.error('invalid longitude input: all longitude values in ' + dict_args['seabass_file'][0] + ' MUST be between -180/180E deg.')
            if abs(ds.lat[row]) > 90.0:
                parser.error('invalid latitude input: all latitude values in ' + dict_args['seabass_file'][0] + ' MUST be between -90/90N deg.')

            # construct sys call to val_extract
            sys_call_str = 'val_extract' + \
                           ' ifile=' + dict_args['sat_file'][0] + \
                           ' slon=' + str(ds.lon[row]) + \
                           ' slat=' + str(ds.lat[row]) + \
                           ' global_att=1' + \
                           ' variable_att=1' + \
                           ' boxsize=' + str(dict_args['box_size'][0]) + flag_arg
            # variable_att flag needed to extract units
            # global_att flag needed to extract sensor/instrument names
            # sunzen=70.0  <---- HISOLZEN threshold
            # satzen=60.0  <---- HISATZEN threshold

            pid = subprocess.run(sys_call_str, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if pid.returncode == 99:
                #if dict_args['verbose']:
                    #print('No matchup: in situ target not in granule.')
                continue #no valid matchup
            elif pid.returncode == 101 or pid.returncode == 102:
                parser.error('val_extract failed -- only accepts Level-2 (L2) satellite files. ' + \
                                dict_args['sat_file'][0] + ' is not a valid L2 file')
            elif pid.returncode != 0:
                parser.error('val_extract failed -- verify that the val_extract binary is compiled and on your PATH and that ' + \
                                dict_args['sat_file'][0] + ' exists')

        # define structures to keep track of val_extract's output files
        file_ls = OrderedDict()
        file_del = []
        var_ls = []

        upix_ct = 0
        fpix_ct = dict_args['box_size'][0]^2
        pix_ct  = 0

        tims = 0
        tim_sat = 0

        cvs = []

        # parse the extract information
        file_del.append(dict_args['sat_file'][0] + '.qc');
        try:
            fileobj = open(dict_args['sat_file'][0] + '.qc','r')
            lines = fileobj.readlines()
            for line in lines:
                newline = re.sub("[\r\n]+",'',line)
                if 'unflagged_pixel_count' in newline:
                    upix_ct = int(newline.split('=')[1])
                elif 'flagged_pixel_count' in newline:
                    fpix_ct = int(newline.split('=')[1])
                elif 'pixel_count' in newline:
                    pix_ct = int(newline.split('=')[1])
                elif 'time' in newline:
                    try:
                        tims = re.search("(\d+)-(\d+)-(\d+)\s+(\d+):(\d+):(\d+)", newline.split('=')[1]);
                        tim_sat = datetime(year=int(tims.group(1)), \
                                  month=int(tims.group(2)), \
                                  day=int(tims.group(3)), \
                                  hour=int(tims.group(4)), \
                                  minute=int(tims.group(5)), \
                                  second=int(tims.group(6)))
                    except:
                        continue
                elif 'variables' in newline:
                    var_ls = newline.split('=')[1].split(',')
                    for var in var_ls:
                        file_del.append(dict_args['sat_file'][0] + '.qc.' + var);
                        if 'l2_flags'   in var or \
                           'stdv_sst'   in var or \
                           'stdv_sst4'  in var or \
                           'bias_sst'   in var or \
                           'bias_sst4'  in var or \
                           'flags_sst'  in var or \
                           'flags_sst4' in var or \
                           'longitude'  in var or \
                           'latitude'   in var:
                            continue
                        file_ls[var] = dict_args['sat_file'][0] + '.qc.' + var
            fileobj.close()
        except:
            parser.error(' unable to open and read file ' + dict_args['sat_file'][0] + '.qc')

        # parse the satellite nc file information
        file_del.append(dict_args['sat_file'][0] + '.qc.global_attrs');
        [inst, plat] = readValEglobatt(dict_args['sat_file'][0] + '.qc.global_attrs', parser)
        if not inst:
            inst = 'na'
        if not plat:
            plat = 'na'

        # apply exclusion criteria
        # compute and evaluate the max time diff test
        if tim_sat > tim_max or tim_sat < tim_min:
            clean_file_lis(file_del)
            if dict_args['verbose']:
                print('No matchup: failed MAX_TIME_DIFF, required =',dict_args["max_time_diff"][0],'Exclusion level = 1, Matrix row =',row)
            continue #no valid matchup

        # compute and evaluate the min valid sat pix test
        if (pix_ct - fpix_ct) != 0:
            if upix_ct >= dict_args['box_size'][0]:
                pix_thresh = 100.0 * (upix_ct / (pix_ct - fpix_ct))
                if pix_thresh < dict_args['min_valid_sat_pix'][0]:
                    clean_file_lis(file_del)
                    if dict_args['verbose']:
                        print('No matchup: failed MIN_VALID_SAT_PIX, required =',dict_args['min_valid_sat_pix'][0],'found =',pix_thresh,'Exclusion level = 4, Matrix row =',row)
                    continue #no valid matchup
            else:
                clean_file_lis(file_del)
                if dict_args['verbose']:
                    print('No matchup: failed MIN_VALID_SAT_PIX, extracted satellite pixels less than box size, required =',dict_args['box_size'][0],'found =',upix_ct,'Exclusion level = 3, Matrix row =',row)
                continue #no valid matchup
        else:
            clean_file_lis(file_del)
            if dict_args['verbose']:
                print('No matchup: failed MIN_VALID_SAT_PIX, division by zero when deriving pix_thresh due to required L2FLAG criteria, Exclusion level = 2, Data row =',row)
            continue #no valid matchup

        # compute and evaluate the CV test
        for var in var_ls:
            try:
                m = re.search("(rrs|aot)_([\d.]+)", var.lower())
                # only compute CV using Rrs between 405nm and 570nm and using AOT between 860nm and 900nm
                if (float(m.group(2)) > 405 and float(m.group(2)) < 570) or (float(m.group(2)) > 860 and float(m.group(2)) < 900):
                    if 'modis' in inst.lower():
                        # for MODIS Aqua and Terra don't use land bands 469nm and 555nm
                        if float(m.group(2)) == 469 or float(m.group(2)) == 555:
                            continue

                    [fmean, fstdev, units] = readValEfile(file_ls[var], parser)
                    if not fmean or not fstdev:
                        continue
                    if float(fmean) != 0:
                        cvs.append(float(fstdev)/float(fmean))
                    else:
                        cvs.append(0.0)
            except:
                continue #case if var not Rrs nor AOT, also catches L2 IOP's rrsdiff_giop

        if cvs: #handles non-OC files, which don't have vars for CV test
            if median(cvs) > dict_args['max_coeff_variation'][0]:
                clean_file_lis(file_del)
                if dict_args['verbose']:
                    print('No matchup: failed MAX_COEF_OF_VARIATION, required =',dict_args['max_coeff_variation'][0],'found =',median(cvs),'Exclusion level = 5, Data row =',row)
                continue #no valid matchup

        write_flag = 1 #only write out (write_flag == true), if matchups found

        #save L2_fname
        L2file_varname = inst + '_' + plat + '_l2fname'
        ds = addDataToOutput(ds,row, L2file_varname.lower(),'none',os.path.basename(dict_args['sat_file'][0]))

        #save rrsaot_cv
        if cvs:
            rrscv_varname = inst + '_' + plat + '_rrsaot_cv'
            ds = addDataToOutput(ds,row, rrscv_varname.lower(),'unitless',median(cvs))

        # save extract-variables
        for var in file_ls:
            if 'qual_sst' in var:
                [fmean, fmax] = readValEfile_qsst(file_ls[var], parser)

                #save mean qual_sst value
                var_name = inst + '_' + plat + '_' + var.lower() + '_mean'
                ds = addDataToOutput(ds,row, var_name.lower(),'none',fmean)

                #save max qual_sst value
                var_name = inst + '_' + plat + '_' + var.lower() + '_max'
                ds = addDataToOutput(ds,row, var_name.lower(),'none',fmax)

            else:
                [fmean, fstdev, units] = readValEfile(file_ls[var], parser)

                #save filtered_mean for each var in file_lis
                var_name = inst + '_' + plat + '_' + var.lower()
                ds = addDataToOutput(ds,row, var_name.lower(),units,fmean)

                #save filtered_stddev for each var in file_lis
                var_name = inst + '_' + plat + '_' + var.lower() + '_sd'
                ds = addDataToOutput(ds,row, var_name.lower(),units,fstdev)

        clean_file_lis(file_del)

    if write_flag == 1:
        if not dict_args['no_header_comment']:
            ds.comments.append(' ')
            ds.comments.append(' File ammended by OCSSW match-up maker script: mk_matchup.py on ' + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + ',')
            ds.comments.append(' using satellite data from ' + inst + ' ' + plat + ' granule: ' + dict_args['sat_file'][0])
            ds.comments.append(' WARNINGS: This script does NOT adjust in situ data to water-leaving values')
            ds.comments.append('           This script does NOT account for potential oversampling by the in situ data in time or space.')
            ds.comments.append('           If successive calls to this script are made for a single in situ file AND multiple-valid-overpasses exist,')
            ds.comments.append('               only the data from the last successive call will be saved to the output file. This may NOT be the best')
            ds.comments.append('               quality satellite data in space and time.')
            ds.comments.append(' Default exclusion criteria are obtained from: S.W. Bailey and P.J. Werdell, "A multi-sensor approach')
            ds.comments.append(' for the on-orbit validation of ocean color satellite data products", Rem. Sens. Environ. 102, 12-23 (2006).')
            ds.comments.append(' NOTE: The coefficient of variation is computed using all available Rrs between 405nm and 570nm and AOT between 860nm and 900nm,')
            ds.comments.append('       with the exception of MODIS Rrs land bands at 469nm and 555nm')
            ds.comments.append(' EXCLUSION CRITERIA applied to this satellite file:')
            ds.comments.append('     Box size of satellite extract = ' + str(dict_args['box_size'][0]) + ' pixels by ' + str(dict_args['box_size'][0]) + ' pixels')
            ds.comments.append('     Minimum percent valid satellite pixels = ' + str(dict_args['min_valid_sat_pix'][0]))
            ds.comments.append('     Maximum solar zenith angle = 70 degrees')
            ds.comments.append('     Maximum satellite zenith angel = 60 degrees')
            ds.comments.append('     Maximum time difference between satellite and in situ = ' + str(dict_args['max_time_diff'][0]) + ' hours')
            ds.comments.append('     Maximum coefficient of variation of satellite pixels = ' + str(dict_args['max_coeff_variation'][0]))
            ds.comments.append(' EXCEPTIONS to Bailey and Werdell (2006):')
            ds.comments.append('     1. User defined values given to mk_matchup.py will override recommended defaults.')
            ds.comments.append('     2. The maximum allowed solar zenith angle used here is 70-deg vs the paper-recommended 75-deg.')
            ds.comments.append('     3. Rrs and AOT data are only in the OC L2 satellite product suite.')
            ds.comments.append('        Other file_types (SST, SST4, IOP, etc) will not evaluate any maximum coefficient of variation threshhold.')
            ds.comments.append('     4. For all SST file_types, the qual_sst_max or qual_sst_mean fields should be used to screen the sst value quality.')
            ds.comments.append('        The qual_sst value varies between 0 (best) and 4 (worst).')
            ds.comments.append('        The qual_sst_mean (qual_sst_max) is the mean (max) of the ' + \
                               str(dict_args['box_size'][0]) + ' by ' + str(dict_args['box_size'][0]) + ' pixel satellite extract.')
            ds.comments.append(' ')

        print('Satellite/in situ match-up(s) found')
        if dict_args['out_file']:
            ds.writeSBfile(dict_args['out_file'][0])
        else:
            ds.writeSBfile(dict_args['seabass_file'][0])
    else:
        print('No valid satellite match-ups found for any lat/lon/time pairs in',dict_args['seabass_file'][0])

    return


def clean_file_lis(file_ls):
    import os
    for d in file_ls:
        try:
            os.remove(d)
        except:
            print('WARNING: Cleanup of ',d,' failed. Verify that you have read/write priviledges in the current working directory.')
    return


def readValEglobatt(fname, parser):
    import re
    inst = ''
    plat = ''
    try:
        fileobj = open(fname,'r')
        lines = fileobj.readlines()
        for line in lines:
            newline = re.sub("[\r\n]+",'',line)
            if 'instrument=' in newline:
                inst = newline.lower().split('=')[1]
            elif 'platform=' in newline:
                plat = newline.lower().split('=')[1]
        fileobj.close()
    except:
        parser.error(' unable to open and read file ' + fname)
    return(inst, plat)


def readValEfile(fname, parser):
    import re
    fmean  = ''
    fstdev = ''
    units  = ''
    try:
        fileobj = open(fname,'r')
        lines = fileobj.readlines()
        fileobj.close()

        for line in lines:
            newline = re.sub("[\r\n]+",'',line)
            if 'filtered_mean' in newline:
                fmean = newline.split('=')[1]
            elif 'filtered_stddev' in newline:
                fstdev = newline.split('=')[1]
            elif 'units' in newline:
                units = re.sub('\s', '_', newline.split('=')[1])
    except:
        parser.error(' unable to open and read file ' + fname)
    return(fmean, fstdev, units)


def readValEfile_qsst(fname,parser):
    import re
    fmean  = ''
    fmax = ''
    try:
        fileobj = open(fname,'r')
        lines = fileobj.readlines()
        fileobj.close()

        for line in lines:
            newline = re.sub("[\r\n]+",'',line)
            if 'mean' in newline and not 'filtered_' in newline:
                fmean = newline.split('=')[1]
            elif 'max' in newline:
                fmax = newline.split('=')[1]
    except:
        parser.error(' unable to open and read file ' + fname)
    return(fmean, fmax)


def addDataToOutput(ds,row, var_name,units,var_value):
    from copy import copy
    from SB_support_v35 import is_number

    #check for valid inputs
    if not var_value:
        var_value = str(ds.missing)
    if not units:
        units = 'none'

    #define fields, units, and data column, if needed
    if var_name not in ds.data:
        ds.headers['fields'] = ds.headers['fields'] + ',' + var_name
        try:
            ds.headers['units'] = ds.headers['units'] + ',' + units.lower()
        except:
            print('Warning: no units found in SeaBASS file header')
        ds.data[var_name] = copy(ds.out_ls)

    #save data to column and row

    #TODO - handle repeat matchups per row (near poles, etc)
    #       Relevant for calling script in a loop on multiple L2 files
    #       Currently, skips overwriting valid data in that row and column/var_name, preserving the first valid matchup

    if is_number(ds.data[var_name][row]):
        if float(ds.data[var_name][row]) == ds.missing:
            ds.data[var_name][row] = var_value
    else:
        if str(ds.missing) in ds.data[var_name][row]:
            ds.data[var_name][row] = var_value

    return(ds)


if __name__ == "__main__": main()
