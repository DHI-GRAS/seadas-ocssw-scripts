"""

SeaDAS library for commonly used functions within other python scripts

"""

def getUrlFileName(openUrl):
    """
    get filename from URL - use content-disposition if provided
    """
    import os
    from urlparse import urlsplit

    if 'Content-Disposition' in openUrl.info():
        # If the response has Content-Disposition, try to get filename from it
        filename = openUrl.info()['Content-Disposition'].split('filename=')[1]
        if filename: return filename
    else:
        # if no filename was found above, parse it out of the final URL.
        return os.path.basename(urlsplit(openUrl.url)[2])


def httpdl(url, localpath='.', outputfilename=None, ntries=5, uncompress=False,
           timeout=10., reqHeaders={}):
    """
    Copy the contents of a file from a given URL to a local file
    Inputs:
        url - URL to retrieve
        localpath - path to place downloaded file
        outputfilename - name to give retreived file (default: URL basename)
        ntries - number to retry attempts
        uncompress - uncompress the downloaded file, if necessary
    """
    global file
    from urllib2 import Request, urlopen, HTTPError, URLError
    import os
    import re
    import shutil
    import socket

    from time import sleep

    sleepytime = 15 + ((30. * (1. / (float(ntries) + 1.))))

    if not os.path.exists(localpath):
        os.umask(002)
        os.makedirs(localpath, mode=02775)

    req = Request(url, headers=reqHeaders)
    status = 0
    response = None
    try:
        response = urlopen(req, timeout=timeout)
    except HTTPError as ehttp:
        if hasattr(ehttp, 'code') and ehttp.code in (400,401,403,404):
            status = ehttp.code
        elif ntries > 0:
            if response:
                response.close()
            print "Connection error, retrying up to %d more time(s)" % ntries
            sleep(sleepytime)
            status = httpdl(url, localpath=localpath, ntries=ntries - 1, timeout=timeout, uncompress=uncompress)
        else:
            print 'We failed to reach a server.'
            print 'Please retry this request at a later time.'

            print 'URL attempted: %s' % url
            if hasattr(ehttp, 'code'):
                print 'HTTP Error code: ', ehttp.code
                status = ehttp.code
            else:
                print 'It is likely that the OBPG limits on access per IP have been exceeded.'
                status = 500

    except URLError as eurl:
        if ntries > 0:
            if response:
                response.close()
            print "Connection error, retrying up to %d more time(s)" % ntries
            sleep(sleepytime)
            status = httpdl(url, localpath=localpath, ntries=ntries - 1, timeout=timeout, uncompress=uncompress)
        else:
            print 'The server could not fulfill the request.'
            print 'URL attempted: %s' % url
            if hasattr(eurl, 'reason'):
                print 'Reason: ', eurl.reason
            else:
                print 'It is likely that the OBPG limits on access per IP have been exceeded.'
            print 'Please retry this request at a later time.'
            status = 500

    except socket.error as socmsg:
        if ntries > 0:
            if response:
                response.close()
            print "Connection error, retrying up to %d more time(s)" % ntries
            sleep(sleepytime)
            status = httpdl(url, localpath=localpath, ntries=ntries - 1, timeout=timeout, uncompress=uncompress)
        else:
            print 'URL attempted: %s' % url
            print 'Well, this is embarrassing...an error occurred that we just cannot get past...'
            print 'Here is what we know: %s' % socmsg
            print 'Please retry this request at a later time.'
            status = 500

    else:
        if response.code == 200 or response.code == 206:
            if outputfilename:
                file = os.path.join(localpath, outputfilename)
            else:
                file = os.path.join(localpath, getUrlFileName(response))

            filename = file
            if response.code == 200:
                with open(file, 'wb') as file:
                    shutil.copyfileobj(response, file)
            else:
                with open(file, 'ab') as file:
                    shutil.copyfileobj(response, file)

            headers = dict(response.info())
            if headers.has_key('content-length'):
                expectedLength = int(response.info()['Content-Length'])
                actualLength = os.stat(filename).st_size
                if expectedLength != actualLength:
                    #continuation - attempt again where it left off...
                    startbyte = actualLength + 1
                    bytestr = "bytes=%s-%s" % (startbyte, expectedLength)
                    reqHeader = {'Range': bytestr}

                    response.close()
                    sleep(sleepytime)
                    status = httpdl(url, localpath=localpath, timeout=timeout, uncompress=uncompress,
                        reqHeaders=reqHeader)
            response.close()

            if re.search(".(Z|gz|bz2)$", filename) and uncompress:
                compressStatus = uncompressFile(filename)
                if compressStatus:
                    status = compressStatus
            else:
                status = 0
        else:
            status = response.code
            response.close()

    return status


