#! /usr/bin/python

# Wrapper routines to provide parameter file arguments to code that does not
# use the OCSSW command-line option argument format

__author__="Sean Bailey, Futuretech Corporation"
__date__ ="$Oct 8, 2010 1:45:00 PM$"


class ProcWrap():
    """
    Documentation
    """
    def __init__(self, params=None,procmd=None):
        """Documentation"""
        self.params = params
        self.procmd = procmd
        
    def l1agen_seawifs(self):
        """
        l1agen_seawifs wrapper
        Usage: l1agen_seawifs argument-list
        The argument-list is a set of keyword=value pairs. The arguments can
        be specified on the commandline, or put into a parameter file, or
        the two methods can be used together, with commandline over-riding.
        
        The list of valid keywords follows:

            ifile (string) = input L0 file name
            ofile (string)(default=NULL) = output L1A file name
                default based on station info file
            metadata (bool) = turn-off metadata file generation
            hrpt (bool) = force hrpt processing
            gac (bool) = force GAC processing
            limit (int) (default=NULL) = limit timetags to +/- n-days around
                data start time
            biterr (int) (default=50) = max number of frame bit errors allowed
            fixgain (int) (default=0) = fix gain setting for HRPT
                (-1 to determine from telemetry)
            stoptime (int) (default=undefined) = stop-time delta (seconds)
            anomaly (string) (default=NULL) = timing anomaly update filename
                GAC only, if not provided, no timing error search will be done
            runenv (string) (default=seadas) = runtime environment
                seadas or sdps
            station (string)(default=$HRPT_STATION_IDENTIFICATION_FILE) = station info file
        """
        options = {'metadata':0,'hrpt':0,'gac':0,'limit':None,'biterr':50,
            'fixgain':0,'stoptime':-999,'anomaly':None,'runenv':'seadas','station':None}
        options.update(self.params)
        self.procmd = ['l1agen_seawifs']
        if options['metadata'] > 0:
            self.procmd.append('-m')
        if options['hrpt'] > 0:
            self.procmd.append('-h')
        if options['gac'] > 0:
            self.procmd.append('-g')
        if options['limit']:
            self.procmd.append('-t')
            self.procmd.append(str(options['limit']))
        if options['biterr'] > 0:
            self.procmd.append('-b')
            self.procmd.append(str(options['biterr']))
        if options['fixgain'] > 0:
            self.procmd.append('-s')
            self.procmd.append(str(options['fixgain']))
        if options['stoptime'] > 0:
            self.procmd.append('-d')
            self.procmd.append(str(options['stoptime']))
        if options['anomaly']:
            self.procmd.append('-e')
            self.procmd.append(str(options['anomaly']))
        if options['runenv'] > 0:
            self.procmd.append('-n')
            self.procmd.append(str(options['runenv']))
        if options['station']:
            self.procmd.append('-f')
            self.procmd.append(str(options['station']))
        self.procmd.append(options['ifile'])

    def l1agen_czcs(self):
        """
        l1agen_czcs wrapper
        Usage: l1agen_czcs argument-list
        The argument-list is a set of keyword=value pairs. The arguments can
        be specified on the commandline, or put into a parameter file, or the
        two methods can be used together, with commandline over-riding.

        The list of valid keywords follows:

            ifile (string) = input L0 CZCS file name
            opath (string) (default='./') = output directory path
        """
        options = {'opath':'./'}
        options.update(self.params)

        self.procmd = ['l1agen_czcs',
            options['ifile'],options['opath']]

    def l1aextract_seawifs(self):
        """
        l1aextract wrapper
        Usage: l1aextract argument-list
        The argument-list is a set of keyword=value pairs. The arguments can
        be specified on the commandline, or put into a parameter file, or the
        two methods can be used together, with commandline over-riding.

        The list of valid keywords follows:

            ifile (string) = input L2 file name
            spixl (int) (default=1) = start pixel number
            epixl (int) (default=-999) = end pixel number
            sline (int) (default=1) = start line number
            eline (int) (default=-999) = end line number
            dpixl (int) (default=1) = pixel subsampling rate
            dline (int) (default=1) = scan line subsampling rate
            ofile (string) (default=ifile name + .sub) = output file name

        Note: Enter line number NOT scan number!
        """

        options = {'spixl':1,'epixl':-999,'sline':1,'eline':-999,
            'dpixl':1,'dline':1}
        options.update(self.params)
        try:
            options['ofile']
        except Exception:
            options['ofile'] = '.'.join([options['ifile'],'sub'])
            
        self.procmd = ['l1aextract_seawifs',options['ifile'],
                str(options['spixl']),
                str(options['epixl']),
                str(options['sline']),
                str(options['eline']),
                str(options['dpixl']),
                str(options['dline']),
                options['ofile']]

    def l1aextract_modis(self):
        """
        l1aextract wrapper
        Usage: l1aextract argument-list
        The argument-list is a set of keyword=value pairs. The arguments can
        be specified on the commandline, or put into a parameter file, or the
        two methods can be used together, with commandline over-riding.

        The list of valid keywords follows:

            ifile (string) = input L2 file name
            spixl (int) (default=1) = start pixel number
            epixl (int) (default=-999) = end pixel number
            sline (int) (default=1) = start line number
            eline (int) (default=-999) = end line number
            ofile (string) (default=ifile name + .sub) = output file name

        Note: Enter line number NOT scan number!
        """
        options = {'spixl':1,'epixl':-999,'sline':1,'eline':-999}
        options.update(self.params)
        try:
            options['ofile']
        except Exception:
            options['ofile'] = '.'.join([options['ifile'],'sub'])
            
        self.procmd = ['l1aextract_modis',options['ifile'],
                str(options['spixl']),
                str(options['epixl']),
                str(options['sline']),
                str(options['eline']),
                options['ofile']]

    def l2extract(self):
        """
        l2extract wrapper
        Usage: l2extract argument-list
        The argument-list is a set of keyword=value pairs. The arguments can
        be specified on the commandline, or put into a parameter file, or the
        two methods can be used together, with commandline over-riding.

        The list of valid keywords follows:

            ifile (string) = input L2 file name
            spixl (int) (default=1) = start pixel number
            epixl (int) (default=-999) = end pixel number
            sline (int) (default=1) = start line number
            eline (int) (default=-999) = end line number
            dpixl (int) (default=1) = pixel subsampling rate
            dline (int) (default=1) = scan line subsampling rate
            ofile (string) (default=ifile name + .sub) = output file name
            prod (string) (default=unspecified) = output product list

        Note: Enter line number NOT scan number!
        """

        options = {'spixl':1,'epixl':-999,'sline':1,'eline':-999,
            'dpixl':1,'dline':1,'prod':''}
        options.update(self.params)
        try:
            options['ofile']
        except Exception:
            options['ofile'] = '.'.join([options['ifile'],'sub'])
            
        self.procmd = ['l2aextract',options['ifile'],
                str(options['spixl']),
                str(options['epixl']),
                str(options['sline']),
                str(options['eline']),
                str(options['dpixl']),
                str(options['dline']),
                options['ofile'],
                options['prod']]
        

    def l2brsgen(self):
        """
        l2brsgen wrapper
        Usage: l2brsgen argument-list
        The argument-list is a set of keyword=value pairs. The arguments can
        be specified on the commandline, or put into a parameter file, or the
        two methods can be used together, with commandline over-riding.

        The list of valid keywords follows:

            ifile (string) = input L2 file name
            ofile (string) (default=ifile name + .BRS) = output file name
            dpixl (int) (default=10) = pixel subsampling rate
            dline (int) (default=10) = scan line subsampling rate
            prod (string) (default=chlor_a) = output product list
            qual (int) (default=2) = output product list
        """
        options = {'dpixl':10,'dline':10,'prod':None,'qual':2}
        options.update(self.params)
        try:
            options['ofile']
        except Exception:
            options['ofile'] = '.'.join([options['ifile'],'BRS'])

        self.procmd = ['l2brsgen']
        if options['dpixl'] > 1:
            self.procmd.append('-x')
            self.procmd.append(str(options['dpixl']))
        if options['dline'] > 1:
            self.procmd.append('-y')
            self.procmd.append(str(options['dline']))
        if options['prod']:
            self.procmd.append('-p')
            self.procmd.append(str(options['prod']).strip())
        if options['qual']:
            self.procmd.append('-q')
            self.procmd.append(str(options['qual']))

        self.procmd.append(options['ifile'])
        self.procmd.append(options['ofile'])


    def smitoppm(self):
        """
        smitoppm wrapper
        Usage: smitoppm argument-list
        The argument-list is a set of keyword=value pairs. The arguments can
        be specified on the commandline, or put into a parameter file, or the
        two methods can be used together, with commandline over-riding.

        The list of valid keywords follows:

            ifile (string) = input L3 SMI file name
            ofile (string) (default=ifile + '.ppm') = output file name
        """
        options = {}
        options.update(self.params)
        try:
            options['ofile']
        except Exception:
            options['ofile'] = '.'.join([options['ifile'],'ppm'])

        self.procmd = ['smitoppm',
            options['ifile']]
        self.procmd.append('>')
        self.procmd.append(options['ofile'])
        

    def procSelect(self,cmd):

        if cmd == 'l1agen_seawifs':
            self.l1agen_seawifs()
        elif cmd == 'l1agen_czcs':
            self.l1agen_czcs()
        elif cmd == 'l1aextract_seawifs':
            self.l1aextract_seawifs()
        elif cmd == 'l1aextract_modis':
            self.l1aextract_modis()
        elif cmd == 'l2extract':
            self.l2extract()
        elif cmd == 'l2brsgen':
            self.l2brsgen()
        elif cmd == 'smitoppm':
            self.smitoppm()
        else:
            self.cmd = None



