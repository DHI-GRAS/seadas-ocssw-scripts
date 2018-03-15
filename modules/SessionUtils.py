from __future__ import print_function
import os
import sys
import time
import re
import requests

python2 = sys.version_info.major < 3

# URL parsing utils:

if python2:
    from urlparse import urljoin, urlsplit, urlunsplit
else:  # python 3
    from urllib.parse import urljoin, urlsplit, urlunsplit


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


def thiscall():
    """
    Get function and arguments for caller
    """
    import inspect
    caller = inspect.stack()[1]
    func = eval(caller[3])  # function object
    args = inspect.getargvalues(caller[0])  # frame
    values = [args.locals[arg] for arg in args.args]
    arglist = dict(zip(args.args, values))  # all as keyword args
    return func, arglist


def set_mtime(filepath, mtime):
    """
    Set modification time for specified file.
    Set access time to "now".
    """
    atime = time.time()
    if python2:
        os.utime(filepath, (atime, mtime))
    else:
        os.utime(filepath, times=(atime, mtime))


# URL content parsing utils:

def getlinks_html(content, regex=''):
    from BeautifulSoup import BeautifulSoup, SoupStrainer
    soup = BeautifulSoup(content, parseOnlyThese=SoupStrainer('a'))
    linklist = soup.findAll('a', attrs={'href': re.compile(regex)})
    linklist = [link.get('href') for link in linklist]
    return linklist


def getlinks_json(content, regex=''):
    import json
    parsed_json = json.loads(content)['rows']
    linklist = [str(row[0]) for row in parsed_json]
    if regex != '':
        import re
        regex = re.compile(regex)
        linklist = [link for link in linklist if regex.search(link)]
    return linklist


# requests.Response utils:

def print_response(response):
    if response:
        for key, value in response.headers.items():
            print('{}\t= {}'.format(key, value))
        print(response.status_code, response.reason)


def is_html(response):
    return response and response.ok and ('html' in response.headers['Content-Type'])


def is_json(response):
    return response and response.ok and ('json' in response.headers['Content-Type'])


def url_mtime(response):
    """
    Returns timestamp of remote file as seconds since the epoch.
    """
    try:
        mtime = response.headers['Last-Modified']
        urltime = time.strptime(mtime, "%a, %d %b %Y %H:%M:%S %Z")
        return time.mktime(urltime)
    except Exception as e:
        print('Exception: {:}'.format(e))
        return sys.maxsize


