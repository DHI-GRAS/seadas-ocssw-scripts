"""

SeaDAS library for commonly used functions within other python scripts

"""
from __future__ import print_function

import sys


def get_url_file_name(openUrl, request):
    """
    get filename from URL - use content-disposition if provided
    """
    import os

    # If the response has Content-Disposition, try to get filename from it
    filename = openUrl.getheader('content-disposition')
    if filename:
        return filename.split('filename=')[1]
    else:
        # if no filename was found above, parse it out of the final URL.
        return os.path.basename(request)


def httpinit(url, timeout=10, urlConn=None):
    """
    initialize HTTP network connection
    """
    import os
    try:
        import http.client as hclient  # python 3
    except ImportError:
        import httplib as hclient  # python 2

    try:
        from urllib.parse import urlparse
    except ImportError:
        from urlparse import urlparse
        
    proxy = None
    proxy_set = os.environ.get('https_proxy')
    if proxy_set is None:
        proxy_set = os.environ.get('http_proxy')
    if proxy_set:
        proxy = urlparse(proxy_set)

    if urlConn is None:
        if proxy is None:
            urlConn = hclient.HTTPSConnection(url, timeout=timeout)
        elif proxy.scheme == 'https':
            urlConn = hclient.HTTPSConnection(proxy.hostname,
                                              proxy.port, timeout=timeout)
        else:
            urlConn = hclient.HTTPConnection(proxy.hostname,
                                             proxy.port, timeout=timeout)

    return urlConn, proxy


def _httpdl(url, request, localpath='.', outputfilename=None, ntries=5,
            uncompress=False, timeout=30., reqHeaders={}, verbose=False,
            reuseConn=False, urlConn=None):
    """
    Copy the contents of a file from a given URL to a local file
    Inputs:
        url - URL to retrieve
        localpath - path to place downloaded file
        outputfilename - name to give retrieved file (default: URL basename)
        ntries - number to retry attempts
        uncompress - uncompress the downloaded file, if necessary (boolean, default False)
        timeout - sets the connection timeout (seconds)
        reqHeaders - hash containing URL headers
        reuseConn - reuse existing connection (boolean, default False)
        urlConn - existing httplib.connection (needed if reuseConn set, default None)
        verbose - get chatty about connection issues (boolean, default False)
    """
    global ofile
    import os
    import re
    import socket

    from time import sleep

    sleepytime = int(5 + ((30. * (1. / (float(ntries) + 1.)))))

    if not os.path.exists(localpath):
        os.umask(0o02)
        os.makedirs(localpath, mode=0o2775)

    urlConn, proxy = httpinit(url, timeout=timeout, urlConn=urlConn)

    if proxy is None:
        full_request = request
    else:
        full_request = ''.join(['https://', url, request])

    try:
        req = urlConn.request('GET', full_request, headers=reqHeaders)
    except:
        err_msg = '\n'.join(['Error! could not establish a network connection. Check your network connection.',
                             'If you do not find a problem, please try again later.'])
        sys.exit(err_msg)

    status = 0
    response = None
    try:
        response = urlConn.getresponse()

        if response.status in (400, 401, 403, 404, 416):
            status = response.status
        elif response.status not in (200, 206):
            urlConn.close()
            if ntries > 0:
                if verbose:
                    print("Connection interrupted, retrying up to %d more time(s)" % ntries)
                sleep(sleepytime)
                urlConn, status = _httpdl(url, request, localpath=localpath,
                                          outputfilename=outputfilename,
                                          ntries=ntries - 1, timeout=timeout,
                                          uncompress=uncompress, reuseConn=reuseConn,
                                          urlConn=None, verbose=verbose)
            else:
                print('We failed to reach a server.')
                print('Please retry this request at a later time.')
                print('URL attempted: %s' % url)
                print('HTTP Error: {0} - {1}'.format(response.status,
                                                     response.reason))
                status = response.status
                urlConn = None

    except socket.error as socmsg:
        if response:
            urlConn.close()
        if ntries > 0:
            if verbose:
                print('Connection error, retrying up to {0} more time(s)'. \
                    format(ntries))
            sleep(sleepytime)
            urlConn, status = _httpdl(url, request, localpath=localpath,
                                      outputfilename=outputfilename, ntries=ntries - 1,
                                      timeout=timeout, uncompress=uncompress,
                                      reuseConn=reuseConn, urlConn=None, verbose=verbose)
        else:
            print('URL attempted: %s' % url)
            print('Well, this is embarrassing...an error occurred that we just cannot get past...')
            print('Here is what we know: %s' % socmsg)
            print('Please retry this request at a later time.')
            status = 500
            urlConn = None
    except:
        if response:
            print('Well, the server did not like this...reports: {0}'. \
                format(response.reason))
            status = response.status
        else:
            err_msg = '\n'.join(['Could not communicate with the server.',
                                 'Please check your network connections and try again later.'])
            sys.exit(err_msg)
    else:
        if response.status == 200 or response.status == 206:
            if outputfilename:
                ofile = os.path.join(localpath, outputfilename)
            else:
                ofile = os.path.join(localpath, get_url_file_name(response,
                                                                  request))
            filename = ofile
            data = response.read()

            if response.status == 200:
                with open(ofile, 'wb') as f:
                    f.write(data)
            else:
                with open(ofile, 'ab') as f:
                    f.write(data)

            headers = dict(response.getheaders())
            if 'content-length' in headers:
                expectedLength = int(headers.get('content-length'))
                if 'content-range' in headers:
                    expectedLength = int(headers.get('content-range').split('/')[1])

                actualLength = os.stat(filename).st_size

                if expectedLength != actualLength:
                    # continuation - attempt again where it left off...
                    bytestr = "bytes=%s-" % (actualLength)
                    reqHeader = {'Range': bytestr}
                    print(bytestr, sleepytime)
                    urlConn.close()
                    sleep(sleepytime)
                    urlConn, status = _httpdl(url, request, localpath=localpath,
                                              outputfilename=outputfilename,
                                              timeout=timeout, uncompress=uncompress,
                                              reqHeaders=reqHeader, reuseConn=reuseConn,
                                              urlConn=None, verbose=verbose)

            if not reuseConn:
                urlConn.close()

            if re.search(".(Z|gz|bz2)$", filename) and uncompress:
                compressStatus = uncompressFile(filename)
                if compressStatus:
                    status = compressStatus
            else:
                status = 0
        else:
            status = response.status
            if not reuseConn:
                urlConn.close()

    return (urlConn, status)


