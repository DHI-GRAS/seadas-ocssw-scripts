#!/usr/bin/env python3

from SB_support_v35 import readSB
from netCDF4 import Dataset
import os
import datetime
import sys
import numpy as np
import argparse
from collections import OrderedDict

def getSensorDefs(instrument,platform):
    sensorDef = OrderedDict()
    # here's where we can store things like k_no2 as well :)

    if instrument == 'seawifs':
        sensorDef['wavelength'] = [412, 443, 490, 510, 555, 670, 765, 865]
        sensorDef['platform'] = 'OrbView-2'
        sensorDef['instrument'] = 'SeaWiFS'

    elif instrument == 'octs':
        sensorDef['wavelength'] = [412, 443, 490, 516, 565, 667, 765, 862]
        sensorDef['platform'] = 'ADEOS'
        sensorDef['instrument'] = 'OCTS'

    elif instrument == 'avhrr':
        sensorDef['wavelength'] = [630, 855, 3700, 11000, 12000]
        sensorDef['platform'] = 'AVHRR'
        sensorDef['instrument'] = 'AVHRR'

    elif instrument == 'osmi':
        sensorDef['wavelength'] = [412, 443, 490, 555, 765, 865]
        sensorDef['platform'] = 'KOMPSAT'
        sensorDef['instrument'] = 'OSMI'
        
    elif instrument == 'modis':
        sensorDef['wavelength'] = [412,443,469,488,531,547,555,645,667,678,748,859,869,1240,1640,2130]
        if platform == 'aqua':
            sensorDef['platform'] = 'Aqua'
        else:
            sensorDef['platform'] = 'Terra'

        sensorDef['instrument'] = 'MODIS'

    elif instrument == 'czcs':
        sensorDef['wavelength'] = [443, 520, 550, 670]
        sensorDef['platform'] = 'Nimbus-7'
        sensorDef['instrument'] = 'CZCS'

    elif instrument == 'ocm':
        sensorDef['wavelength'] = [414, 441, 486, 511, 556, 669, 769, 865]
        sensorDef['platform'] = 'IRS-P4'
        sensorDef['instrument'] = 'OCM'

    elif instrument == 'ocm-2':
        sensorDef['wavelength'] = [415, 442, 491, 512, 557, 620, 745, 866]
        sensorDef['platform'] = 'Oceansat-2'
        sensorDef['instrument'] = 'OCM-2'

    elif instrument == 'meris':
        sensorDef['wavelength'] = [413, 443, 490, 510, 560, 620, 665, 681, 709, 754, 762, 779, 865, 885, 900]
        sensorDef['platform'] = 'Envisat'
        sensorDef['instrument'] = 'MERIS'

    elif instrument == 'viirs':
        sensorDef['wavelength'] = [410, 443, 486, 551, 671, 745, 862, 1238, 1601, 2257]
        sensorDef['platform'] = 'Suomi-NPP'
        sensorDef['instrument'] = 'VIIRS'

    elif instrument == 'ocrvc':
        sensorDef['wavelength'] = [412, 443, 490, 510, 531, 555, 670]
        sensorDef['platform'] = 'OCRVC'
        sensorDef['instrument'] = 'OCRVC'

    elif instrument == 'hico':
        sensorDef['wavelength'] = [353, 358, 364, 370, 375, 381, 387, 393, 398, 404, 410, 416, 421, 427, 433, 438, 444, 450, 456, 461, 467, 473, 479, 484, 490, 496, 501, 507, 513, 519, 524, 530, 536, 542, 547, 553, 559, 564, 570, 576, 582, 587, 593, 599, 605, 610, 616, 622, 627, 633, 639, 645, 650, 656, 662, 668, 673, 679, 685, 690, 696, 702, 708, 713, 719, 725, 731, 736, 742, 748, 753, 759, 765, 771, 776, 782, 788, 794, 799, 805, 811, 816, 822, 828, 834, 839, 845, 851, 857, 862, 868, 874, 880, 885, 891, 897, 902, 908, 914, 920, 925, 931, 937, 943, 948, 954, 960, 965, 971, 977, 983, 988, 994, 1000, 1006, 1011, 1017, 1023, 1028, 1034, 1040, 1046, 1051, 1057, 1063, 1069, 1074, 1080]
        sensorDef['platform'] = 'ISS'
        sensorDef['instrument'] = 'HICO'

    elif instrument == 'goci':
        sensorDef['wavelength'] = [412, 443, 490, 555, 660, 680, 745, 865]
        sensorDef['platform'] = 'COMS'
        sensorDef['instrument'] = 'GOCI'

    elif instrument == 'oli':
        sensorDef['wavelength'] = [443, 482, 561, 655, 865, 1609, 2201]
        sensorDef['platform'] = 'Landsat-8'
        sensorDef['instrument'] = 'OLI'

    elif instrument == 'ocia':
        sensorDef['wavelength'] = [366, 376, 385, 395, 405, 414, 424, 434, 443, 453, 463, 472, 482, 492, 502, 511, 521, 531, 541, 550, 560, 570, 580, 589, 599, 609, 619, 628, 638, 648, 658, 665, 674, 684, 694, 704, 714, 723, 733, 743, 753, 762, 772, 782, 792, 801, 811, 821, 831, 840, 850, 860, 869, 879, 889, 937, 1239, 1382, 1642, 2127, 2247]
        sensorDef['platform'] = 'PACE'
        sensorDef['instrument'] = 'OCIA"'

    elif instrument == 'averis':
        sensorDef['wavelength'] = [366, 376, 385, 395, 405, 414, 424, 434, 443, 453, 463, 472, 482, 492, 502, 511, 521, 531, 541, 550, 560, 570, 580, 589, 599, 609, 619, 628, 638, 648, 658, 665, 674, 684, 694, 704, 714, 723, 733, 743, 753, 762, 772, 782, 792, 801, 811, 821, 831, 840, 850, 860, 869, 879, 889, 898, 908, 918, 927, 937, 947, 956, 966, 976, 985, 995, 1005, 1014, 1024, 1033, 1043, 1053, 1062, 1072, 1081, 1091, 1101, 1110, 1120, 1129, 1139, 1148, 1158, 1167, 1177, 1186, 1196, 1205, 1215, 1224, 1234, 1243, 1253, 1263, 1273, 1283, 1293, 1303, 1313, 1323, 1333, 1343, 1352, 1362, 1372, 1382, 1392, 1402, 1412, 1422, 1432, 1442, 1452, 1462, 1472, 1482, 1492, 1502, 1512, 1522, 1532, 1542, 1552, 1562, 1572, 1582, 1592, 1602, 1612, 1622, 1632, 1642, 1651, 1661, 1671, 1681, 1691, 1701, 1711, 1721, 1731, 1741, 1751, 1761, 1771, 1781, 1791, 1801, 1811, 1821, 1831, 1841, 1851, 1861, 1871, 1876, 1886, 1896, 1906, 1916, 1926, 1936, 1946, 1956, 1966, 1977, 1987, 1997, 2007, 2017, 2027, 2037, 2047, 2057, 2067, 2077, 2087, 2097, 2107, 2117, 2127, 2137, 2147, 2157, 2167, 2177, 2187, 2197, 2207, 2217, 2227, 2237, 2247, 2257, 2267, 2277, 2287, 2297, 2306, 2316]
        sensorDef['platform'] = 'AVIRIS'
        sensorDef['instrument'] = 'AVIRIS'

    elif instrument == 'prism':
        sensorDef['wavelength'] = [350.357208, 361.678589, 373.000854, 384.324005, 395.648071, 406.973022, 418.298889, 429.625671, 440.953308, 452.281891, 463.611359, 474.941711, 486.27298, 497.605133, 508.938202, 520.272156, 531.606995, 542.94281, 554.279419, 565.617004, 576.955444, 588.2948, 599.635071, 610.976257, 622.318298, 633.661255, 645.005127, 656.349915, 667.695557, 679.042114, 690.389587, 701.737915, 713.087158, 724.437317, 735.788391, 747.140381, 758.493225, 769.846985, 781.20166, 792.55719, 803.913635, 815.270996, 826.629272, 837.988403]
        sensorDef['platform'] = 'PRISM'
        sensorDef['instrument'] = 'PRISM'

    elif instrument == 'olci':
        sensorDef['wavelength'] = [400, 412, 442, 490, 510, 560, 620, 665, 674, 681, 709, 754, 761, 764, 768, 779, 865, 885, 900, 940, 1012]
        sensorDef['platform'] = 'Sentinel-3'
        sensorDef['instrument'] = 'OLCI'

    elif instrument == 'sgli':
        sensorDef['wavelength'] = [380, 412, 443, 490, 529, 566, 672, 763, 867, 1055, 1385, 1634, 2211]
        sensorDef['platform'] = 'GCOM_C'
        sensorDef['instrument'] = 'SGLI'

    elif instrument == 'msi':
        sensorDef['wavelength'] = [444, 497, 560, 664, 704, 740, 783, 837, 865, 945, 1374, 1613, 2200]
        sensorDef['platform'] = 'Sentinel-2A'
        sensorDef['instrument'] = 'MSI'

    else:
        sys.exit("Instrument not supported: %s (%s)" % (instrument,platform))

    return sensorDef

