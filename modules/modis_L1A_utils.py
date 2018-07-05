#! /usr/bin/env python

import os
import sys
from modules.ParamUtils import ParamProcessing


class modis_l1a:
    """
    This class defines the parameters and sets up the environment necessary
    to process a MODIS L0 granule to produce a L1A granule.  It is implemented
    by the modis_L1A code.  This class also contains the methods necessary to
    run the l0_write_construct and l1agen_modis binaries.
    """

    def __init__(self, file=None,
                 parfile=None,
                 l1a=None,
                 nextgranule=None,
                 startnudge=10,
                 stopnudge=10,
                 satellite=None,
                 fix=True,
                 lutver=None,
                 lutdir=None,
                 log=False,
                 verbose=True):
        self.file = file
        self.parfile = parfile
        self.l1a = l1a
        self.proctype = 'modisL1A'
        self.nextgranule = nextgranule
        self.stopnudge = stopnudge
        self.startnudge = startnudge
        self.sat_name = satellite
        self.verbose = verbose
        self.fix = fix
        self.lutversion = lutver
        self.lutdir = lutdir
        self.log = log
        self.ancdir = None
        self.curdir = False
        self.pcf_template = None
        self.dirs = {}

        # version-specific variables
        self.collection_id = '061'
        self.pgeversion = '6.1.1'
