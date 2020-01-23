"""

SeaDAS library for commonly used functions within other python scripts

"""
from __future__ import print_function

import os
import sys
import re
import subprocess
import time
import datetime
import logging
import requests
from requests.adapters import HTTPAdapter

from modules.MetaUtils import readMetadata


#  ------------------ DANGER -------------------
#
# The next 3 functions:
#    getSession
#    httpdl
#    uncompressFile
#
# exist in two places:
#    OCSSWROOT/src/manifest/manifest.py
#    OCSSWROOT/scripts/modules/ProcUtils.py
#
# Make sure changes get into both files.
#

DEFAULT_CHUNK_SIZE = 131072

# requests session object used to keep connections around
obpgSession = None

def getSession(verbose=0, ntries=5):
    global obpgSession

    if not obpgSession:
        # turn on debug statements for requests
        if verbose > 1:
            logging.basicConfig(level=logging.DEBUG)

        obpgSession = requests.Session()
        obpgSession.mount('https://', HTTPAdapter(max_retries=ntries))

        if verbose:
            print("OBPG session started")
    else:
        if verbose > 1:
            print("reusing existing OBPG session")

    return obpgSession


#  ------------------ DANGER -------------------
# See comment above
def httpdl(server, request, localpath='.', outputfilename=None, ntries=5,
           uncompress=False, timeout=30., verbose=0, 
           chunk_size=DEFAULT_CHUNK_SIZE):

    status = 0
    urlStr = 'https://' + server + request

    global obpgSession

    getSession(verbose=verbose, ntries=ntries)

    with obpgSession.get(urlStr, stream=True, timeout=timeout) as req:

        ctype = req.headers.get('Content-Type')
        if req.status_code in (400, 401, 403, 404, 416):
            status = req.status_code
        elif ctype and ctype.startswith('text/html'):
            status = 401
        else:
            if not os.path.exists(localpath):
                os.umask(0o02)
                os.makedirs(localpath, mode=0o2775)
    
            if not outputfilename:
                cd = req.headers.get('Content-Disposition')
                if cd:
                    outputfilename = re.findall("filename=(.+)", cd)[0]
                else:
                    outputfilename = urlStr.split('/')[-1]
    
            ofile = os.path.join(localpath, outputfilename)
        
            with open(ofile, 'wb') as fd:
                for chunk in req.iter_content(chunk_size=chunk_size):
                    if chunk: # filter out keep-alive new chunks
                        fd.write(chunk)
    
            if uncompress and re.search(".(Z|gz|bz2)$", ofile):
                compressStatus = uncompressFile(ofile)
                if compressStatus:
                    status = compressStatus
            else:
                status = 0

    return status


#  ------------------ DANGER -------------------
# See comment above
def uncompressFile(compressed_file):
    """
    uncompress file
    compression methods:
        bzip2
        gzip
        UNIX compress
    """

    compProg = {"gz": "gunzip -f ", "Z": "gunzip -f ", "bz2": "bunzip2 -f "}
    exten = os.path.basename(compressed_file).split('.')[-1]
    unzip = compProg[exten]
    p = subprocess.Popen(unzip + compressed_file, shell=True)
    status = os.waitpid(p.pid, 0)[1]
    if status:
        print("Warning! Unable to decompress %s" % compressed_file)
        return status
    else:
        return 0


def cleanList(filename, parse=None):
    """
    Parses file list from oceandata.sci.gsfc.nasa.gov through html source
    intended for update_luts.py, by may have other uses
    """
    oldfile = os.path.abspath(filename)
    newlist = []
    if parse is None:
        parse = re.compile(r"(?<=(\"|\')>)\S+(\.(hdf|h5|dat|txt))")
    if not os.path.exists(oldfile):
        print('Error: ' + oldfile + ' does not exist')
        sys.exit(1)
    else:
        of = open(oldfile, 'r')
        for line in of:
            if '<td><a' in line:
                try:
                    newlist.append(parse.search(line).group(0))
                except Exception:
                    pass
        of.close()
        os.remove(oldfile)
        return newlist


def date_convert(datetime_i, in_datetype=None, out_datetype=None):
    """
    Convert between datetime object and/or standard string formats

    Inputs:
        datetime_i   datetime object or formatted string
        in_datetype  input format code;
                     must be present if datetime_i is a string
        out_datetype output format code; if absent, return datetime object

        datetype may be one of:
        'j': Julian     YYYYDDDHHMMSS
        'g': Gregorian  YYYYMMDDHHMMSS
        't': TAI        YYYY-MM-DDTHH:MM:SS.uuuuuuZ
        'h': HDF-EOS    YYYY-MM-DD HH:MM:SS.uuuuuu
    """

    # define commonly used date formats
    date_time_format = {
        'd': "%Y%m%d",  # YYYYMMDD
        'j': "%Y%j%H%M%S",  # Julian    YYYYDDDHHMMSS
        'g': "%Y%m%d%H%M%S",  # Gregorian YYYYMMDDHHMMSS
        't': "%Y-%m-%dT%H:%M:%S.%fZ",  # TAI YYYY-MM-DDTHH:MM:SS.uuuuuuZ
        'h': "%Y-%m-%d %H:%M:%S.%f",  # HDF-EOS YYYY-MM-DD HH:MM:SS.uuuuuu
    }
    if in_datetype is None:
        dateobj = datetime_i
    else:
        dateobj = datetime.datetime.strptime(datetime_i,
                                             date_time_format[in_datetype])

    if out_datetype is None:
        return dateobj
    else:
        return dateobj.strftime(date_time_format[out_datetype])