def main():
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
    description='''
    This program takes a specially-crafted SeaBASS formatted file and outputs
    an L1B file which can be read by the l2gen program.  Below is an example
    file with comments explaining things.


/begin_header
!
! COMMENTS
!
! This is a test input file for the seabass2L1B.py script.
! The file format is defined at:
!
!   https://seabass.gsfc.nasa.gov/wiki/Data_Submission#Data Format
!
! required headers
!   instrument = SeaWiFS, OCTS, AVHRR, OSMI, MODIS, CZCS, OCM, OCM-2, MERIS, VIIRS,
!                OCRVC, HICO, GOCI, OLI, OCIA, AVIRIS, PRISM, OLCI, SGLI, MSI
!   platform = Aqua, Terra
!   missing
!   delimiter
!   fields
!
! optional headers
!   pixels_per_line = if supplied the data is wrapped into a 2D file instead of
!                     one pixel per line in the L1B file.
!   pixnum = comma delimited array, "pixels_per_line" in length
!   start_date
!   start_time
!   north_latitude
!   east_longitude
!   senz
!   sena
!   solz
!   sola
!   windspeed
!   windangle
!   pressure
!   ozone
!   relhumid
!   watervapor
!   
!
! required fields are:
!   Lt_nnn = (W m^-2 um^-1 sr^-1) an Lt field is required for each wavelength of
!            the selected sensor.
!
! optional fields
!   scantime = unix time (double, secs since 1970), takes precedence over
!              date,time.  If neither scantime nor date,time exist then
!              start_date, start_time header is used.
!   date = yyyymmdd
!   time = hh:mm:ss
!   lat
!   lon
!   senz
!   sena
!   solz
!   sola
!   windspeed
!   windangle
!   pressure
!   ozone
!   relhumid
!   watervapor
!
/instrument=MODIS
/platform=Aqua
/missing=-32767
/delimiter=space
/start_date=20010314
/start_time=16:01:30[GMT]
/north_latitude=-46.797[DEG]
/east_longitude=-95.561[DEG]
/pixels_per_line=3
/pixnum=0,0,0
/senz=44.72
/sena=83.44
/solz=51.02
/sola=-29.62
/fields=Lt_412,Lt_443,Lt_469,Lt_488,Lt_531,Lt_547,Lt_555,Lt_645,Lt_667,Lt_678,Lt_748,Lt_859,Lt_869,Lt_1240,Lt_1640,Lt_2130
/end_header
61.86 54.37 50.11 40.83 26.54 23.22 21.63 10.78 9.70 9.09 6.03 3.3 3.17 .84 .34 .09
61.86 54.37 50.11 40.83 26.54 23.22 21.63 10.78 9.70 9.09 6.03 3.3 3.17 .84 .34 .09
61.86 54.37 50.11 40.83 26.54 23.22 21.63 10.78 9.70 9.09 6.03 3.3 3.17 .84 .34 .09
61.86 54.37 50.11 40.83 26.54 23.22 21.63 10.78 9.70 9.09 6.03 3.3 3.17 .84 .34 .09
61.86 54.37 50.11 40.83 26.54 23.22 21.63 10.78 9.70 9.09 6.03 3.3 3.17 .84 .34 .09
61.86 54.37 50.11 40.83 26.54 23.22 21.63 10.78 9.70 9.09 6.03 3.3 3.17 .84 .34 .09
61.86 54.37 50.11 40.83 26.54 23.22 21.63 10.78 9.70 9.09 6.03 3.3 3.17 .84 .34 .09
61.86 54.37 50.11 40.83 26.54 23.22 21.63 10.78 9.70 9.09 6.03 3.3 3.17 .84 .34 .09
61.86 54.37 50.11 40.83 26.54 23.22 21.63 10.78 9.70 9.09 6.03 3.3 3.17 .84 .34 .09


    The argument-list is a set of keyword=value pairs.
    ''', add_help=True)

    parser.add_argument('-ifile', nargs=1, type=str, help='input SeaBASS file')
    parser.add_argument('-ofile', nargs=1, type=str, help='output L1B file name ')

    args=parser.parse_args()
    dict_args=vars(args)
    if not dict_args['ifile'] or not dict_args['ofile']:
        parser.error("you must specify an input file and an output file")

    ifileName = dict_args['ifile'][0]
    ofileName = dict_args['ofile'][0]

    ds = readSB(filename=ifileName, mask_missing=False, mask_above_detection_limit=False,
                mask_below_detection_limit=False, no_warn=True)

    # make sure all of the required fields are in the header section
    if 'instrument' not in ds.headers:
        sys.exit('Error: Must include "instrument" in the headers.')
    if 'platform' not in ds.headers:
        sys.exit('Error: Must include "platform" in the headers.')
    if 'missing' not in ds.headers:
        sys.exit('Error: Must include "missing" in the headers.')
    if 'delimiter' not in ds.headers:
        sys.exit('Error: Must include "delimiter" in the headers.')
    if 'fields' not in ds.headers:
        sys.exit('Error: Must include "fields" in the headers.')

    sensorDef = getSensorDefs(ds.headers['instrument'], ds.headers['platform'])
    sensorWavelengths = sensorDef['wavelength']
    sensorBandNames = []
    for wave in sensorWavelengths:
        sensorBandNames.append("Lt_" + str(wave))

    fieldNames = list(ds.data.keys())
    numPixels = len(ds.data[fieldNames[0]])
    pixelsPerLine = 1
    try:
        pixelsPerLine = int(ds.headers['pixels_per_line'])
    except:
        pass
    numLines = int(numPixels / pixelsPerLine)

    lat = []
    try:
        lat = ds.data['lat']
    except:
        try:
            lat =  np.full((numLines,pixelsPerLine), float((ds.headers['north_latitude'].split('['))[0]))
        except:
            sys.exit('Error: Must include "north_latitude" in the header or "lat" in the data block')

    lon = []
    try:
        lon = ds.data['lon']
    except:
        try:
            lon = np.full((numLines,pixelsPerLine), float((ds.headers['east_longitude'].split('['))[0]))
        except:
            sys.exit('Error: Must include "east_longitude" in the header or "lon" in the data block')

    solz = []
    try:
        solz = ds.data['solz']
    except:
        try:
            solz = np.full((numLines, pixelsPerLine), ds.headers['solz'])
        except:
            pass

    sola = []
    try:
        sola = ds.data['sola']
    except:
        try:
            sola = np.full((numLines, pixelsPerLine), ds.headers['sola'])
        except:
            pass

    senz = []
    try:
        senz = ds.data['senz']
    except:
        try:
            senz = np.full((numLines, pixelsPerLine), ds.headers['senz'])
        except:
            sys.exit('Error: Must include "senz" in the header or in the data block')

    sena = []
    try:
        sena = ds.data['sena']
    except:
        try:
            sena = np.full((numLines, pixelsPerLine), ds.headers['sena'])
        except:
            sys.exit('Error: Must include "sena" in the header or in the data block')

    pixnum = []
    try:
        pixnum = [ int(x) for x in ds.headers['pixnum'].split(",") ]
    except:
        pass

    windspeed = []
    try:
        windspeed = ds.data['windspeed']
    except:
        try:
            windspeed = np.full((numLines, pixelsPerLine), ds.headers['windspeed'])
        except:
            pass

    windangle = []
    try:
        windangle = ds.data['windangle']
    except:
        try:
            windangle = np.full((numLines, pixelsPerLine), ds.headers['windangle'])
        except:
            pass

    pressure = []
    try:
        pressure = ds.data['pressure']
    except:
        try:
            pressure = np.full((numLines, pixelsPerLine), ds.headers['pressure'])
        except:
            pass

    ozone = []
    try:
        ozone = ds.data['ozone']
    except:
        try:
            ozone = np.full((numLines, pixelsPerLine), ds.headers['ozone'])
        except:
            pass

    relhumid = []
    try:
        relhumid = ds.data['relhumid']
    except:
        try:
            relhumid = np.full((numLines, pixelsPerLine), ds.headers['relhumid'])
        except:
            pass

    watervapor = []
    try:
        watervapor = ds.data['watervapor']
    except:
        try:
            watervapor = np.full((numLines, pixelsPerLine), ds.headers['watervapor'])
        except:
            pass


    
    if os.path.exists(ofileName):
        os.remove(ofileName)

    ncfile = Dataset(ofileName, "w", format="NETCDF4")

    ncfile.createDimension('number_of_lines', numLines)
    ncfile.createDimension('pixels_per_line', pixelsPerLine)
    ncfile.createDimension('number_of_bands', len(sensorWavelengths))

    sensorgrp = ncfile.createGroup('sensor_band_parameters')
    scangrp = ncfile.createGroup('scan_line_attributes')
    datagrp = ncfile.createGroup('geophysical_data')
    navgrp = ncfile.createGroup('navigation_data')

    # global attributes
    ncfile.title = (sensorDef['instrument'] + ' Level-1B').encode("ascii")
    ncfile.instrument = sensorDef['instrument'].encode("ascii")
    ncfile.platform = sensorDef['platform'].encode("ascii")
    ncfile.processing_level = 'L1B'.encode("ascii")
    ncfile.date_created = (datetime.datetime.utcnow().isoformat()).encode("ascii")
    ncfile.history = (' '.join(sys.argv)).encode("ascii")

    # create sensor group variables
    sensorgrp.createVariable('wavelength', 'i', ('number_of_bands'), fill_value=-32767)
    sensorgrp.createVariable('F0', 'f', ('number_of_bands'), fill_value=-32767)
    sensorgrp.createVariable('Tau_r', 'f', ('number_of_bands'), fill_value=-32767)
    sensorgrp.createVariable('k_oz', 'f', ('number_of_bands'), fill_value=-32767)
    sensorgrp.createVariable('t_co2', 'f', ('number_of_bands'), fill_value=-32767)
    sensorgrp.createVariable('k_no2', 'f', ('number_of_bands'), fill_value=-32767)
    sensorgrp.createVariable('a_h2o', 'f', ('number_of_bands'), fill_value=-32767)
    sensorgrp.createVariable('b_h2o', 'f', ('number_of_bands'), fill_value=-32767)
    sensorgrp.createVariable('c_h2o', 'f', ('number_of_bands'), fill_value=-32767)
    sensorgrp.createVariable('d_h2o', 'f', ('number_of_bands'), fill_value=-32767)
    sensorgrp.createVariable('e_h2o', 'f', ('number_of_bands'), fill_value=-32767)
    sensorgrp.createVariable('f_h2o', 'f', ('number_of_bands'), fill_value=-32767)
    sensorgrp.createVariable('g_h2o', 'f', ('number_of_bands'), fill_value=-32767)
    sensorgrp.createVariable('awhite', 'f', ('number_of_bands'), fill_value=-32767)
    sensorgrp.createVariable('aw', 'f', ('number_of_bands'), fill_value=-32767)
    sensorgrp.createVariable('bbw', 'f', ('number_of_bands'), fill_value=-32767)
    if len(pixnum):
        sensorgrp.createVariable('pixnum', 'i', ('pixels_per_line'), fill_value=-32767)

    # create scan group variables
    scangrp.createVariable('scantime', 'd', ('number_of_lines'), fill_value=-32767)

    # create geophysical data variables
    for varName in sensorBandNames:
        datagrp.createVariable(varName, 'f', ('number_of_lines', 'pixels_per_line'), fill_value=-32767)

    # create navigation variables
    navgrp.createVariable('longitude', 'f', ('number_of_lines', 'pixels_per_line'), fill_value=-32767)
    navgrp.createVariable('latitude', 'f', ('number_of_lines', 'pixels_per_line'), fill_value=-32767)
    navgrp.createVariable('senz', 'f', ('number_of_lines', 'pixels_per_line'), fill_value=-32767)
    navgrp.createVariable('sena', 'f', ('number_of_lines', 'pixels_per_line'), fill_value=-32767)
    if len(solz):
        navgrp.createVariable('solz', 'f', ('number_of_lines', 'pixels_per_line'), fill_value=-32767)
        navgrp.createVariable('sola', 'f', ('number_of_lines', 'pixels_per_line'), fill_value=-32767)

    # create ancillary data variables if they exist
    if len(windspeed) or len(windangle) or len(pressure) or len(ozone) or len(relhumid) or len(watervapor):
        ancillarygrp = ncfile.createGroup('ancillary_data')
        if len(windspeed):
            ancillarygrp.createVariable('windspeed', 'f', ('number_of_lines', 'pixels_per_line'), fill_value=-32767)
        if len(windangle):
            ancillarygrp.createVariable('windangle', 'f', ('number_of_lines', 'pixels_per_line'), fill_value=-32767)
        if len(pressure):
            ancillarygrp.createVariable('pressure', 'f', ('number_of_lines', 'pixels_per_line'), fill_value=-32767)
        if len(ozone):
            ancillarygrp.createVariable('ozone', 'f', ('number_of_lines', 'pixels_per_line'), fill_value=-32767)
        if len(relhumid):
            ancillarygrp.createVariable('relhumid', 'f', ('number_of_lines', 'pixels_per_line'), fill_value=-32767)
        if len(watervapor):
            ancillarygrp.createVariable('watervapor', 'f', ('number_of_lines', 'pixels_per_line'), fill_value=-32767)


    ####################################################
    # done creating variables, now we can write the data
    ####################################################

    # fill ancillary data values
    if len(windspeed):
        ancillarygrp.variables['windspeed'][:] =  windspeed   
    if len(windangle):
        ancillarygrp.variables['windangle'][:] = windangle
    if len(pressure):
        ancillarygrp.variables['pressure'][:] = pressure   
    if len(ozone):
        ancillarygrp.variables['ozone'][:] = ozone   
    if len(relhumid):
        ancillarygrp.variables['relhumid'][:] = relhumid
    if len(watervapor):
        ancillarygrp.variables['watervapor'][:] = watervapor

    # fill data values
    sensorgrp.variables['wavelength'][:] = sensorWavelengths
    if len(pixnum):
        try:
            sensorgrp.variables['pixnum'][:] = pixnum
        except:
            sys.exit('Error: "pixnum" must have have a length of "pixels_per_line"')

    if 'scantime' in fieldNames:
        try:
            scangrp.variables['scantime'][:] = ds.data['scantime'][::pixelsPerLine]
        except:
            sys.exit('Error: the number of lines in the data section must be a multiple of "pixels_per_line"')
            
    else:
        scantime = np.array([(lambda scantime: [dt.timestamp()])(dt) for dt in ds.fd_datetime()])
        try:
            scangrp.variables['scantime'][:] = scantime[::pixelsPerLine]
        except:
            sys.exit('Error: the number of lines in the data section must be a multiple of "pixels_per_line"')
            
    # fill in data values
    for varName in sensorBandNames:
        datagrp.variables[varName][:] = ds.data[varName.lower()]

    navgrp.variables['latitude'][:] = lat
    navgrp.variables['longitude'][:] = lon
    navgrp.variables['senz'][:] = senz
    navgrp.variables['sena'][:] = sena

    if len(solz):
        navgrp.variables['solz'][:] = solz
        navgrp.variables['sola'][:] = sola

    ncfile.close()

if __name__ == "__main__": main()
