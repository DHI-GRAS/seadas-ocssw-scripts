#!/usr/bin/env python3

"""
A script to perform searches of the EarthData Common Metadata Repository (CMR)
for satellite granule names given:
    OB.DAAC satellite/instrument
AND
        lat/lon/time pair (or range)
    OR
        a valid SeaBASS file with lat/lon/time

written by J.Scott on 2016/12/12 (joel.scott@nasa.gov)
"""

def main():

    import argparse, os, sys, re, json, subprocess
    from urllib import request
    from datetime import datetime, timedelta
    from math import isnan
    from collections import OrderedDict
    sys.path.append('./modules')
    from SB_support_v35 import readSB

    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,description='''\
      This program perform searches of the EarthData Common Metadata Repository (CMR) for satellite
      granule names given an OB.DAAC satellite/instrument, lat/lon/time pair or range
      
      Outputs:
         1) a list of OB.DAAC L2 satellite file granule names that contain the input criteria, per the CMR records.
         2) a list of public download links to fetch the matching satellite file granules, per the CMR's records.
      
      Inputs:
        The argument-list is a set of -keyword value pairs.

      Example usage calls:
         fd_matchup.py --sat=modist --lat_pnt=23.0 --lon_pnt=170.0 --time_pnt=2015-11-16T09:00:00Z --time_window=8
         fd_matchup.py --sat=modist --time_range_min=2015-11-15T09:00:00Z --time_range_max=2015-11-17T09:00:00Z --lat_range_min=23.0 --lat_range_max=25.0 --lon_range_min=170.0 --lon_range_max=175.0
         fd_matchup.py --sat=modist --time_window=4 --seabass_file=[your SB file name].sb
      ''',add_help=True)

    parser.add_argument('--sat', nargs=1, required=True, type=str, choices=['modisa','modist','viirsn','goci','meris','czcs','octs','seawifs'], help='''\
      String specifier for satellite platform/instrument
      
      Valid options are:
      -----------------
      modisa  = MODIS on AQUA
      modist  = MODIS on TERRA
      viirsn  = VIIRS on NPP
      meris   = MERIS on ENVISAT
      goci    = GOCI on COMS
      czcs    = CZCS on Nimbus-7
      seawifs = SeaWiFS on OrbView-2
      octs    = OCTS on ADEOS-I
      ''')

    parser.add_argument('--data_type', nargs=1, type=str, default=(['*']), choices=['oc','iop','sst'], help='''\
      OPTIONAL: String specifier for satellite data type
      Default behavior returns all product suites
      
      Valid options are:
      -----------------
      oc   = Returns OC (ocean color) product suite
      iop  = Returns IOP (inherent optical properties) product suite
      sst  = Returns SST product suite (including SST4 where applicable)
      ''')

    parser.add_argument('--lat_pnt', nargs=1, type=float, help=('''\
      Latitude (point) of interest
      Valid values: (-90,90N)
      Use with -lon_pnt
      '''))

    parser.add_argument('--lon_pnt', nargs=1, type=float, help=('''\
      Longitude (point) of interest
      Valid values: (-180,180E)
      Use with -lat_pnt
      '''))

    parser.add_argument('--lat_range_min', nargs=1, type=float, help=('''\
      Minimum latitude (range) for region of interest
      Valid values: (-90,90N)
      Use with -lon_range_min, -lon_range_max, -lat_range_max
      '''))

    parser.add_argument('--lat_range_max', nargs=1, type=float, help=('''\
      Maximum latitude (range) for region of interest
      Valid values: (-90,90N)
      Use with -lon_range_min, -lon_range_max, -lat_range_min
      '''))

    parser.add_argument('--lon_range_min', nargs=1, type=float, help=('''\
      Minimum longitude (range) for region of interest
      Valid values: (-180,180E)
      Use with -lon_range_max, -lat_range_min, -lat_range_max
      '''))

    parser.add_argument('--lon_range_max', nargs=1, type=float, help=('''\
      Maximum longitude (range) for region of interest
      Valid values: (-180,180E)
      Use with -lon_range_min, -lat_range_min, -lat_range_max
      '''))

    parser.add_argument('--time_pnt', nargs=1, type=str, help='''\
      Time (point) of interest in UTC
      Default behavior: returns matches within 90 minutes before and 90 minutes after this given time
      Valid format: string of the form: yyyy-mm-ddThh:mm:ssZ
      OPTIONALLY: Use with -time_window
      ''')

    parser.add_argument('--time_window', nargs=1, type=int, default=([3]), help=('''\
      Hour time window about given time(s)
      OPTIONAL: default value 3 hours (i.e. - 90 minutes before and 90 minutes after given time)
      Valid values: integer hours (1-11)
      Use with -seabass_file OR -time_pnt
      '''))

    parser.add_argument('--time_range_min', nargs=1, type=str, help='''\
      Minimum time (range) of interest in UTC
      Valid format: string of the form: yyyy-mm-ddThh:mm:ssZ
      Use with -time_range_max
     ''')
    parser.add_argument('--time_range_max', nargs=1, type=str, help='''\
      Maximum time (range) of interest in UTC
      Valid format: string of the form: yyyy-mm-ddThh:mm:ssZ
      Use with -time_range_min
     ''')

    parser.add_argument('--seabass_file', nargs=1, type=str, help='''\
      Valid SeaBASS file name
      File must contain lat,lon,date,time as /field entries OR
      lat,lon,year,month,day,hour,minute,second as /field entries.
      ''')

    parser.add_argument('--get_data', nargs=1, type=str, help='''\
      Flag to download all identified satellite granules.
      Requires the use of a system wget call.
      Set to the desired output directory.
      ''')

    args=parser.parse_args()
    if not args.sat:
        parser.error("you must specify an satellite string to conduct a search")
    else:
        dict_args=vars(args)
        sat = dict_args['sat'][0]

    #dictionary of lists of CMR platform, instrument, collection names
    dict_plat = {}

    dict_plat['modisa']  = ['MODIS','AQUA','MODISA_L2_']
    dict_plat['modist']  = ['MODIS','TERRA','MODIST_L2_']
    dict_plat['viirsn']  = ['VIIRS','NPP','VIIRSN_L2_']
    dict_plat['meris']   = ['MERIS','ENVISAT','MERIS_L2_']
    dict_plat['goci']    = ['GOCI','COMS','GOCI_L2_']
    dict_plat['czcs']    = ['CZCS','Nimbus-7','CZCS_L2_']
    dict_plat['seawifs'] = ['SeaWiFS','OrbView-2','SeaWiFS_L2_']
    dict_plat['octs']    = ['OCTS','ADEOS-I','OCTS_L2_']

    if sat not in dict_plat:
        parser.error('you provided an invalid satellite string specifier. Use -h flag to see a list of valid options for --sat')

    if args.time_window:
        if dict_args['time_window'][0] < 0 or dict_args['time_window'][0] > 11:
            parser.error('invalid --time_window value provided. Please specify an integer between 0 and 11 hours. Received --time_window = ' + str(dict_args['time_window'][0]))
        twin_Hmin = -1 * int(dict_args['time_window'][0] / 2)
        twin_Mmin = -60 * int((dict_args['time_window'][0] / 2) - int(dict_args['time_window'][0] / 2))
        twin_Hmax = 1 * int(dict_args['time_window'][0] / 2)
        twin_Mmax = 60 * ((dict_args['time_window'][0] / 2) - int(dict_args['time_window'][0] / 2));

    #beginning of file/loop if-condition
    if args.seabass_file:
        if os.path.isfile(dict_args['seabass_file'][0]):
            ds = readSB(filename=dict_args['seabass_file'][0], mask_missing=1, mask_above_detection_limit=1, mask_below_detection_limit=1)
        else:
            parser.error('ERROR: invalid --seabass_file specified. Does: ' + dict_args['seabass_file'][0] + ' exist?')

        #given date,time,lat,lon OR year,month,day,hour,minute,second,lat,lon
        try:
            ds.datetime = readSB.fd_datetime_ymdhms(ds.data['year'], ds.data['month'], ds.data['day'], ds.data['hour'], ds.data['minute'], ds.data['second'])
        except:
            try:
                ds.datetime = readSB.fd_datetime(ds.data['date'], ds.data['time'])
            except:
                parser.error('missing fields in SeaBASS file. File must contain date,time OR year,month,day,hour,minute,second')

        try:
            ds.lon = [float(i) for i in ds.data['lon']]
            ds.lat = [float(i) for i in ds.data['lat']]
        except:
            parser.error('missing fields in SeaBASS file. File must contain lat,lon')

        granlinks = OrderedDict()
        hits = 0

        for lat,lon,dt in zip(ds.lat,ds.lon,ds.datetime):
            if isnan(lat) or isnan(lon):
                continue
            if abs(lon) > 180.0:
                parser.error('invalid longitude input: all longitude values in ' + dict_args['seabass_file'][0] + ' MUST be between -180/180E deg.')
            if abs(lat) > 90.0:
                parser.error('invalid latitude input: all latitude values in ' + dict_args['seabass_file'][0] + ' MUST be between -90/90N deg.')
            tim_min = dt + timedelta(hours=twin_Hmin,minutes=twin_Mmin) #use as: tim_min.strftime('%Y-%m-%dT%H:%M:%SZ')
            tim_max = dt + timedelta(hours=twin_Hmax,minutes=twin_Mmax) #use as: tim_max.strftime('%Y-%m-%dT%H:%M:%SZ')
            url = 'https://cmr.earthdata.nasa.gov/search/granules.json?page_size=2000' + \
                        '&provider=OB_DAAC' + \
                        '&point=' + str(lon) + ',' + str(lat) + \
                        '&instrument=' + dict_plat[sat][0] + \
                        '&platform=' + dict_plat[sat][1] + \
                        '&entry_title=' + dict_plat[sat][2] + dict_args['data_type'][0] + \
                        '&options[entry_title][pattern]=true' + \
                        '&temporal=' + tim_min.strftime('%Y-%m-%dT%H:%M:%SZ') + ',' + tim_max.strftime('%Y-%m-%dT%H:%M:%SZ') + \
                        '&sort_key=entry_title'
            req = request.Request(url)
            req.add_header('Accept', 'application/json')
            content = json.loads(request.urlopen(req).read().decode('utf-8'))

            hits = hits + len(content['feed']['entry'])
            for entry in content['feed']['entry']:
                granid = entry['producer_granule_id']
                granlinks[granid] = entry['links'][0]['href']
        if hits > 0:
            unique_hits = 0
            for granid in granlinks:
                unique_hits = unique_hits + 1
                print('Match found for: ' + dict_plat[sat][1] + '/' + dict_plat[sat][0] + \
                      ', ' + tim_min.strftime('%Y-%m-%dT%H:%M:%SZ') + ' to ' + tim_max.strftime('%Y-%m-%dT%H:%M:%SZ') + \
                      ', lat=' + str(lat) + ', lon=' + str(lon))
                print('Match-up granule name: ' + granid)
                if args.get_data and dict_args['get_data'][0]:
                    print('Downloading file to: ' + dict_args['get_data'][0])
                    s1 = subprocess.call("wget -4 --content-disposition --directory-prefix=" + dict_args['get_data'][0] + " " + granlinks[granid], shell=True)
                else:
                    print('Download link: ' + granlinks[granid])
                print('')
            print('Number of granules found: ' + str(unique_hits))
        else:
            print('WARNING: No granules found for ' + dict_plat[sat][1] + '/' + dict_plat[sat][0] + ' and any lat/lon/time inputs.')
    #end of file/loop if-condition

    #beginning of lat/lon/time if-condition
    else:
        #Define time vars from input
        if args.time_pnt:
            try:
                tims = re.match("(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})Z", dict_args['time_pnt'][0]);
                dt = datetime(year=int(tims.group(1)), \
                              month=int(tims.group(2)), \
                              day=int(tims.group(3)), \
                              hour=int(tims.group(4)), \
                              minute=int(tims.group(5)), \
                              second=int(tims.group(6)))
                tim_min = dt + timedelta(hours=twin_Hmin,minutes=twin_Mmin) #use as: tim_min.strftime('%Y-%m-%dT%H:%M:%SZ')
                tim_max = dt + timedelta(hours=twin_Hmax,minutes=twin_Mmax) #use as: tim_max.strftime('%Y-%m-%dT%H:%M:%SZ')
            except:
                parser.error('invalid time arguments provided. All time inputs MUST be in UTC in the form: YYYY-MM-DDTHH:MM:SSZReceived --time_pnt = ' + dict_args['time_pnt'][0])
        elif args.time_range_min and args.time_range_max:
            try:
                tims = re.match("(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})Z", dict_args['time_range_min'][0]);
                tim_min = datetime(year=int(tims.group(1)), \
                              month=int(tims.group(2)), \
                              day=int(tims.group(3)), \
                              hour=int(tims.group(4)), \
                              minute=int(tims.group(5)), \
                              second=int(tims.group(6))) #use as: tim_min.strftime('%Y-%m-%dT%H:%M:%SZ')
                tims = re.match("(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})Z", dict_args['time_range_max'][0]);
                tim_max = datetime(year=int(tims.group(1)), \
                              month=int(tims.group(2)), \
                              day=int(tims.group(3)), \
                              hour=int(tims.group(4)), \
                              minute=int(tims.group(5)), \
                              second=int(tims.group(6))) #use as: tim_max.strftime('%Y-%m-%dT%H:%M:%SZ')
            except:
                parser.error('invalid time arguments provided. All time inputs MUST be in UTC in the form: YYYY-MM-DDTHH:MM:SSZ Received --time_range_min = ' + dict_args['time_range_min'][0] + ' and --time_range_max = ' + dict_args['time_range_max'][0])
            if tim_min > tim_max:
                parser.error('invalid time inputs: --time_range_min MUST be less than --time_range_max. Received --time_range_min = ' + dict_args['time_range_min'][0] + ' and --time_range_max = ' + dict_args['time_range_max'][0])
        else:
            parser.error('invalid time arguments provided. All time inputs MUST be in UTC. Valid options are --time_pnt= OR --time_range_min= AND --time_range_max=, where all times are of the format YYYY-MM-DDTHH:MM:SSZ')

        #Define lat vars from input and call search query
        if args.lat_pnt and args.lon_pnt:
            if abs(dict_args['lon_pnt'][0]) > 180.0:
                parser.error('invalid longitude input: --lon_pnt MUST be between -180/180E deg. Received lon = ' + str(dict_args['lon_pnt'][0]))
            if abs(dict_args['lat_pnt'][0]) > 90.0:
                parser.error('invalid latitude input: --lat_pnt MUST be between -90/90N deg. Received lat = ' + str(dict_args['lat_pnt'][0]))
            url = 'https://cmr.earthdata.nasa.gov/search/granules.json?page_size=2000' + \
                            '&provider=OB_DAAC' + \
                            '&point=' + str(dict_args['lon_pnt'][0]) + ',' + str(dict_args['lat_pnt'][0]) + \
                            '&instrument=' + dict_plat[sat][0] + \
                            '&platform=' + dict_plat[sat][1] + \
                            '&entry_title=' + dict_plat[sat][2] + dict_args['data_type'][0] + \
                            '&options[entry_title][pattern]=true' + \
                            '&temporal=' + tim_min.strftime('%Y-%m-%dT%H:%M:%SZ') + ',' + tim_max.strftime('%Y-%m-%dT%H:%M:%SZ') + \
                            '&sort_key=entry_title'
            req = request.Request(url)
            req.add_header('Accept', 'application/json')
            content = json.loads(request.urlopen(req).read().decode('utf-8'))
        elif args.lat_range_min and args.lat_range_max and \
             args.lon_range_min and args.lon_range_max:
            if abs(dict_args['lon_range_min'][0]) > 180.0 or abs(dict_args['lon_range_max'][0]) > 180.0:
                parser.error('invalid longitude inputs: --lon_range_min and --lon_range_max MUST be between -180/180E deg. Received --lon_range_min = ' + str(dict_args['lon_range_min'][0]) + ' and --lon_range_max = ' + str(dict_args['lon_range_max'][0]))
            if abs(dict_args['lat_range_min'][0]) > 90.0 or abs(dict_args['lat_range_max'][0]) > 90.0:
                parser.error('invalid latitude inputs: --lat_range_min and --lat_range_max MUST be between -90/90N deg. Received --lat_range_min = ' + str(dict_args['lat_range_min'][0]) + ' and -lat_range_max = ' + str(dict_args['lat_range_max'][0]))
            if dict_args['lat_range_min'][0] > dict_args['lat_range_max'][0]:
                parser.error('invalid latitude inputs: --lat_range_min MUST be less than --lat_range_max and both MUST be between -90/90N deg. Received --lat_range_min = ' + str(dict_args['lat_range_min'][0]) + ' and --lat_range_max = ' + str(dict_args['lat_range_max'][0]))
            if dict_args['lon_range_min'][0] > dict_args['lon_range_max'][0]:
                parser.error('invalid longitude inputs: --lon_range_min MUST be less than --lon_range_max and both MUST be between -180/180E deg. Received --lon_range_min = ' + str(dict_args['lon_range_min'][0]) + ' and --lon_range_max = ' + str(dict_args['lon_range_max'][0]))
            url = 'https://cmr.earthdata.nasa.gov/search/granules.json?page_size=2000' + \
                            '&provider=OB_DAAC' + \
                            '&bounding_box=' + str(dict_args['lon_range_min'][0]) + ',' + str(dict_args['lat_range_min'][0]) + ',' + \
                                                   str(dict_args['lon_range_max'][0]) + ',' + str(dict_args['lat_range_max'][0]) + \
                            '&instrument=' + dict_plat[sat][0] + \
                            '&platform=' + dict_plat[sat][1] + \
                            '&entry_title=' + dict_plat[sat][2] + dict_args['data_type'][0] + \
                            '&options[entry_title][pattern]=true' + \
                            '&temporal=' + tim_min.strftime('%Y-%m-%dT%H:%M:%SZ') + ',' + tim_max.strftime('%Y-%m-%dT%H:%M:%SZ') + \
                            '&sort_key=entry_title'
            req = request.Request(url)
            req.add_header('Accept', 'application/json')
            content = json.loads(request.urlopen(req).read().decode('utf-8'))
        else:
            parser.error('invalid combination of --lat_pnt and --lon_pnt OR --lat_range_min, --lat_range_max, --lon_range_min, and --lon_range_max arguments provided. All latitude inputs MUST be between -90/90N deg. All longitude inputs MUST be between -180/180E deg.')

        #Parse json return for the lat/lon/time if-condition
        granlinks = OrderedDict()
        hits = len(content['feed']['entry'])
        if hits > 0:
            for entry in content['feed']['entry']:
                granid = entry['producer_granule_id']
                granlinks[granid] = entry['links'][0]['href']
                print('Match found for: ' + dict_plat[sat][1] + '/' + dict_plat[sat][0] + \
                      ', ' + tim_min.strftime('%Y-%m-%dT%H:%M:%SZ') + ' to ' + tim_max.strftime('%Y-%m-%dT%H:%M:%SZ'))
                print('Match-up granule name: ' + granid)
                if args.get_data and dict_args['get_data'][0]:
                    print('Downloading file to: ' + dict_args['get_data'][0])
                    s1 = subprocess.call("wget -4 --content-disposition --directory-prefix=" + dict_args['get_data'][0] + " " + granlinks[granid], shell=True)
                else:
                    print('Download link: ' + granlinks[granid])
                print('')
            print('Number of granules found: ' + str(hits))
        else:
            print('WARNING: No matching granules found for ' + dict_plat[sat][1] + '/' + dict_plat[sat][0] + \
                  ' containing the requested lat/lon area during the ' + str(dict_args['time_window'][0]) + '-hr window of ' + \
                  tim_min.strftime('%Y-%m-%dT%H:%M:%SZ') + ' to ' + tim_max.strftime('%Y-%m-%dT%H:%M:%SZ'))

if __name__ == "__main__": main()
