import os
import re
from shutil import copyfile
import ProcUtils as ProcUtils

class lut_utils:
    def __init__(self, mission=None, verbose=False, curdir=False, ancdir=None, timeout=10):
        """
        Utilities to update various LUT files for processing
        """

        self.mission = mission
        self.ancdir = ancdir
        self.curdir = curdir

        self.dirs = {}
        self.files = {}
        self.verbose = verbose
        self.status = 0
        self.timeout = timeout

        self.query_site = "http://oceancolor.gsfc.nasa.gov"
        self.data_site = "http://oceandata.sci.gsfc.nasa.gov"


    def update_aquarius(self):
        """
        update the aquarius luts
        """
        if self.verbose: print "[ Aquarius ]"
        # Get most recent version from local disk
        outputdir = os.path.join(self.dirs['var'], 'aquarius')
        listFile = os.path.join(outputdir, "index.html")
        if not os.path.exists(outputdir):
            os.makedirs(outputdir)
#        luts = os.listdir(outputdir)
#        for f in luts:
#            if os.path.isdir(f) or re.search('^\.', f):
#                luts.remove(f)

        # Get remote list of files and download if necessary
        # OPER
        status = ProcUtils.httpdl(
            self.data_site + "/Ancillary/LUTs/aquarius/index.html",
            localpath=outputdir, timeout=self.timeout, verbose=self.verbose)
        if status:
            print "Error downloading %s" % '/'.join(
                [self.data_site, "Ancillary/LUTs/aquarius/"])
            self.status = 1

        operlist = ProcUtils.cleanList(listFile)
        ProcUtils.remove(listFile)
        for f in operlist:
            status = ProcUtils.httpdl(
                self.data_site + "/Ancillary/LUTs/aquarius/" + f,
                localpath=outputdir, timeout=self.timeout, verbose=self.verbose)
            if status:
                print "Error downloading %s" % f
                self.status = 1
            else:
                if self.verbose: print "+ " + f

        if self.verbose: print "[ Done ]\n"


    def update_seawifs(self):
        """
        update the SeaWiFS elements.dat and time_anomaly files
        """
        if self.verbose: print "[ SeaWiFS ]"

        # elements.dat
        url = self.data_site + "/Ancillary/LUTs/seawifs/elements.dat"
        outputdir = os.path.join(self.dirs['var'], 'seawifs')
        status = ProcUtils.httpdl(url, localpath=outputdir, timeout=self.timeout,verbose=self.verbose)
        if status:
            print "* ERROR: The download failed with status code: " + str(status)
            print "* Please check your network connection and for the existence of the remote file:"
            print "* " + self.data_site + "/Ancillary/LUTs/seawifs/elements.dat"
            self.status = 1
        else:
            if self.verbose: print "+ elements.dat"

        # time_anomaly.txt
        url = self.data_site + "/Ancillary/LUTs/seawifs/time_anomaly.txt"
        outputdir = os.path.join(self.dirs['var'], 'seawifs')
        status = ProcUtils.httpdl(url, localpath=outputdir, timeout=self.timeout,verbose=self.verbose)
        if status:
            print "*** ERROR: The download failed with status code: " + str(status)
            print "*** Please check your network connection and for the existence of the remote file:"
            print "* " + self.data_site + "/Ancillary/LUTs/seawifs/time_anomaly.txt"
            self.status = 1
        else:
            if self.verbose: print "+ time_anomaly.txt"

        if self.verbose: print "[ Done ]\n"


    def update_modis_viirsn(self):
        """
        update the calibration LUTs, utcpole.dat and leapsec.dat files
        """

        msn = {'aqua': 'modisa', 'terra': 'modist', 'viirsn': 'viirsn'}

        if self.mission in ('aqua','terra'):

            if self.verbose:
                print "[ MODIS ]"

            url = self.data_site + "/Ancillary/LUTs/modis/leapsec.dat"
            outputdir = os.path.join(self.dirs['var'], 'modis')
            status = ProcUtils.httpdl(url, localpath=outputdir, timeout=self.timeout,verbose=self.verbose)
            if status:
                print "* ERROR: The download failed with status code: " + str(status)
                print "* Please check your network connection and for the existence of the remote file:"
                print "* " + self.data_site + "/Ancillary/LUTs/modis/leapsec.dat"
                self.status = 1
            else:
                if self.verbose: print "+ leapsec.dat"

            url = self.data_site + "/Ancillary/LUTs/modis/utcpole.dat"
            outputdir = os.path.join(self.dirs['var'], 'modis')
            status = ProcUtils.httpdl(url, localpath=outputdir, timeout=self.timeout,verbose=self.verbose)
            if status:
                print "* ERROR: The download failed with status code: " + str(status)
                print "* Please check your network connection and for the existence of the remote file:"
                print "* " + self.data_site + "/Ancillary/LUTs/modis/utcpole.dat"
                self.status = 1
            else:
                if self.verbose: print "+ utcpole.dat"

        if self.verbose:
            print "[ MODIS: %s ]" % self.mission.upper()

        for cal in ('cal', 'xcal'):
            if self.mission == 'viirsn' and cal == 'xcal':
                continue
            # Get most recent version from local disk
            outputdir = os.path.join(self.dirs['var'], msn[self.mission], cal, 'OPER')
            listFile = os.path.join(outputdir, "index.html")
            if not os.path.exists(outputdir):
                os.makedirs(outputdir)
            luts = os.listdir(outputdir)
            for f in luts:
                if os.path.isdir(f) or re.search('^\.', f):
                    luts.remove(f)

            # Get remote list of files and download if necessary
            # OPER
            status = ProcUtils.httpdl(
                self.data_site + "/Ancillary/LUTs/" + msn[self.mission] + "/" + cal + "/OPER/index.html",
                localpath=outputdir, timeout=self.timeout, verbose=self.verbose)
            if status:
                print "Error downloading %s" % '/'.join(
                    [self.data_site, "Ancillary/LUTs", msn[self.mission], cal, "OPER/"])
                self.status = 1

            parse = re.compile(r"(?<=\">)\S+(\.(hdf|h5))")
            operlist = ProcUtils.cleanList(listFile,parse=parse)
            ProcUtils.remove(listFile)

            listsplitstr = 'LUTs.'
            listelem = 1
            if cal == 'xcal':
                listsplitstr = '_'
                listelem = 2
            if self.mission == 'viirsn':
                listsplitstr = "SDR-F-LUT_npp_"
                listelem = 1
            operversion = operlist[0].split(listsplitstr)[listelem]

            #check for version - if different, remove existing files
            for f in luts:
                if f == '.svn':
                    continue
                if f.find(operversion) < 0:
                    # remove files
                    os.remove(os.path.join(self.dirs['var'], msn[self.mission], cal, 'OPER', f))
                    if self.verbose: print "- OPER:" + f


                # modify msl12_defaults.par
                if self.mission in ('aqua','terra') and cal == 'xcal':
                    do_modify = True
                    msl12_defaults = os.path.join(self.dirs['root'], msn[self.mission] ,'msl12_defaults.par')
                    if operversion in open(msl12_defaults).read():
                        do_modify = False

                    if do_modify:
                        mod_defaults = msl12_defaults + '.new'
                        defaults = [line for line in open(msl12_defaults, 'r')]
                        mod = open(mod_defaults, 'w')
                        for line in defaults:
                            if 'xcalfile=' in line:
                                xcalfile = '_'.join(['xcal',msn[self.mission],operversion])
                                xcalfilepath = os.path.join('$OCVARROOT', msn[self.mission] ,cal,'OPER',xcalfile)
                                line = "xcalfile=%s\n" % xcalfilepath
                            mod.write(line)
                        mod.close()
                        copyfile(mod_defaults, msl12_defaults)
                        os.remove(mod_defaults)
                        # Hires
                        msl12_defaults = os.path.join(self.dirs['root'], 'h'+msn[self.mission] ,'msl12_defaults.par')
                        mod_defaults = msl12_defaults + '.new'
                        defaults = [line for line in open(msl12_defaults, 'r')]
                        mod = open(mod_defaults, 'w')
                        for line in defaults:
                            if 'xcalfile=' in line:
                                xcalfile = '_'.join(['xcal',msn[self.mission],operversion])
                                xcalfilepath = os.path.join('$OCVARROOT', msn[self.mission] ,cal,'OPER',xcalfile)
                                line = "xcalfile=%s\n" % xcalfilepath
                            mod.write(line)
                        mod.close()
                        copyfile(mod_defaults, msl12_defaults)
                        os.remove(mod_defaults)


            #check for existing files, if not there, get 'em!
            for f in operlist:
                if not os.path.exists(os.path.join(outputdir, f)):
                    status = ProcUtils.httpdl(
                        self.data_site + "/Ancillary/LUTs/" + msn[self.mission] + "/" + cal + "/OPER/" + f,
                        localpath=outputdir, timeout=self.timeout, verbose=self.verbose)
                    if status:
                        print "Error downloading %s" % f
                        self.status = 1
                    else:
                        if self.verbose: print "+ OPER:" + f


            # EVAL
            outputdir = os.path.join(self.dirs['var'], msn[self.mission], cal, 'EVAL')
            listFile = os.path.join(outputdir, "index.html")

            status = ProcUtils.httpdl(
                self.data_site + "/Ancillary/LUTs/" + msn[self.mission] + "/" + cal + "/EVAL/index.html",
                localpath=outputdir, timeout=self.timeout, verbose=self.verbose)
            if status:
                print "Error downloading %s" % '/'.join(
                    [self.data_site, "Ancillary/LUTs", msn[self.mission], cal, "EVAL/"])
                self.status = 1
            evallist = ProcUtils.cleanList(listFile)
            ProcUtils.remove(listFile)

            for f in evallist:
                if not os.path.exists(os.path.join(outputdir, f)):
                    status = ProcUtils.httpdl(
                        self.data_site + "/Ancillary/LUTs/" + msn[self.mission] + "/" + cal + "/EVAL/" + f,
                        localpath=outputdir, timeout=self.timeout, verbose=self.verbose)
                    if status:
                        print "Error downloading %s" % f
                        self.status = 1
                    else:
                        if self.verbose: print "+ EVAL:" + f

        if self.verbose: print "[ Done ]\n"