def urlFileSearch(url):
    """
    half-baked - don't use :)
    """
    from urllib2 import Request, urlopen, URLError
    import re
    import socket
    from BeautifulSoup import BeautifulSoup

    socket.setdefaulttimeout(10)

    req = Request(url)
    try:
        response = urlopen(req)
        soup = BeautifulSoup(response)
        all = soup.findAll('a', href=re.compile('.*getfile.*'))
        files = []
        for i in all:
            files.append(i.contents[0])
        return files

    except URLError, e:
        if hasattr(e, 'reason'):
            print 'We failed to reach a server.'
            print 'URL attempted: %s' % url
            print 'Reason: ', e.reason
            return 110
        elif hasattr(e, 'code'):
            print 'The server could not fulfill the request.'
            print 'Error code: ', e.code
            return e.code


def uncompressFile(file):
    """
    uncompress file
    compression methods:
        bzip2
        gzip
        UNIX compress
    """
    import os
    import subprocess

    compProg = {"gz": "gunzip -f ", "Z": "gunzip -f ", "bz2": "bunzip2 -f "}
    exten = os.path.basename(file).split('.')[-1]
    unzip = compProg[exten]
    p = subprocess.Popen(unzip + file, shell=True)
    status = os.waitpid(p.pid, 0)[1]
    if status:
        print "Warning! Unable to decompress %s" % file
        return status
    else:
        return 0


def cleanList(file):
    """
    Parses file list from oceandata.sci.gsfc.nasa.gov through html source
    intended for update_luts.py, by may have other uses
    """
    import os
    import re
    import sys

    oldfile = os.path.abspath(file)
    newlist = []
    parse = re.compile(r"(?<=\">)\S+(\.(hdf|h5|dat|txt))")
    if not os.path.exists(oldfile):
        print 'Error: ' + oldfile + ' does not exist'
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
    import datetime

    # define commonly used date formats
    format = {
        'd': "%Y%m%d", # YYYYMMDD
        'j': "%Y%j%H%M%S", # Julian    YYYYDDDHHMMSS
        'g': "%Y%m%d%H%M%S", # Gregorian YYYYMMDDHHMMSS
        't': "%Y-%m-%dT%H:%M:%S.%fZ", # TAI YYYY-MM-DDTHH:MM:SS.uuuuuuZ
        'h': "%Y-%m-%d %H:%M:%S.%f", # HDF-EOS YYYY-MM-DD HH:MM:SS.uuuuuu
    }
    if in_datetype is None:
        dateobj = datetime_i
    else:
        dateobj = datetime.datetime.strptime(datetime_i, format[in_datetype])

    if out_datetype is None:
        return dateobj
    else:
        return dateobj.strftime(format[out_datetype])


def addsecs(datetime_i, dsec, datetype):
    """
    Offset datetime_i by dsec seconds.
    """
    import datetime

    dateobj = date_convert(datetime_i, datetype)
    delta = datetime.timedelta(seconds=dsec)
    return date_convert(dateobj + delta, out_datetype=datetype)


def remove(file):
    """
    Delete a file from the system
    A simple wrapper for os.remove
    """
    import os

    if os.path.exists(file):
        os.remove(file)
        return 0

    return 1


def ctime(file):
    """
    retuns creation time of file
    """
    import datetime
    import os
    import time

    today = datetime.date.today().toordinal()
    utc_create = time.localtime(os.path.getctime(file))

    return today - datetime.date(utc_create.tm_year, utc_create.tm_mon, utc_create.tm_mday).toordinal()


def cat(file):
    """
    Print a file to the standard output.
    """
    f = open(file, 'r')
    while True:
        line = f.readline()
        if not len(line):
            break
        print line,
    f.close()


def check_sensor(file):
    """
    Determine the satellite sensor from the file metadata
    if unable to determine the sensor, return 'X'
    """

    senlst = {'Sea-viewing Wide Field-of-view Sensor (SeaWiFS)': 'seawifs', 'Coastal Zone Color Scanner (CZCS)': 'czcs',
              'Ocean Color and Temperature Scanner (OCTS)': 'octs',
              'Ocean Scanning Multi-Spectral Imager (OSMI)': 'osmi',
              'Ocean   Color   Monitor   OCM-2': 'ocm2',
              'MOS': 'mos', 'VIIRS': 'viirs', 'Aquarius': 'aquarius'}

    from MetaUtils import readMetadata
    import re

    fileattr = readMetadata(file)
    if fileattr.has_key('ASSOCIATEDPLATFORMSHORTNAME'):
        print fileattr['ASSOCIATEDPLATFORMSHORTNAME']
        return fileattr['ASSOCIATEDPLATFORMSHORTNAME']
    elif fileattr.has_key('Instrument_Short_Name'):
        return senlst[str(fileattr['Instrument_Short_Name'])]
    elif fileattr.has_key('Sensor'):
        return senlst[(fileattr['Sensor']).strip()]
    elif fileattr.has_key('PRODUCT') and re.search('MER', fileattr['PRODUCT']):
        print fileattr['PRODUCT']
        return 'meris'
    else:
        return 'X'

     
