from __future__ import print_function

import os

import JsonUtils as Session
import SensorUtils


def lut_version(lut_name):
    import re
    f = os.path.basename(lut_name)

    # lut_name like xcal_<sensor>_<version>_<wavelength>.hdf
    if re.match('xcal', f):
        parts = re.split('([_.])', f)
        return ''.join(parts[4:-4])

    # lut_name like <stuff>[_.][vV]<version>.<suffix>
    v = re.search('[_.][vV]\d+', f)
    if v:
        parts = re.split('([_.])', f[v.start() + 1:])
        return ''.join(parts[0:-2])

    # no version in lut_name
    return None


def any_version(lut_name):
    import re
    d = os.path.dirname(lut_name)
    f = os.path.basename(lut_name)
    v = lut_version(f)
    if v:
        p = re.compile(v)
        return os.path.join(d, p.sub('*', f))
    else:
        return lut_name


def old_version(newfile):
    import glob
    similar = glob.glob(any_version(newfile))
    deletable = [f for f in similar if
                 os.path.getmtime(f) < os.path.getmtime(newfile)]
    return deletable


def purge_luts(newfiles, verbose=False):
    deletable = [old_version(newf) for newf in newfiles]
    # flatten list of lists into single list
    deletable = [oldf for sublist in deletable for oldf in sublist]
    if len(deletable) > 0:
        if verbose:
            print('\n...deleting outdated LUTs:')
        for f in sorted(deletable):
            if verbose:
                print('- ' + os.path.basename(f))
                os.remove(f)


class LutUtils:
    """
    Utilities to update various LUT files for processing
    """

    def __init__(self, mission=None, verbose=False, evalluts=False,
                 timeout=10, clobber=False, dry_run=False):

        self.mission = mission
        self.verbose = verbose
        self.evalluts = evalluts
        self.timeout = timeout
        self.clobber = clobber
        self.dry_run = dry_run
        self.status = 0
        self.site_root = 'https://oceandata.sci.gsfc.nasa.gov/Ancillary/LUTs'
        self.localroot = os.getenv('OCVARROOT')
        self.sensor = SensorUtils.by_desc(mission)

        self.session = Session.SessionUtils(timeout=timeout, clobber=clobber, verbose=verbose)

    def lut_dirs(self):
        dirs = []

        # add instrument dir for MODIS utcpole.dat and leapsec.dat
        if self.sensor['instrument'] == 'MODIS':
            dirs.append(self.sensor['dir'])

        # add unique sensor name
        sensor = self.sensor['sensor'].lower()
        dirs.append(sensor)

        # add calibration dirs for MODIS and VIIRS
        if self.sensor['instrument'] in ['MODIS', 'VIIRS']:
            if sensor  == 'viirsj1':
                caldirs = ['cal']
            else:
                caldirs = ['cal', 'xcal']
            for caldir in caldirs:
                dirs.append(os.path.join(sensor, caldir, 'OPER'))
                if self.evalluts:
                    dirs.append(os.path.join(sensor, caldir, 'EVAL'))

        '''
        # Uncomment this section if we ever reorganize $OCVARROOT to match $OCDATAROOT
        dirs.append(self.sensor['dir'])
        subdir = self.sensor.get('subdir')
        if subdir:
            dirs.append(os.path.join(self.sensor['dir'], subdir))
        '''
        return dirs

    def get_luts(self):

        # regex for all valid suffixes
        # suffix = '\.(hdf|h5|nc|dat|txt)$'
        suffix = ''  # take whatever's there
        query = '?format=json'

        downloaded = []
        for d in self.lut_dirs():
            url = os.path.join(self.site_root, d, '') + query
            dirpath = os.path.join(self.localroot, d)
            if self.verbose:
                print()
                print('Downloading files into ' + dirpath)

            # check times for non-versioned files
            new1 = self.session.download_allfiles(
                url, dirpath,
                dry_run=self.dry_run, clobber=self.clobber,
                regex='^((?!\d+).)*' + suffix, check_times=True)
            if self.session.status:
                self.status = 1

            # check only filesize for others
            new2 = self.session.download_allfiles(
                url, dirpath,
                dry_run=self.dry_run, clobber=self.clobber,
                regex=suffix, check_times=False)
            if self.session.status:
                self.status = 1

            newfiles = new1 + new2
            if len(newfiles) == 0:
                if self.verbose:
                    print('...no new files.')
            else:
                downloaded.append(newfiles)

                # remove outdated LUTs from OPER
                if 'OPER' in d:
                    purge_luts(newfiles, verbose=self.verbose)

        return downloaded

# end of class LutUtils
