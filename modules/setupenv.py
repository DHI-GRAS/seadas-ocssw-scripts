import os
import sys


def env(self):
    """
    A simple module to populate some important environment variables
    """

    if os.getenv("OCDATAROOT") is None:
        print("ERROR: OCDATAROOT environment variable not set.")
        sys.exit(1)
    else:
        self.dirs['root'] = os.getenv("OCDATAROOT")

    if not os.path.exists(os.getenv("OCDATAROOT")):
        print("ERROR: The OCDATAROOT " + os.getenv("OCDATAROOT") + " directory does not exist.")
        print("Please make sure you have downloaded and installed the SeaDAS processing data support file (seadas_processing.tar.gz).")
        sys.exit(1)

    self.dirs['scripts'] = os.path.join(os.getenv("OCSSWROOT"), "scripts")
    self.dirs['var'] = os.path.join(os.getenv("OCSSWROOT"), "var")
    self.dirs['bin'] = os.getenv("OCSSW_BIN")
    self.dirs['bin3'] = os.getenv("LIB3_BIN")
    self.dirs['log'] = os.path.join(os.getenv("OCSSWROOT"), "log")
    if not os.path.exists(self.dirs['log']):
        self.dirs['log'] = self.dirs['var']

    if os.getenv("OCSSW_DEBUG") is not None and int(os.getenv("OCSSW_DEBUG")) > 0:
        if not os.path.exists(self.dirs['bin']):
            print("Error:  OCSSW_DEBUG set, but...\n\t%s\ndoes not exist!" % self.dirs['bin'])
            sys.exit(1)
        else:
            print("Running debug binaries...\n\t%s" % self.dirs['bin'])

    self.dirs['run'] = os.path.abspath(os.getcwd())
    if self.curdir:
        self.dirs['anc'] = self.dirs['run']
    else:
        if self.ancdir is None:
            if os.getenv("L2GEN_ANC") is None and os.getenv("USER_L2GEN_ANC") is None:
                if self.verbose:
                    print("Neither the L2GEN_ANC nor USER_L2GEN_ANC environment variables are set.")
                    print("...using the current working directory for ancillary file download.")
                self.curdir = True
                self.dirs['anc'] = self.dirs['run']
            else:
                if os.getenv("L2GEN_ANC") is not None:
                    self.dirs['anc'] = os.getenv("L2GEN_ANC")
                else:
                    self.dirs['anc'] = os.getenv("USER_L2GEN_ANC")
        else:
            if self.ancdir[0] != "/":
                self.dirs['anc'] = os.path.join(self.dirs['run'], self.ancdir)
            else:
                self.dirs['anc'] = self.ancdir
