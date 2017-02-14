#!/usr/bin/env python3

"""
A Perl script to create and output satellite matchups from a SeaBASS file given:
    1) an OB.DAAC L2 (SST, SST4, IOP, or OC) satellite file
    2) a valid SeaBASS file with lat,lon,date,time as /field entries or lat,lon,year,month,day,hour,minute,second as /field entries.

written by J.Scott on 2016/12/13 (joel.scott@nasa.gov)
"""

def main():

    import argparse, os, sys, re, subprocess
    from datetime import datetime, timedelta
    from copy import copy
    from math import isnan
    from collections import OrderedDict
    sys.path.append('./modules')
    from SB_support_v35 import readSB

    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,description='''\
      This program create and output satellite matchups from a given SeaBASS file.
      
      Outputs:
          1) the original SeaBASS data
          AND
          2) collocated satellite products as additional fields as columns into -out_file 
             OR if -out_file is not specified, as -seabass_file with _matchups.sb appeneded

      Required inputs:
          1) an OB.DAAC L2 (SST, SST4, IOP, or OC) satellite file
          2) a valid SeaBASS file with lat,lon,date,time as field entries or
             lat,lon,year,month,day,hour,minute,second as field entries.

      Example usage call:
         mk_matchup.py --sat_file=[OB.DAAC satellite file name].nc --seabass_file=[SeaBASS file name].sb --out_file=[OPTIONAL, output SeaBASS file name].sb
      ''',add_help=True)

    parser.add_argument('--sat_file', nargs=1, required=True, type=str, help='''\
      Valid OB.DAAC L2 satellite netcdf file name.
      ''')

    parser.add_argument('--seabass_file', nargs=1, required=True, type=str, help='''\
      Valid SeaBASS file name
      File must contain lat,lon,date,time as field entries
      OR
      lat,lon,year,month,day,hour,minute,second as field entries.
      ''')

    parser.add_argument('--out_file', nargs=1, type=str, help='''\
      OPTIONAL: output SeaBASS file name
      Matched-up satellite variables will be appended as additional fields
      to the data matrix and relevant headers.
      ''')

    parser.add_argument('--clobber', nargs='?', const=True, help='''\
      OPTIONAL: clobber original -seabass_file and reuse as out_file
      Matched-up satellite variables will be APPENDED as additional fields
      to the data matrix and relevant headers in the -seabass_file.
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
      Valid value: (1 - 4 hours), default = 3
      '''))

    parser.add_argument('--max_coeff_variation', nargs=1, default=([0.15]), type=float, help=('''\
      OPTIONAL: maximum coefficient of variation of satellite pixels within the satellite extract
      Valid value: (0.0 - 1.0), default = 0.15
      '''))

    # Exclusion criteria; defaults from:
    # S.W. Bailey and P.J. Werdell, "A multi-sensor approach for the on-orbit validation of ocean color satellite data products", Rem. Sens. Environ. 102, 12-23 (2006).
    # with one exception: The maximum allowed solar zenith angle used here is 70-deg vs the paper's recommended 75-deg.

    args=parser.parse_args()
    if not args.sat_file or not args.seabass_file:
        parser.error("you must specify a --sat_file AND a --seabass_file")
    else:
        dict_args=vars(args)

    # input verification
    if ((dict_args["box_size"][0] % 2) == 0) or (dict_args["box_size"][0] > 11) or (dict_args["box_size"][0] < 3):
        parser.error("invalid --box_size specified, must be an ODD integer between 3 and 11")

    if (dict_args["min_valid_sat_pix"][0] > 100.0) or (dict_args["min_valid_sat_pix"][0] < 0.0):
        parser.error("invalid --min_valid_sat_pix specified, must be a percentage expressed as a floating point number between 0.0 and 100.0")

    if (dict_args["max_time_diff"][0] > 4) or (dict_args["max_time_diff"][0] < 1):
        parser.error("invalid --max_time_diff specified, must be a value between 1 and 4")
    else:
        twin_min = -1.0 * dict_args["max_time_diff"][0];
        twin_max =  1.0 * dict_args["max_time_diff"][0];

    if (dict_args["max_coeff_variation"][0] > 1.0) or (dict_args["max_coeff_variation"][0] < 0.0):
        parser.error("invalid --max_coeff_variation specified, must be an floating point number between 0.0 and 1.0")

    if not args.out_file:
        if not args.clobber:
            dict_args['out_file']=[dict_args['seabass_file'][0] + '_matchups.sb']
        else:
            dict_args['out_file']=dict_args['seabass_file']

    # read and verify SeaBASS file and required fields
    if os.path.isfile(dict_args['seabass_file'][0]):
        ds = readSB(filename=dict_args['seabass_file'][0], mask_missing=0, mask_above_detection_limit=0, mask_below_detection_limit=0)
    else:
        parser.error('ERROR: invalid --seabass_file specified. Does: ' + dict_args['seabass_file'][0] + ' exist?')

    try:
        ds.lon = [float(i) for i in ds.data['lon']]
        ds.lat = [float(i) for i in ds.data['lat']]
    except:
        parser.error('missing fields in SeaBASS file. File must contain lat,lon')

    try:
        ds.datetime = readSB.fd_datetime_ymdhms(ds.data['year'], ds.data['month'], ds.data['day'], ds.data['hour'], ds.data['minute'], ds.data['second'])
    except:
        try:
            ds.datetime = readSB.fd_datetime(ds.data['date'], ds.data['time'])
        except:
            parser.error('missing fields in SeaBASS file. File must contain date,time OR year,month,day,hour,minute,second')

    write_flag = 0

    out_ls = []
    for i in range(0,len(ds.lat)):
        out_ls.append(str(ds.missing))

    # loop through input SeaBASS file data rows
    for lat,lon,dt,row in zip(ds.lat,ds.lon,ds.datetime,range(0,len(ds.lat))):

        # verify inputs
        if isnan(lat) or isnan(lon):
            continue

        if abs(lon) > 180.0:
            parser.error('invalid longitude input: all longitude values in ' + dict_args['seabass_file'][0] + ' MUST be between -180/180E deg.')
        if abs(lat) > 90.0:
            parser.error('invalid latitude input: all latitude values in ' + dict_args['seabass_file'][0] + ' MUST be between -90/90N deg.')

        # create time range of satellite obs to extract
        tim_min = dt + timedelta(hours=twin_min)
        tim_max = dt + timedelta(hours=twin_max)

        # construct sys call to make
        print(' ')
        print('Calculating satellite match-up for L2 file: ')
        sys_call_str = 'val_extract' + \
                       ' ifile=' + dict_args['sat_file'][0] + \
                       ' slon=' + str(lon) + \
                       ' slat=' + str(lat) + \
                       ' global_att=1' + \
                       ' variable_att=1' + \
                       ' boxsize=' + str(dict_args['box_size'][0]) + \
                       ' ignore_flags=LAND\ HIGLINT\ HILT\ HISATZEN\ HISOLZEN\ STRAYLIGHT\ CLDICE\ ATMFAIL\ LOWLW\ FILTER\ NAVFAIL\ NAVWARN' + \
                       ' count_flags=LAND\ NAVFAIL'
        # variable_att flag needed to extract units
        # global_att flag needed to extract sensor/instrument names
        # sunzen=70.0  <---- HISOLZEN threshold
        # satzen=60.0  <---- HISATZEN threshold

        s1 = subprocess.call(sys_call_str, shell=True)

        if s1 == 99:

            print('WARNING: No satellite matchups found for point: lat=' + str(lat) + ', lon=' + str(lon) + ', time=' + dt.strftime('%Y-%m-%dT%H:%M:%SZ') + ' in ' + dict_args['seabass_file'][0])
            continue

        elif s1 == 101 or s1 == 102:

            parser.error('val_extract failed -- only accepts Level-2 (L2) satellite files. This: ' + dict_args['sat_file'][0] + ' is not a valid L2 file.')

        elif s1 != 0:

            parser.error('val_extract failed -- ensure that the val_extract binary is compiled and on your PATH and that ' + dict_args['sat_file'][0] + ' exists.')

        # define structures to keep track of val_extract's output files
        file_ls = OrderedDict()
        file_del = []
        var_ls = []

        upix_ct = 0
        fpix_ct = dict_args['box_size'][0]^2
        pix_ct  = 0

        tims = 0
        tim_sat = 0

        inst = 'na'
        plat = 'na'

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
                        tims = re.match("(\d+)-(\d+)-(\d+)\s+(\d+):(\d+):(\d+)", newline.split('=')[1]);
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
                           'qual_sst'   in var or \
                           'qual_sst4'  in var or \
                           'longitude'  in var or \
                           'latitude'   in var:
                            continue
                        file_ls[var] = dict_args['sat_file'][0] + '.qc.' + var
            fileobj.close()
        except:
            parser.error(' unable to open and read file: ' + dict_args['sat_file'][0] + '.qc')

        # parse the satellite nc file information
        file_del.append(dict_args['sat_file'][0] + '.qc.global_attrs');
        try:
            fileobj = open(dict_args['sat_file'][0] + '.qc.global_attrs','r')
            lines = fileobj.readlines()
            for line in lines:
                newline = re.sub("[\r\n]+",'',line)
                if 'instrument' in newline:
                    inst = newline.lower().split('=')[1]
                elif 'platform' in newline:
                    plat = newline.lower().split('=')[1]
            fileobj.close()
        except:
            parser.error(' unable to open and read file: ' + dict_args['sat_file'][0] + '.qc.global_attrs')

        # apply exclusion criteria
        if tim_sat > tim_max or tim_sat < tim_min:
            print('Warning: satellite match-up does NOT meet exclusion criteria for --max_time_diff = ' + str(dict_args['max_time_diff'][0]))
            clean_file_lis(file_del)
            continue

        if (pix_ct - fpix_ct) != 0:
            pix_thresh = 100.0 * (upix_ct / (pix_ct - fpix_ct))
            if pix_thresh < dict_args['min_valid_sat_pix'][0]:
                print('Warning: satellite match-up does NOT meet exclusion criteria for --min_valid_sat_pix = ' + str(dict_args['min_valid_sat_pix'][0]))
                clean_file_lis(file_del)
                continue
        else:
            print('Warning: satellite match-up does NOT meet exclusion criteria for --min_valid_sat_pix = ' + str(dict_args['min_valid_sat_pix'][0]))
            clean_file_lis(file_del)
            continue

        write_flag = 1
        print('Satellite/in situ match-up found.')

        # add L2_fname var space to output array
        var_fname = inst + '_' + plat + '_fname'
        if var_fname not in ds.data:
            ds.headers['fields'] = ds.headers['fields'] + ',' + var_fname
            try:
                ds.headers['units'] = ds.headers['units'] + ',none'
            except:
                print('Warning: no units found in SeaBASS file header.')
            ds.data[var_fname] = copy(out_ls)

        # extract variables
        for var in file_ls:
            var_name = inst + '_' + plat + '_' + var.lower()
            units = 'none'
            value = str(ds.missing)

            try:
                fileobj = open(file_ls[var],'r')
                lines = fileobj.readlines()
                for line in lines:
                    newline = re.sub("[\r\n]+",'',line)
                    if 'filtered_mean' in newline:
                        value = newline.split('=')[1]
                    elif 'units' in newline:
                        units = re.sub('\s', '_', newline.split('=')[1])
                fileobj.close()
            except:
                parser.error(' unable to open and read file: ' + file_ls[var])

            if var_name not in ds.data:
                ds.headers['fields'] = ds.headers['fields'] + ',' + var_name
                try:
                    ds.headers['units'] = ds.headers['units'] + ',' + units.lower()
                except:
                    print('Warning: no units found in SeaBASS file header.')
                ds.data[var_name] = copy(out_ls)

            #TODO - handle repeat matchups per row (near poles, etc)
            #       Relevant for calling script in a loop on multiple L2 files, especially with -clobber flag
            #       Currently, skips overwriting valid data in that row and column/var_name, preserving the first valid matchup
            if float(ds.data[var_name][row]) == ds.missing and float(value) != ds.missing:
                ds.data[var_fname][row] = os.path.basename(dict_args['sat_file'][0])
                ds.data[var_name][row] = value

        clean_file_lis(file_del)

    print(' ')
    if write_flag == 1:
        print('Writing output to file: ' + dict_args['out_file'][0])
        fout = open(dict_args['out_file'][0],'w')
        fout.write('/begin_header\n')
        for header in ds.headers:
            fout.write('/' + header + '=' + ds.headers[header] + '\n')
        for comment in ds.comments:
            fout.write('!' + comment + '\n')
        fout.write('/end_header\n')
        if 'comma' in ds.headers['delimiter']: delim = ','
        if 'space' in ds.headers['delimiter']: delim = ' '
        if 'tab'   in ds.headers['delimiter']: delim = '\t'
        for i in range(0,len(ds.lat)):
            row_ls = []
            for var in ds.data:
                row_ls.append(str(ds.data[var][i]))
            fout.write(delim.join(row_ls) + '\n')
        fout.close()
    else:
        print('Exiting: No valid satellite match-ups found for any lat/lon/time pairs in: ' + dict_args['seabass_file'][0])



def clean_file_lis(file_ls):
    import os
    for d in file_ls:
        try:
            os.remove(d)
        except:
            print('WARNING: Cleanup of ' + d + ' failed. Ensure that you have read/write priviledges in the current directory.')
    return



if __name__ == "__main__": main()
