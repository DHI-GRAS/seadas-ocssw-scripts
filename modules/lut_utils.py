import os
import re
import ProcUtils as ProcUtils


def get_lut_version(lut_name):
    """
    Returns the version part of a LUT, as found in the file name.
    """
    version = ''
    ver_parts = lut_name.split('.')
    if len(ver_parts) > 1:
        ver_fnd = False
        ndx = 0
        while not ver_fnd and ndx < len(ver_parts):
            if ver_parts[ndx][0] == 'V':
                ver_fnd = True
            else:
                ndx += 1
        while ver_fnd and ndx < len(ver_parts):
            for char in ver_parts[ndx]:
                if char.isdigit():
                    version += str(int(char))
                elif char == '_':
                    ver_fnd = False
            ndx += 1
    return version


def compare_lut_names(lut1, lut2):
    """
    Compare two Look Up Table file names and return -1, 0, or 1 respectively
    if the file named in l1 "is less" (i.e. older), equal to, or "greater"
    (newer) than the file named l2.
    """
    ret_val = 0
    lut1_ver = get_lut_version(lut1)
    lut2_ver = get_lut_version(lut2)

    if lut1_ver < lut2_ver:
        return -1
    elif lut1_ver > lut2_ver:
        return 1
    return ret_val


class lut_utils:

    def __init__(self, mission=None, verbose=False,
                 curdir=False, ancdir=None, timeout=10):
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

        self.data_site = "oceandata.sci.gsfc.nasa.gov"
        self.query_site = ''.join(["https://", self.data_site])
        self.data_root = "Ancillary/LUTs"

    def update_aquarius(self):
        """
        update the aquarius luts
        """
        urlConn, proxy = ProcUtils.httpinit(self.data_site, self.timeout)

        if self.verbose: print "[ Aquarius ]"
        # Get most recent version from local disk
        outputdir = os.path.join(self.dirs['var'], 'aquarius')
        listFile = os.path.join(outputdir, "index.html")
        if not os.path.exists(outputdir):
            os.makedirs(outputdir)

        # Get list of remote files and download if necessary
        status = ProcUtils.httpdl(
            self.data_site, "/Ancillary/LUTs/aquarius",
            localpath=outputdir, outputfilename="index.html",
            timeout=self.timeout, reuseConn=True,
            urlConn=urlConn, verbose=self.verbose)
        if status:
            print "Error downloading %s" % '/'.join(
                [self.data_site, "Ancillary/LUTs/aquarius/"])
            self.status = 1

        operlist = ProcUtils.cleanList(listFile)
        ProcUtils.remove(listFile)
        for f in operlist:
            status = ProcUtils.httpdl(
                self.data_site, "/Ancillary/LUTs/aquarius/" + f,
                localpath=outputdir,
                timeout=self.timeout, reuseConn=True,
                urlConn=urlConn, verbose=self.verbose)
            if status:
                print "Error downloading %s" % f
                self.status = 1
            else:
                if self.verbose: print "+ " + f

        urlConn.close()
        if self.verbose: print "[ Done ]\n"

    def update_seawifs(self):
        """
        update the SeaWiFS elements.dat and time_anomaly files
        """
        urlConn, proxy = ProcUtils.httpinit(self.data_site, self.timeout)

        if self.verbose: print "[ SeaWiFS ]"

        # elements.dat
        url = "/Ancillary/LUTs/seawifs/elements.dat"
        outputdir = os.path.join(self.dirs['var'], 'seawifs')
        status = ProcUtils.httpdl(self.data_site, url, localpath=outputdir,
                                  reuseConn=True, urlConn=urlConn,
                                  timeout=self.timeout, verbose=self.verbose)
        if status:
            print "* ERROR: The download failed with status code: " + str(status)
            print "* Please check your network connection and for the existence of the remote file:"
            print "* " + self.data_site + "/Ancillary/LUTs/seawifs/elements.dat"
            self.status = 1
        else:
            if self.verbose: print "+ elements.dat"

        # time_anomaly.txt
        url = "/Ancillary/LUTs/seawifs/time_anomaly.txt"
        outputdir = os.path.join(self.dirs['var'], 'seawifs')
        status = ProcUtils.httpdl(self.data_site, url, localpath=outputdir,
                                  timeout=self.timeout, reuseConn=True,
                                  urlConn=urlConn, verbose=self.verbose)
        if status:
            print "*** ERROR: The download failed with status code: " + str(status)
            print "*** Please check your network connection and for the existence of the remote file:"
            print "* " + self.data_site + "/Ancillary/LUTs/seawifs/time_anomaly.txt"
            self.status = 1
        else:
            if self.verbose: print "+ time_anomaly.txt"

        urlConn.close()
        if self.verbose: print "[ Done ]\n"

    def update_modis_viirsn(self):
        """
        update the calibration LUTs, utcpole.dat and leapsec.dat files
        """
        urlConn, proxy = ProcUtils.httpinit(self.data_site, self.timeout)

        msn = {'aqua': 'modisa', 'terra': 'modist', 'viirsn': 'viirsn'}

        if self.mission in ('aqua', 'terra'):
            if self.verbose:
                print "[ MODIS ]"
            self.instrument = 'modis'
            self.platform = self.mission
            self.sensor = 'modis'

            url = "/Ancillary/LUTs/modis/leapsec.dat"
            outputdir = os.path.join(self.dirs['var'], 'modis')
            status = ProcUtils.httpdl(self.data_site, url, localpath=outputdir,
                                      timeout=self.timeout, reuseConn=True,
                                      urlConn=urlConn, verbose=self.verbose)
            if status:
                print "* ERROR: The download failed with status code: " + str(status)
                print "* Please check your network connection and for the existence of the remote file:"
                print "* " + self.data_site + "/Ancillary/LUTs/modis/leapsec.dat"
                self.status = 1
            else:
                if self.verbose: print "+ leapsec.dat"

            url = "/Ancillary/LUTs/modis/utcpole.dat"
            outputdir = os.path.join(self.dirs['var'], 'modis')
            status = ProcUtils.httpdl(self.data_site, url, localpath=outputdir,
                                      timeout=self.timeout, reuseConn=True,
                                      urlConn=urlConn, verbose=self.verbose)
            if status:
                print "* ERROR: The download failed with status code: " + str(status)
                print "* Please check your network connection and for the existence of the remote file:"
                print "* " + self.data_site + "/Ancillary/LUTs/modis/utcpole.dat"
                self.status = 1
            else:
                if self.verbose: print "+ utcpole.dat"

        if self.mission == 'viirsn':
            if self.verbose:
                print "[ VIIRS ]"
            self.instrument = 'viirs'
            self.platform = 'npp'
            self.sensor = 'viirsn'

            url = "/Ancillary/LUTs/viirsn/IETTime.dat"
            outputdir = os.path.join(self.dirs['var'], 'viirsn')
            status = ProcUtils.httpdl(self.data_site, url, localpath=outputdir,
                                      timeout=self.timeout, reuseConn=True,
                                      urlConn=urlConn, verbose=self.verbose)
            if status:
                print "* ERROR: The download failed with status code: " + str(status)
                print "* Please check your network connection and for the existence of the remote file:"
                print "* " + self.data_site + url
                self.status = 1
            else:
                if self.verbose: print "+ IETTime.dat"

                url = "/Ancillary/LUTs/viirsn/polar_wander.ascii"
            outputdir = os.path.join(self.dirs['var'], 'viirsn')
            status = ProcUtils.httpdl(self.data_site, url, localpath=outputdir,
                                      timeout=self.timeout, reuseConn=True,
                                      urlConn=urlConn, verbose=self.verbose)
            if status:
                print "* ERROR: The download failed with status code: " + str(status)
                print "* Please check your network connection and for the existence of the remote file:"
                print "* " + self.data_site + url
                self.status = 1
            else:
                if self.verbose: print "+ polar_wander.h5"

        if self.verbose:
            print "[ Sensor: %s ]" % self.mission.upper()

        for cal in ('cal', 'xcal'):
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
                self.data_site, "/Ancillary/LUTs/" + msn[self.mission] + "/" + cal + "/OPER",
                localpath=outputdir, outputfilename="index.html",
                timeout=self.timeout, reuseConn=True,
                urlConn=urlConn, verbose=self.verbose)
            if status:
                print "Error downloading %s" % '/'.join(
                    [self.data_site, "Ancillary/LUTs", msn[self.mission], cal, "OPER/"])
                self.status = 1

            parse = re.compile(r"(?<=(\'|\")>)\S+(\.(hdf|h5|nc))")
            operlist = ProcUtils.cleanList(listFile, parse=parse)
            ProcUtils.remove(listFile)

            listsplitstr = 'LUTs.'
            listelem = 1
            listelem2 = 1
            operversion = ''
            operversion2 = ''
            if cal == 'xcal':
                listsplitstr = '_'
                listelem = 2
            if self.mission == 'viirsn' and cal != 'xcal':
                listsplitstr = "SDR-F-LUT_npp_"
                listsplitstr2 = "LUT_v"
                listelem = 1

            for f in operlist:
                if self.mission == 'viirsn' and cal != 'xcal':
                    if f.startswith('VIIRS-SDR-F-LUT_npp_'):
                        operversion = f.split(listsplitstr)[listelem]
                    else:
                        operversion2 = (f.split(listsplitstr2)[listelem2]).split('_')[0]
                else:
                    operversion = f.split(listsplitstr)[listelem]

            # check for version - if different, remove existing files
            for f in luts:
                if f == '.svn':
                    continue

                if f.startswith('SDR-F-LUT_npp_') and f.find(operversion) < 0:
                    # remove files
                    os.remove(os.path.join(self.dirs['var'], msn[self.mission], cal, 'OPER', f))
                    if self.verbose: print "- OPER:" + f

                if f.startswith('VIIRS_NPP_') and f.find(operversion2) < 0:
                    # remove files
                    os.remove(os.path.join(self.dirs['var'], msn[self.mission], cal, 'OPER', f))
                    if self.verbose: print "- OPER:" + f

            # check for existing files, if not there, get 'em!
            for f in operlist:
                if not os.path.exists(os.path.join(outputdir, f)):
                    status = ProcUtils.httpdl(
                        self.data_site,
                        "/Ancillary/LUTs/" + msn[self.mission] + "/" + cal + "/OPER/" + f,
                        localpath=outputdir, timeout=self.timeout,
                        reuseConn=True, urlConn=urlConn, verbose=self.verbose)
                    if status:
                        print "Error downloading %s" % f
                        self.status = 1
                    else:
                        if self.verbose: print "+ OPER:" + f

            # EVAL
            outputdir = os.path.join(self.dirs['var'], msn[self.mission], cal, 'EVAL')
            listFile = os.path.join(outputdir, "index.html")

            status = ProcUtils.httpdl(
                self.data_site, "/Ancillary/LUTs/" + msn[self.mission] + "/" + cal + "/EVAL",
                localpath=outputdir, outputfilename="index.html",
                timeout=self.timeout, reuseConn=True,
                urlConn=urlConn, verbose=self.verbose)
            if status:
                print "Error downloading %s" % '/'.join(
                    [self.data_site, "Ancillary/LUTs", msn[self.mission], cal, "EVAL/"])
                self.status = 1
            evallist = ProcUtils.cleanList(listFile)
            ProcUtils.remove(listFile)

            for f in evallist:
                if not os.path.exists(os.path.join(outputdir, f)):
                    status = ProcUtils.httpdl(
                        self.data_site,
                        "/Ancillary/LUTs/" + msn[self.mission] + "/" + cal + "/EVAL/" + f,
                        localpath=outputdir, timeout=self.timeout,
                        reuseConn=True, urlConn=urlConn, verbose=self.verbose)
                    if status:
                        print "Error downloading %s" % f
                        self.status = 1
                    else:
                        if self.verbose: print "+ EVAL:" + f

        urlConn.close()
        if self.verbose: print "[ Done ]\n"
