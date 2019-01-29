
import os
import sys
import time

from ProcUtils import httpinit, httpdl

# URL parsing utils:

try:
    from urllib.parse import urljoin, urlsplit, urlunsplit  # python 3
except ImportError:
    from urlparse import urljoin, urlsplit, urlunsplit  # python 2

try:
    import http.client as hclient  # python 3
except ImportError:
    import httplib as hclient  # python 2


def base_url(url):
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, None, None))


def full_url(url, link):
    """
    Add query to urljoin() results
    ONLY if it's a page
    """
    base = base_url(urljoin(url, link))
    if not is_page(base):
        return base
    else:
        scheme, netloc, path, query, fragment = urlsplit(base)
        query = urlsplit(url).query
        return urlunsplit((scheme, netloc, path, query, None))


def is_page(url):
    """
    Make the dangerous assumption that URLs
    pointing to another web page always end in '/'.
    """
    return base_url(url).endswith('/')


# General utils:

def retry(func, *args, **kwargs):
    """
    Retry specified function call after a short delay
    """
    from time import sleep
    ntries = kwargs.get('ntries')
    if ntries:
        delay = int(5 + (30. * (1. / (float(ntries) + 1.))))
        if kwargs.get('verbose'):
            print('Sleeping {}s; {} tries left.'.format(delay, ntries - 1))
        sleep(delay)
        kwargs['ntries'] = ntries - 1
    return func(*args, **kwargs)


def set_mtime(filepath, mtime):
    """
    Set modification time for specified file.
    Set access time to "now".
    """
    atime = time.time()
    try:
        os.utime(filepath, times=(atime, mtime))  # python 3
    except TypeError:
        os.utime(filepath, (atime, mtime))  # python 2


# Table/link parsing utils:

def linkdict(rows):
    """
    Each link in list is a dictionary describing a remote file:
    link['href']  = URL pointing to file
    link['mtime'] = timestamp as seconds since the epoch
    link['size']  = size in bytes
"""
    keys = ['href', 'mtime', 'size']
    linklist = []
    for row in rows:
        link = dict(list(zip(keys, row)))
        link['mtime'] = link_mtime(link['mtime'])
        linklist.append(link)
    return linklist


def link_mtime(mtime):
    """
    Format remote file timestamp as seconds since the epoch.
    """
    try:
        urltime = time.strptime(mtime, "%Y-%m-%d %H:%M:%S")
        return time.mktime(urltime)
    except ValueError:
        return sys.maxsize


def getlinks_json(content):
    import json
    return linkdict(json.loads(content)['rows'])


def needs_download(link, filepath, check_times=False):
    """
    Returns False if filepath is present and size matches remote url;
    True otherwise.  Optionally check timestamp as well.
    """

    # only download files
    if is_page(link['href']):
        return False

    # always download missing files
    if not os.path.isfile(filepath):
        return True

    # check file size
    diffsize = os.path.getsize(filepath) != link['size']
    if not check_times:
        return diffsize

    # optionally check timestamp
    else:
        older = os.path.getmtime(filepath) < link['mtime']
        return diffsize or older


# HTTPResponse utils:
def is_json(response):
    return response and ('json' in response.getheader('content-type'))


def ok_status(response):
    return response and (response.status < 400)