class SessionUtils:

    def __init__(self, timeout=5, max_tries=5, verbose=False, clobber=False):
        self.timeout = timeout
        self.max_tries = max_tries
        self.verbose = verbose
        self.clobber = clobber
        self.session = requests.Session()

    def open_url(self, url, ntries=None, get=False):
        """
        Return requests.Session object for specified url.
        Retries up to self.max_tries times if server is busy.
        By default, retrieves header only.
        """
        if not ntries:
            ntries = self.max_tries
        response = None

        try:
            if get:
                response = self.session.get(url, timeout=self.timeout)
            else:
                response = self.session.head(url, timeout=self.timeout)
            # if self.verbose:
            #     print('{}\t{}\t{}'.format(
            #         response.status_code, url, response.headers['Content-Type']))

            # redirect as needed
            # TODO: get new url back to caller
            loc = response.headers.get('Location')
            if loc:  # response.is_redirect:
                if self.verbose:
                    print('redirected to {}'.format(loc))
                response = self.open_url(self, loc)

            # return response if okay
            if response.ok:
                pass

            # retry if server is busy
            elif (response.status_code > 499) and (ntries > 0):
                if self.verbose:
                    print('Server busy; will retry {}'.format(url))
                response = retry(self.open_url, url, ntries=ntries, get=get)

            # give up if too many tries
            elif ntries == 0:
                print('FAILED after {} tries: {}'.format(ntries, url))

            # give up if bad response
            else:
                print('Bad response for {}'.format(url))
                print_response(response)

        except requests.exceptions.Timeout:
            if ntries > 0:
                if self.verbose:
                    print('Server timeout; will retry {}'.format(url))
                response = retry(self.open_url, url, ntries=ntries, get=get)
                pass

        except Exception as e:
            print('Exception: {:}'.format(e))

        finally:
            return response

    def needs_download(self, url, filepath, check_times=False, response=None):
        """
        Returns False if filepath is present and size matches remote url;
        True otherwise.  Optionally check timestamp as well.
        """

        # only download files
        if is_page(url):
            return False

        if not os.path.isfile(filepath):
            # if self.verbose:
            #     print('Local file not found:', filepath)
            return True

        if not response:
            response = self.open_url(url)
        if not (response and response.ok):
            return False

        # check file size
        diffsize = os.path.getsize(filepath) != int(response.headers['Content-Length'])
        if not check_times:
            return diffsize

        # optionally check timestamp
        else:
            older = os.path.getmtime(filepath) < url_mtime(response)
            return diffsize or older

    def download_file(self, url, filepath):
        try:
            r = self.session.get(url, timeout=self.timeout, stream=True)
            with open(filepath, 'wb') as fd:
                for chunk in r.iter_content(chunk_size=512):
                    fd.write(chunk)
            response = self.open_url(url)
            set_mtime(filepath, url_mtime(response))
        except Exception as e:
            print('Exception: {:}'.format(e))

    def list_pageurls(self, url, regex=''):
        """
        Returns a sorted, unique set of links from a given url.
        Optionally specify regex to filter for acceptable files;
        default is to list only links starting with url.
        """
        response = self.open_url(url, get=True)
        if is_html(response):
            linklist = getlinks_html(response.text, regex)
        elif is_json(response):
            linklist = getlinks_json(response.text, regex)
        else:
            return []

        # get full url
        linklist = [full_url(url, link) for link in linklist]

        # if no filter, return only links containing url
        # TODO: skip original url, and urls ending in "/"
        if regex == '':
            linklist = [link for link in linklist if base_url(url) in link]

        # return sorted, unique list
        return sorted(set(linklist))

    def download_allfiles(self, url, dirpath, regex='', check_times=False,
                          response=None, clobber=False, dry_run=False):
        """
        Downloads all available files from a remote url into a local dirpath.
        Default is to download only if local file doesn't match remote size;
        set clobber=True to always download.
        """
        if not response:
            response = self.open_url(url)
        if not (response and response.ok):
            return []

        downloaded = []
        if dry_run and self.verbose:
            print('Dry run:')
        if not os.path.exists(dirpath) and not dry_run:
            os.makedirs(dirpath)

        for link in self.list_pageurls(url, regex=regex):
            f = os.path.basename(link)
            filepath = os.path.join(dirpath, f)
            if clobber or self.needs_download(
                    link, filepath, check_times=check_times):
                if not dry_run:
                    self.download_file(link, filepath)
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
        try:
            response = self.open_url(url)
            if response.ok:
                if self.verbose:
                    print('{}\t{}\t{}'.
                          format(level, url, response.headers['Content-Type']))
                else:
                    print(url)
                visited.append(url)

                if is_page(url):
                    for link in self.list_pageurls(url):
                        if (base_url(url) in link) and (link not in visited):
                            visited = self.spider(link, level=level + 1,
                                                  visited=visited)
            else:
                print('spider {} {}:\t{}'.
                      format(response.status_code, response.reason, url))

        except Exception as e:
            print('Exception: {:}'.format(e))

        finally:
            return visited

# end of class SessionUtils


if __name__ == '__main__':
    # parameters
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = 'https://oceandata.sci.gsfc.nasa.gov/Ancillary/LUTs/?format=json'

    # logging
    debug = False  # True
    if debug:
        import logging

        logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)

    # init session, run crawler
    s = SessionUtils(verbose=True)
    s.spider(url)
