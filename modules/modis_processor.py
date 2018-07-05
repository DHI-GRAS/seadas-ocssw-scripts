
"""
Class for handling the processing of MODIS data files.
"""

import modis_L1A_utils
import ProcUtils
import os
import subprocess
import sys

__author__ = 'melliott'

class ModisProcessor():
    """
    A class for doing MODIS Processing
    """
    def __init__(self, l0_name, l1a=None, geo=None):
        self.ocssw_root = os.getenv('OCSSWROOT')
        self.l0_file = l0_name
        if l1a is not None:
            self.l1a = l1a
        else:
            self.l1a = self.derive_l1a_basename() + '.L1A_LAC'
        if geo is not None:
            self.geo = l1a
        else:
            self.geo = self.derive_l1a_basename() + '.GEO'

    def derive_l1a_basename(self):
        """
        Determine what the default basename for the L1A file (and GEO file) should be.
        """
        create_constructor_cmd = ''.join(['l0cnst_write_modis ',
                                          self.l0_file, ' > ', 'granules.tmp'])
        print('Running: ', create_constructor_cmd)
        try:
            status = subprocess.call(create_constructor_cmd, shell=True)
            print(status)
            if status != 0:
                print('Error! Could not run l0const')
                sys.exit(41)
            else:
                print('l0cnst_write_modis run compleat')
        except OSError as ose:
            print(ose.errno, ose.strerror)
        with open('granules.tmp') as gran_file:
            lines = gran_file.readlines()
        starttime = None
        for line in lines:
            print('processing: ', line)
            fields = line.split('=')
            if fields[0].strip() == 'starttime':
                starttime = fields[1].strip()
                break
        if starttime is None:
            print('Error!  Could not determine start time.')
            sys.exit(42)
        os.remove('granules.tmp')
        granule_time = ProcUtils.date_convert(starttime, 't', 'j')
        return ''.join(['A', granule_time])

    def run_modis_geo(self, out_file=''):
        """
        Do the MODIS Geonavigation processing.
        """
        geo_cmd = os.path.join(self.ocssw_root, 'run/scripts', 'modis_GEO.py') \
                               + ' ' + self.l1a
        if out_file != '':
            geo_cmd += ' -o ' + out_file
        ret_val = subprocess.call(geo_cmd, shell=True)
        return ret_val

    def run_modis_l1a(self, out_file=''):
        """
        Do the MODIS L1A processing.
        """
        l1a_cmd = os.path.join(self.ocssw_root, 'run/scripts', 'modis_L1A.py')
        l1a_cmd +=  ' -v '
        l1a_cmd +=  ' ' + self.l0_file
        if out_file != '':
            l1a_cmd += ' -o ' + out_file
        ret_val = subprocess.call(l1a_cmd, shell=True)
        return ret_val

    def run_modis_l1b(self):
        """
        Do the MODIS L1B processing.
        """
        l1b_cmd = os.path.join(self.ocssw_root, 'run/scripts', 'modis_L1B.py') \
                  + ' ' + self.l1a
        ret_val = subprocess.call(l1b_cmd, shell=True)
        return ret_val