#        self.lutversion = '0'

        if self.parfile:
            p = ParamProcessing(parfile=self.parfile)
            p.parseParFile(prog='l1agen')
            phash = p.params['l1agen']
            for param in (phash.keys()):
                if not self[param]:
                    self[param] = phash[param]
        self.l0file = os.path.basename(self.file)

    def __setitem__(self, index, item):
        self.__dict__[index] = item

    def __getitem__(self, index):
        return self.__dict__[index]


    def chk(self):
        """
        check input parameters
        """
        if not os.path.exists(self.file):
            print("ERROR: File: " + self.file + " does not exist.")
            sys.exit(1)

        if self.nextgranule is not None:
            if not os.path.exists(self.nextgranule):
                print("ERROR: File " + self.nextgranule + " does not exist.")
                sys.exit(1)
            else:
                self.stopnudge = 0
                if self.verbose:
                    print("* Next L0 granule is specified, therefore setting stopnudge = 0 *")

    def get_constructor(self):
        import subprocess
        import ProcUtils

        # rudimentary PCF file for logging, leapsec.dat
        self.pcf_file = self.l0file + '.pcf'
        ProcUtils.remove(self.pcf_file)

        os.environ['PGS_PC_INFO_FILE'] = self.pcf_file
        pcf = [line for line in open(self.pcf_template, 'r')]
        sed = open(self.pcf_file, 'w')
        for line in pcf:
            line = line.replace('LOGDIR', self.dirs['run'])
            line = line.replace('L1AFILE', os.path.basename(self.file))
            line = line.replace('VARDIR', os.path.join(self.dirs['var'], 'modis'))
            sed.write(line)
        sed.close()

        # create constructor file
        if self.verbose:
            print("Determining pass start and stop time...\n")

        self.grantimes = self.l0file + '.grantimes'
        ProcUtils.remove(self.grantimes)
        status = subprocess.call(
            ' '.join([os.path.join(self.dirs['bin'], 'l0cnst_write_modis'), self.l0file, ">", self.grantimes]),
            shell=True)
        return status

    def l1a_name(self):
        import ProcUtils
    # determine output file name
        starttime = None
        f = open(self.grantimes, 'r')
        for a in f.readlines():
            a = a.split('=')
            if not a: continue # empty line
            if a[0] == 'starttime':
                starttime = a[1].strip()
                break
        f.close()

        if starttime:
            grantime = ProcUtils.date_convert(starttime, 't', 'j')

            if self.l1a is not None:
                if self.verbose:
                    print("Using specified output L1A filename: %s" % self.l1a)
            else:
                if self.sat_name == "aqua":
                    self.l1a = os.path.join(self.dirs['run'], "A%s.L1A_LAC" % grantime)
                else:
                    self.l1a = os.path.join(self.dirs['run'], "T%s.L1A_LAC" % grantime)
                if self.verbose:
                    print("Using derived output L1A filename: %s" % self.l1a)


    def l0(self):
        """
        Write L0 Constructor File
        """
        import os
        import subprocess
        import sys
        import ProcUtils

        # The L0 file and constructor file must reside in the same directory,
        # so create a symlink to the L0 file as needed.

        if not os.path.exists(self.l0file):
            os.symlink(self.file, self.l0file)

        # create constructor file
        status = self.get_constructor()

        if status != 0 and status != 3:
            # bad error - exit now
            print("l0cnst_write_modis: Unrecoverable error encountered while attempting to generate constructor file.")
            sys.exit(1)

        if status == 3:
            # recoverable? try to fix l0
            if self.verbose:
                print("l0cnst_write_modis: A corrupt packet or a packet of the wrong size")
                print("                    was detected while generating the constructor file.")
            if not self.fix:
                print("Fixing of Level-0 file is currently disabled.")
                print("Please re-run without the '--disable-fix_L0' option.")
                sys.exit(1)

            # 1st call to l0fix_modis: get pass times
            if self.verbose:
                print("Attempting to fix the Level 0 file using l0fix_modis")

            self.l0fix1 = self.l0file + '.l0fix1'
            ProcUtils.remove(self.l0fix1)
            l0fixcmd = ' '.join(
                [os.path.join(self.dirs['bin'], 'l0fix_modis'), self.l0file, '-1', '-1', '>', self.l0fix1])
            if self.verbose:
                print(l0fixcmd)
            status = subprocess.call(l0fixcmd, shell=True)
            if status:
                print("l0fix_modis: Unrecoverable error in l0fix_modis!")
                sys.exit(1)

            # 2nd call to l0fix_modis: fix packets
            for line in open(self.l0fix1, 'r'):
                if "taitime_start:" in line:
                    self.taitime_start = line.split()[1]
                if "taitime_stop:" in line:
                    self.taitime_stop = line.split()[1]

            self.l0fix2 = self.l0file + '.l0fix2'
            ProcUtils.remove(self.l0fix2)

            l0fixcmd = ' '.join(
                [os.path.join(self.dirs['bin'], 'l0fix_modis'), self.l0file, self.taitime_start, self.taitime_stop,
                 self.l0file + '.fixed', '>', self.l0fix2])
            if self.verbose:
                print(l0fixcmd)
            status = subprocess.call(l0fixcmd, shell=True)
            if status:
                print("l0fix_modis: Unrecoverable error in l0fix_modis!")
                sys.exit(1)
            if self.verbose:
                print("New Level 0 file successfully generated. Regenerating constructor file...")
            self.l0file += '.fixed'

            # try again to make constructor file
            status = self.get_constructor()
            if status:
                print("Failed to generate constructor file after running l0fix_modis.")
                print("Please examine your Level 0 file to determine if it is completely corrupt.")
                sys.exit(1)

        # Determine pass start and stop times and duration of pass
        self.l1a_name()

        for line in open(self.grantimes, 'r'):
            if "starttime" in line:
                self.start = line[10:].rstrip()
            if "stoptime" in line:
                self.stop = line[10:].rstrip()
            if "length" in line:
                self.gransec = line[16:].rstrip()

        # Adjust starttime, stoptime, and gransec for L0 processing
        self.start = ProcUtils.addsecs(self.start, self.startnudge, 't')
        self.stop = ProcUtils.addsecs(self.stop, -1 * self.stopnudge, 't')
        self.gransec = float(self.gransec) - self.startnudge - self.stopnudge
        self.granmin = str(float(self.gransec) / 60.0)

        # set output file name
        if self.verbose:
            print("Input Level 0:", self.file)
            print("Output Level 1A:", self.l1a)
            print("Satellite:", self.sat_name)
            print("Start Time:", self.start)
            print("Stop Time:", self.stop)
            print("Granule Duration:", self.gransec, "seconds")
            print("")

    def run(self):
        """
        Run l1agen_modis (MOD_PRO01)
        """
        import os
        import shutil
        import subprocess
        import sys
        import ProcUtils

        # if next granule is set, create temp concatenated file
        if self.nextgranule is not None:
            shutil.move(self.l0file, self.l0file + '.tmp')
            cat = open(self.l0file, 'wb')
            shutil.copyfileobj(open(self.l0file + '.tmp', 'rb'), cat)
            shutil.copyfileobj(open(self.nextgranule, 'rb'), cat)
            cat.close()

        if self.verbose:
            print("Processing MODIS L0 file to L1A...")
        status = subprocess.call(os.path.join(self.dirs['bin'], 'l1agen_modis'), shell=True)
        if self.verbose:
            print('l1agen_modis exit status:', str(status))

        # if next granule is set, move original L0 file back to original name
        if self.nextgranule is not None:
            shutil.move(self.l0file + '.tmp', self.l0file)

        # clean up log files
        if not status:
            ProcUtils.remove(self.l0file + '.constr')
            ProcUtils.remove(self.l0file + '.grantimes')
            ProcUtils.remove(self.l0file + '.l0fix1')
            ProcUtils.remove(self.l0file + '.l0fix2')
            ProcUtils.remove(self.l0file + '.pcf')
            base = os.path.basename(self.l0file)
            ProcUtils.remove(os.path.join(self.dirs['run'], 'LogReport.' + base))
            ProcUtils.remove(os.path.join(self.dirs['run'], 'LogStatus.' + base))
            ProcUtils.remove(os.path.join(self.dirs['run'], 'LogUser.' + base))
            ProcUtils.remove(os.path.join(self.dirs['run'], "GetAttr.temp"))
            ProcUtils.remove(os.path.join(self.dirs['run'], "ShmMem"))
            ProcUtils.remove(self.l1a + '.met')

            if os.path.islink(self.l0file):
                os.remove(self.l0file)

            if os.path.islink(os.path.basename(self.file)):
                os.remove(os.path.basename(self.file))

            if self.log is False:
                ProcUtils.remove(self.pcf_file)
                base = os.path.basename(self.l1a)
                ProcUtils.remove(os.path.join(self.dirs['run'], 'LogReport.' + base))
                ProcUtils.remove(os.path.join(self.dirs['run'], 'LogStatus.' + base))
                ProcUtils.remove(os.path.join(self.dirs['run'], 'LogUser.' + base))

            if self.verbose:
                print("MODIS L1A processing complete.")
        else:
            print("modis_l1a: ERROR: MODIS L1A processing failed.")
            print("Please examine the LogStatus and LogUser files for more information.")
            sys.exit(1)
