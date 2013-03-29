#! /usr/bin/env python

import ProcUtils
from modules.ParamUtils import ParamProcessing

class modis_geo:
    
    def __init__(self,file=file,
                 parfile=None,
                 geofile=None,
                 a1=None,a2=None,
                 e1=None,e2=None,
                 download=True,
                 entrained=False,
                 terrain=False,
                 geothresh=95,
                 sensor=None,
                 anc_file=None,
                 ancdir=None,
                 ancdb='ancillary_data.db',
                 refreshDB=False,
                 lutver=None,
                 lutdir=None,
                 log=False,
                 verbose=False):


        # defaults
        self.file = file
        self.parfile = parfile
        self.geofile = geofile
        self.ancdir = ancdir
        self.ancdb = ancdb
        self.refreshDB = refreshDB
        self.a1 = a1
        self.a2 = a2
        self.e1 = e1
        self.e2 = e2
        self.download = download
        self.entrained = entrained
        self.terrain = terrain
        self.geothresh = geothresh
        self.lutversion = lutver
        self.lutdir = lutdir
        self.log = log
        self.proctype = 'modisGEO'
        self.curdir = False
        self.pcf_file = None
        self.verbose = verbose
        self.dirs = {}
        self.sensor = sensor
        self.sat_name = None
        self.start = None
        self.stop = None
        self.anc_file = anc_file

        # version-specific variables
        self.collection_id = '005'
        self.pgeversion = '5.0.52'
        self.lutversion = '13'

        if self.parfile:
            print self.parfile
            p=ParamProcessing(parfile=self.parfile)
            p.parseParFile(prog='geogen')
            print p.params
            phash = p.params['geogen']
            for param in (phash.keys()):
                print phash[param]
                if not self[param]:
                    self[param] = phash[param]

    def __setitem__(self, index, item):
        self.__dict__[index] = item

    def __getitem__(self,index):
        return self.__dict__[index]

    def chk(self):
        """
        Check parameters
        """
        import os
        import sys
        
        if self.file is None:
            print "ERROR: No MODIS_L1A_file was specified in either the parameter file or in the argument list. Exiting"
            sys.exit(1)
        if not os.path.exists(self.file):
            print "ERROR: File '" + self.file + "' does not exist. Exiting."
            sys.exit(1)
        if self.a1 is not None and not os.path.exists(self.a1):
            print "ERROR: Attitude file '" + self.a1 + "' does not exist. Exiting."
            sys.exit(1)
        if self.a2 is not None and not os.path.exists(self.a2):
            print "ERROR: Attitude file '" + self.a2 + "' does not exist. Exiting."
            sys.exit(99)
        if self.e1 is not None and not os.path.exists(self.e1):
            print "ERROR: Ephemeris file '" + self.e1 + "' does not exist. Exiting."
            sys.exit(1)
        if self.e2 is not None and not os.path.exists(self.e2):
            print "ERROR: Ephemeris file '" + self.e2 + "' does not exist. Exiting."
            sys.exit(1)
        if self.a1 is None and self.e1 is not None or self.a1 is not None and self.e1 is None:
            print "ERROR: User must specify attitude AND ephemeris files."
            print "       Attitude/ephemeris files must ALL be specified or NONE specified. Exiting."
            sys.exit(1)
        if self.terrain is True and not os.path.exists(self.dirs['dem']):
            print "WARNING: Could not locate MODIS digital elevation maps directory:"
            print "         '" + self.dirs['dem'] + "/'."
            print ""
            print "*TERRAIN CORRECTION DISABLED*"
            self.terrain = False

    def utcleap(self):
        """
        Check date of utcpole.dat and leapsec.dat. Download if older than 14 days.
        """
        import os
        from ProcUtils import ctime
        import lut_utils as lu
        from setupenv import env
        l=lu.lut_utils(verbose=self.verbose,mission=self.sat_name)
        #quiet down a bit...
        resetVerbose=0
        if l.verbose:
            resetVerbose=1
            l.verbose=False

        env(l)
        if resetVerbose:
            l.verbose=True
        
        if not os.path.exists(os.path.join(self.dirs['var'],"modis", "utcpole.dat")) \
            or not os.path.exists(os.path.join(self.dirs['var'],"modis", "leapsec.dat")):
                if self.verbose:
                    print "** Files utcpole.dat/leapsec.dat are not present on hard disk."
                    print "** Running update_luts.py to download the missing files..."
                l.update_modis_viirsn()
        else:
            utc_age = ctime(os.path.join(self.dirs['var'],"modis", "utcpole.dat"))
            leap_age = ctime(os.path.join(self.dirs['var'],"modis", "leapsec.dat"))
            if leap_age > 14 or utc_age > 14:
                if self.verbose:
                    print "** Files utcpole.dat/leapsec.dat are more than 2w old"
                    print "** Running update_luts to update files..."
                l.update_modis_viirsn()
            
    
    def atteph(self):
        """
        Determine and retrieve required ATTEPH files
        """
        import os
        import sys
        import anc_utils as ga
        from setupenv import env

        
        # Check for user specified atteph files
        if self.a1 is not None:
            self.atteph_type = "user_provided"
            self.kinematic_state = "SDP Toolkit"
            self.attfile1 = os.path.basename(self.a1)
            self.attdir1 = os.path.abspath(os.path.dirname(self.a1))
            self.ephfile1 = os.path.basename(self.e1)
            self.ephdir1 = os.path.abspath(os.path.dirname(self.e1))
            
            if self.a2 is not None:
                self.attfile2 = os.path.basename(self.a2)
                self.attdir2 = os.path.abspath(os.path.dirname(self.a2))
            else:
                self.attfile2 = "NULL"
                self.attdir2 = "NULL"
            
            if self.e2 is not None:
                self.ephfile2 = os.path.basename(self.e2)
                self.ephdir2 = os.path.abspath(os.path.dirname(self.e2))
            else:
                self.ephfile2 = "NULL"
                self.ephdir2 = "NULL"
            
            if self.verbose:
                print "Using specified attitude and ephemeris files."
                print ""
                print "att_file1:", os.path.join(self.attdir1, self.attfile1)
                if self.attfile2 == "NULL":
                    print "att_file2: NULL"
                else:
                    print "att_file2:", os.path.join(self.attdir2, self.attfile2)
                print "eph_file1:", os.path.join(self.ephdir1, self.ephfile1)
                if self.ephfile2 == "NULL":
                    print "eph_file2: NULL"
                else:
                    print "eph_file2:", os.path.join(self.ephdir2, self.ephfile2)
        else:
            if self.verbose:
                print "Determining required attitude and ephemeris files..."
            get = ga.getanc(file=self.file,
                atteph=True,
                ancdb=self.ancdb,
                ancdir=self.ancdir,
                refreshDB=self.refreshDB,
                sensor=self.sensor,
                start=self.start,
                stop=self.stop,
                download=self.download,
                verbose=self.verbose)

            #quiet down a bit...
            resetVerbose=0
            if get.verbose:
                resetVerbose=1
                get.verbose=False

            env(get)
            if resetVerbose:
                get.verbose=True
            get.chk()
            if file and get.finddb():
                get.setup()
            else:
                get.setup()
                get.findweb()

            get.locate()
            get.cleanup()

            
            self.db_status = get.db_status
            # DB return status bitwise values:
            # 0 - all is well in the world
            # 1 - predicted attitude selected
            # 2 - predicted ephemeris selected
            # 4 - no attitude found
            # 8 - no ephemeris found
            # 16 - invalid mission
            if self.sat_name == "terra" and self.db_status & 15:
                self.kinematic_state = "MODIS Packet"
                self.attfile1 = "NULL"
                self.attdir1 = "NULL"
                self.attfile2 = "NULL"
                self.attdir2 = "NULL"
                self.ephfile1 = "NULL"
                self.ephdir1 = "NULL"
                self.ephfile2 = "NULL"
                self.ephdir2 = "NULL"
            elif self.db_status & 12:
                if self.verbose:
                    if self.db_status & 4:
                        print "Missing attitude files!"
                    if self.db_status & 8:
                        print "Missing ephemeris files!"
                    print "Cannot continue processing....exiting..."

                    sys.exit(31)
            else:
                self.kinematic_state = "SDP Toolkit"
                if get.files.has_key('att1'):
                    self.attfile1 = os.path.basename(get.files['att1'])
                    self.attdir1  = os.path.dirname(get.files['att1'])
                else:
                    print "Missing attitude files!"
                    sys.exit(31)
                if get.files.has_key('eph1'):
                    self.ephfile1 = os.path.basename(get.files['eph1'])
                    self.ephdir1  = os.path.dirname(get.files['eph1'])
                else:
                    print "Missing ephemeris files!"
                    sys.exit(31)
                if get.files.has_key('att2'):
                    self.attfile2 = os.path.basename(get.files['att2'])
                    self.attdir2 = os.path.dirname(get.files['att2'])
                else:
                    self.attfile2 = "NULL"
                    self.attdir2 = "NULL"
                if get.files.has_key('eph2'):
                    self.ephfile2 = os.path.basename(get.files['eph2'])
                    self.ephdir2 = os.path.dirname(get.files['eph2'])
                else:
                    self.ephfile2 = "NULL"
                    self.ephdir2 = "NULL"

    def geochk(self):
        """Examine a MODIS geolocation file for percent missing data
        Returns an error if percent is greater than a threshold"""

        import os
        import sys
        from modules.MetaUtils import readMetadata

        thresh = float(self.geothresh)
        if not os.path.exists(self.geofile):
            print "*** ERROR: geogen_modis failed to produce a geolocation file."
            print "*** Validation test failed for geolocation file:", os.path.basename(self.geofile)
            sys.exit(1)

        metadata = readMetadata(self.geofile)
        if metadata:
            if 'QAPERCENTMISSINGDATA' in metadata:
                pctmissing = metadata['QAPERCENTMISSINGDATA']
                if pctmissing is not None:
                    pctvalid = 100 - pctmissing
                    if pctvalid < thresh:
                        print "Percent valid data (%.2f) is less than threshold (%.2f)" % (pctvalid,thresh)
                        sys.exit(1)
                    else:
                        if self.verbose:
                            print "Percentage of pixels with missing geolocation: %.2f" % pctmissing
                            print "Validation test passed for geolocation file %s" % self.geofile
                        sys.exit(0)
            else:
                print "Problem reading geolocation file: %s" % self.geofile
                sys.exit(2)
        else:
            print "Problem reading geolocation file: %s" % self.geofile
            sys.exit(2)

    def run(self):
        """
        Run geogen_modis (MOD_PR03)
        """
        import subprocess
        import os

        if self.verbose:
            print ""
            print "Creating MODIS geolocation file..."
        geogen = os.path.join(self.dirs['bin'],'geogen_modis')
        status = subprocess.call(geogen, shell=True)
        if self.verbose:
            if status:
                print "geogen_modis returned with exit status: " + str(status)
                print "Will run modis_geocheck to confirm results..."
            else:
                print "geogen_modis created %s successfully!" % self.geofile

        if status:
            if self.verbose:
                print ""
                print "Running validation test on geolocation file.."
            chkstatus = self.geochk()
            if chkstatus:
                print "ERROR: MODIS geolocation processing failed."
                self.log = True
            else:
                if self.verbose: print "MODIS geolocation processing complete."

        ProcUtils.remove(os.path.join(self.dirs['run'], "GetAttr.temp"))
        ProcUtils.remove(os.path.join(self.dirs['run'], "ShmMem"))
        ProcUtils.remove('.'.join([self.file, 'met']))
        ProcUtils.remove('.'.join([self.geofile, 'met']))
        if self.log is False:
            ProcUtils.remove(self.pcf_file)
            base = os.path.basename(self.geofile)
            ProcUtils.remove(os.path.join(self.dirs['run'],('.'.join(['LogReport', base]))))
            ProcUtils.remove(os.path.join(self.dirs['run'],('.'.join(['LogStatus', base]))))
            ProcUtils.remove(os.path.join(self.dirs['run'],('.'.join(['LogUser', base]))))
