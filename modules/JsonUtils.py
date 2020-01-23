
import os
import sys
import time
import json

from ProcUtils import getSession, httpdl

# URL parsing utils:

try:
    from urllib.parse import urljoin, urlsplit, urlunsplit  # python 3
except ImportError:
    from urlparse import urljoin, urlsplit, urlunsplit  # python 2


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
    ntries = kwargs.get('ntries')
    if ntries:
        delay = int(5 + (30. * (1. / (float(ntries) + 1.))))
        if kwargs.get('verbose'):
            print('Sleeping {}s; {} tries left.'.format(delay, ntries - 1))
        time.sleep(delay)
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
    return response and ('json' in response.headers.get('Content-Type'))


def ok_status(response):
    return response and (response.status < 400)


class SessionUtils:

    def __init__(self, timeout=5, max_tries=5, verbose=0, clobber=False):
        self.timeout = timeout
        self.max_tries = max_tries
        self.verbose = verbose
        self.clobber = clobber
        self.status = 0

    def download_file(self, url, filepath):
        try:
            parts = urlsplit(url)
            outputdir = os.path.dirname(filepath)
            status = httpdl(parts.netloc, parts.path, localpath=outputdir,
                            timeout=self.timeout, ntries=self.max_tries, verbose=self.verbose)
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
        linklist = []
        session = getSession(verbose=self.verbose, ntries=self.max_tries)
        with session.get(url, stream=True, timeout=self.timeout) as response:
            if is_json(response):
                linklist = getlinks_json(response.content)
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

# end of class SessionUtils


if __name__ == '__main__':
    # parameters
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = 'https://oceandata.sci.gsfc.nasa.gov/Ancillary/LUTs/?format=json'

    sessionUtil = SessionUtils()
    links = sessionUtil.get_links(url)
    print(links)