class SessionUtils:

    def __init__(self, timeout=5, max_tries=5, verbose=False, clobber=False):
        self.timeout = timeout
        self.max_tries = max_tries
        self.verbose = verbose
        self.clobber = clobber
        self.session = None
        self.status = 0

    def open_url(self, url, ntries=None, get=False):
        """
        Return requests.Session object for specified url.
        Retries up to self.max_tries times if server is busy.
        By default, retrieves header only.
        """
        if not ntries:
            ntries = self.max_tries
        response = None

        parts = urlsplit(url)
        path = urlunsplit(('', '', parts.path, parts.query, ''))

        if not self.session:
            self.session, proxy = httpinit(parts.netloc, timeout=self.timeout)

        try:
            if get:
                self.session.request('GET', path)
            else:
                self.session.request('HEAD', path)
            response = self.session.getresponse()

        except hclient.HTTPException as h:
            self.status = 1
            print('Networking problem: %s: %s' % (h.__class__, str(h)))

        except Exception as e:
            self.status = 1
            print('Exception: {:}'.format(e))

        try:
            # return response if okay
            if ok_status(response):
                pass

            # retry if server is busy
            elif response and (response.status > 499) and (ntries > 0):
                if self.verbose:
                    print('Server busy; will retry {}'.format(url))
                response = retry(self.open_url, url, ntries=ntries, get=get)

            # give up if too many tries
            elif ntries == 0:
                self.status = 1
                print('FAILED after {} tries: {}'.format(ntries, url))

            # give up if bad response
            else:
                self.status = 1
                print('Bad response for {}: {}  {}'.
                      format(url, response.status, response.reason))

        except Exception as e:
            self.status = 1
            print('Exception: {:}'.format(e))

        finally:
            return response

    def download_file(self, url, filepath):
        try:
            parts = urlsplit(url)
            outputdir = os.path.dirname(filepath)
            self.session, status = httpdl(parts.netloc, parts.path,
                                          localpath=outputdir, timeout=self.timeout,
                                          reuseConn=True, urlConn=self.session,
                                          verbose=self.verbose)
            if status:
                self.status = 1
                print('Error downloading {}'.format(filepath))
        except Exception as e:
            self.status = 1
            print('Exception: {:}'.format(e))
        return

    def get_links(self, url, regex=''):
        """
        Returns a unique set of links from a given url.
        Optionally specify regex to filter for acceptable files;
        default is to list only links starting with url.
        """
        response = self.open_url(url, get=True)
        content = response.read()

        if is_json(response):
            linklist = getlinks_json(content)
        else:
            return []

        # make relative urls fully-qualified
        for link in linklist:
            link['href'] = full_url(url, link['href'])

        # filter for regex
        if regex != '':
            import re
            regex = re.compile(regex)
            linklist = [link for link in linklist if regex.search(link['href'])]
        else:  # if no filter, return only links containing url
            linklist = [link for link in linklist if base_url(url) in link['href']]

        return linklist

    def download_allfiles(self, url, dirpath, regex='', check_times=False,
                          clobber=False, dry_run=False):
        """
        Downloads all available files from a remote url into a local dirpath.
        Default is to download only if local file doesn't match remote size;
        set clobber=True to always download.
        """
        downloaded = []
        if dry_run and self.verbose:
            print('Dry run:')
        if not os.path.exists(dirpath) and not dry_run:
            os.makedirs(dirpath)

        all_links = self.get_links(url, regex=regex)
        for link in all_links:
            f = os.path.basename(link['href'])
            filepath = os.path.join(dirpath, f)
            if clobber or needs_download(link, filepath,
                                         check_times=check_times):
                if not dry_run:
                    self.download_file(link['href'], filepath)
                    set_mtime(filepath, link['mtime'])
                    downloaded.append(filepath)
                if self.verbose:
                    print('+ ' + f)

        return downloaded

    def spider(self, url, level=0, visited=None):
        """
        Demo crawler
        """
        if visited is None:
            visited = []

        print('{}\t{}'.format(level, url))
        visited.append(url)

        if is_page(url):
            for link in self.get_links(url):
                link = link['href']
                if (base_url(url) in link) and (link not in visited):
                    visited = self.spider(link, level=level + 1, visited=visited)

        return visited


# end of class SessionUtils


if __name__ == '__main__':
    # parameters
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = 'https://oceandata.sci.gsfc.nasa.gov/Ancillary/LUTs/?format=json'

    # logging
    # debug = False
    debug = True
    if debug:
        import logging

        logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)

    # init session, run crawler
    s = SessionUtils(verbose=True)
    s.spider(url)
