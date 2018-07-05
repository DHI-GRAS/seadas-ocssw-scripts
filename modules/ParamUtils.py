# Utilities used by processing module, ocproc.py

__author__="Sean Bailey, Futuretech Corporation"
__date__ ="$Apr 10, 2010 4:49:15 PM$"

import re
import sys

class ParamProcessing:
    """
    Parameter processing class - build and parse par files
    """
    def __init__(self, params=None,parfile=None,parstr='',sensor=None,verbose=False):
        """
        Set up parameter processing methods
        """
        if params is None: params = {}
        self.params = params
        self.parfile = parfile
        self.parstr = parstr
        self.sensor = sensor
        self.verbose = verbose

    ############################################################################
    def buildParameterFile(self,prog):
        """Build a parameter file  from a dictionary of parameters.
        Writes parfile if pfile is defined, else Returns parfile string."""

        for k in self.params[prog].keys():
            if re.match('ocproc',k):
                del self.params[prog][k]

        filelst = ['ifile','ofile','ofile1','ofile2','ofile3','geofile',
            'spixl','dpixl','epixl','sline','eline','dline',
            'north','south','west','east']
        self.parstr = ''
        for f in filelst:
            try:
                pstr = '='.join([f, self.params[prog][f]])
                self.parstr = "\n".join([self.parstr,pstr])
            except Exception:
                pass

        for k,v in sorted(self.params[prog].items()):
            try:
                try:
                    filelst.index(k)
                    pass
                except Exception:
                    pstr = '='.join([k, v])
                    self.parstr = "\n".join([self.parstr,pstr])
            except Exception:
                pass

        if self.parfile:
            if self.verbose:
                print("Writing parfile %s" % self.parfile)
            logfile = open(self.parfile, 'w')
            logfile.write(self.parstr)
            logfile.write("\n")
            logfile.close()


    ############################################################################
    def parseParFile(self,prog='main'):
        """
        Parse a parameter file, returning a dictionary listing
        """
        try:
            if self.verbose:
                print('PAR',self.parfile)
            pfile = self.parfile
            par_file = open(pfile,'r')
        except Exception:
            print("File {0} not found!".format(self.parfile))
            return None

        try:
            self.params[prog]
        except Exception:
            self.params[prog]={}

        lines = par_file.readlines()
        for line in lines:
            if (len(line) == 0) or re.match('^\s+$',line):
                continue
            if line[0] == '#':
                parts = line.split()
                try:
                    ix = parts.index('section')
                    prog = parts[ix + 1].strip()
                    try:
                        self.params[prog] #TODO Fix this odd construction
                        continue
                    except Exception:
                        self.params[prog]={}
                except Exception:
                    pass
                continue
            if line.find('=') != -1:
                line_parts = line.split('#')[0].strip().split('=')
                if line_parts[0]:
                    if line_parts[0] == 'par':
                        p2 = ParamProcessing(parfile=line_parts[1])
                        p2.parseParFile(prog=prog)
                        self.params[prog].update(p2.params[prog])
                    elif line_parts[0] == 'ifile':
                        self.params[prog]['file'] = line_parts[1]
                    else:
                        self.params[prog][line_parts[0]] = line_parts[1]
            else:
                err_msg = 'Error!  Entry "{0}" is invalid in par file {1}'.format(line, self.parfile)
                sys.exit(err_msg)

    ############################################################################
    def genOutputFilename(self,prog=None):
        """Given a program, derive a standard output filename"""

        ifile = self.params[prog]['ifile']
        modsen ={'A':'T','P':'A'}
        ofile = None
        
        try:
            ofile = self.params[prog]['ofile']
        except Exception:
            fparts = ifile.split('.')
            if prog == 'l1agen':
                if re.search('L0',ifile):
                    ofile = ifile.replace('L0','L1A')
                elif re.match('M?D*',ifile):
                    type = ifile[6]
                    yrdy = ifile[7:14]
                    hrmn = ifile[15:19]
                    ofile = ''.join([modsen[type],yrdy,hrmn,'00.L1A_LAC'])
            elif prog == 'l1brsgen':
                ofile = '.'.join([fparts[0],'L1_BRS'])
            elif prog == 'l1mapgen':
                ofile = '.'.join([fparts[0],'L1_MAP'])
            elif prog == 'l2gen':
                if re.search('L1[AB]',ifile):
                    of = re.compile( '(L1A|L1B)')
                    ofile = of.sub( 'L2', ifile)
                else:
                    ofile = '.'.join([fparts[0],'L2'])
            elif prog == 'l2brsgen':
                try:
                    prod = self.params[prog]['prod']
                except Exception:
                    prod = 'chlor_a'
                ofile = '.'.join([fparts[0],prod,'L2_BRS'])
            elif prog == 'l2mapgen':
                try:
                    prod = self.params[prog]['prod']
                except Exception:
                    prod = 'chlor_a'
                ofile = '.'.join([fparts[0],prod,'L2_MAP'])
            elif prog == 'l2bin':
                ofile = 'output.file'
            elif prog == 'l3bin':
                ofile = 'output.file'
            elif prog == 'smigen':
                  ofile = 'output.file'
            elif prog == 'smitoppm':
                ofile = '.'.join([ifile,'ppm'])
            elif prog == 'l3gen':
                ofile = 'output.file'

            else:
                ofile = '.'.join([prog,'output_file'])

        self.params[prog]['ofile'] = ofile