def addsecs(datetime_i, dsec, datetype=None):
    """
    Offset datetime_i by dsec seconds.
    """
    dateobj = date_convert(datetime_i, datetype)
    delta = datetime.timedelta(seconds=dsec)
    return date_convert(dateobj + delta, out_datetype=datetype)

def diffsecs(time0, time1, datetype=None):
    """
    Return difference in seconds.
    """
    t0 = date_convert(time0, datetype)
    t1 = date_convert(time1, datetype)
    return (t1-t0).total_seconds()

def round_minutes(datetime_i, datetype=None, resolution=5, rounding=0):
    """Round to nearest "resolution" minutes, preserving format.

    Parameters
    ----------
    datetime_i : string
        String representation of datetime, in "datetype" format
    datetype : string
        Format of datetime, as strftime or date_convert() code
    resolution : integer, optional
        Number of minutes to round to (default=5)
    rounding : integer, optional
        Rounding "direction", where
            <0 = round down
             0 = round to nearest (default)
            >0 = round up
    """
    dateobj = date_convert(datetime_i, datetype)

    if rounding < 0: # round down
        new_minute = (dateobj.minute // resolution) * resolution
    elif rounding > 0: # round up
        new_minute = (dateobj.minute // resolution + 1) * resolution
    else:  # round to nearest value
        new_minute = ((dateobj.minute + resolution/2.0) // resolution) * resolution

    # truncate to current hour; add new minutes
    dateobj -= datetime.timedelta(minutes=dateobj.minute,
                                  seconds=dateobj.second,
                                  microseconds=dateobj.microsecond)
    dateobj += datetime.timedelta(minutes=new_minute)

    return date_convert(dateobj, out_datetype=datetype)


def remove(file_to_delete):
    """
    Delete a file from the system
    A simple wrapper for os.remove
    """

    if os.path.exists(file_to_delete):
        os.remove(file_to_delete)
        return 0

    return 1


def ctime(the_file):
    """
    returns days since file creation
    """

    today = datetime.date.today().toordinal()
    utc_create = time.localtime(os.path.getctime(the_file))

    return today - datetime.date(utc_create.tm_year, utc_create.tm_mon, utc_create.tm_mday).toordinal()


def mtime(the_file):
    """
    returns days since last file modification
    """

    today = datetime.date.today().toordinal()
    utc_mtime = time.localtime(os.path.getmtime(the_file))

    return today - datetime.date(utc_mtime.tm_year, utc_mtime.tm_mon, utc_mtime.tm_mday).toordinal()


def cat(file_to_print):
    """
    Print a file to the standard output.
    """
    with open(file_to_print) as f:
        print(f.read())


def check_sensor(inp_file):
    """
    Determine the satellite sensor from the file metadata
    if unable to determine the sensor, return 'X'
    """

    senlst = {'Sea-viewing Wide Field-of-view Sensor (SeaWiFS)': 'seawifs',
              'SeaWiFS': 'seawifs',
              'Coastal Zone Color Scanner (CZCS)': 'czcs',
              'Ocean Color and Temperature Scanner (OCTS)': 'octs',
              'Ocean Scanning Multi-Spectral Imager (OSMI)': 'osmi',
              'Ocean   Color   Monitor   OCM-2': 'ocm2',
              'MOS': 'mos', 'VIIRS': 'viirs', 'Aquarius': 'aquarius',
              'hico': 'hico'}


    fileattr = readMetadata(inp_file)
    if not fileattr:
        # sys.stderr.write('empty fileattr found in ' + inp_file + '\n')
        return 'X'
    if 'ASSOCIATEDPLATFORMSHORTNAME' in fileattr:
        print(fileattr['ASSOCIATEDPLATFORMSHORTNAME'])
        return fileattr['ASSOCIATEDPLATFORMSHORTNAME']
    elif 'Instrument_Short_Name' in fileattr:
        return senlst[str(fileattr['Instrument_Short_Name'])]
    elif 'Sensor' in fileattr:
        return senlst[(fileattr['Sensor']).strip()]
    elif 'PRODUCT' in fileattr and re.search('MER', fileattr['PRODUCT']):
        print(fileattr['PRODUCT'])
        return 'meris'
    elif 'instrument' in fileattr:
        print(fileattr['instrument'])
        return senlst[(fileattr['instrument'])].strip()
    else:
        return 'X'