def httpdl(url, request, localpath='.', outputfilename=None, ntries=5,
           uncompress=False, timeout=30., reqHeaders={}, verbose=False,
           reuseConn=False, urlConn=None):
    urlConn, status = _httpdl(url, request, localpath, outputfilename, ntries,
                              uncompress, timeout, reqHeaders, verbose,
                              reuseConn, urlConn)
    if reuseConn:
        return (urlConn, status)
    else:
        return status


def uncompressFile(compressed_file):
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
    import os
    import re

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
    import datetime

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


def addsecs(datetime_i, dsec, datetype):
    """
    Offset datetime_i by dsec seconds.
    """
    import datetime

    dateobj = date_convert(datetime_i, datetype)
    delta = datetime.timedelta(seconds=dsec)
    return date_convert(dateobj + delta, out_datetype=datetype)


def remove(file_to_delete):
    """
    Delete a file from the system
    A simple wrapper for os.remove
    """
    import os

    if os.path.exists(file_to_delete):
        os.remove(file_to_delete)
        return 0

    return 1


def ctime(the_file):
    """
    returns days since file creation
    """
    import datetime
    import os
    import time

    today = datetime.date.today().toordinal()
    utc_create = time.localtime(os.path.getctime(the_file))

    return today - datetime.date(utc_create.tm_year, utc_create.tm_mon, utc_create.tm_mday).toordinal()


def mtime(the_file):
    """
    returns days since last file modification
    """
    import datetime
    import os
    import time

    today = datetime.date.today().toordinal()
    utc_mtime = time.localtime(os.path.getmtime(the_file))

    return today - datetime.date(utc_mtime.tm_year, utc_mtime.tm_mon, utc_mtime.tm_mday).toordinal()


def cat(file_to_print):
    """
    Print a file to the standard output.
    """
    f = open(file_to_print, 'r')
    while True:
        line = f.readline()
        if not len(line):
            break
        print(line, end=' ')
    f.close()


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

    from modules.MetaUtils import readMetadata
    import re

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
