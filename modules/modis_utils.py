"""
Utility functions for MODIS processing programs.
"""

from MetaUtils import readMetadata
import get_obpg_file_type
import next_level_name_finder
import obpg_data_file
import os
import ProcUtils
import re
import shutil
import subprocess
import sys


def buildpcf(self):
    """
    Build process control file for MODIS L1A, Geolocation and L1B creation
    """

    base = self.file
    if self.proctype == "modisL1A":
        base = self.l1a
    if self.proctype == 'modisGEO':
        base = self.geofile
    if self.proctype == 'modisL1B':
        base = self.okm
    self.pcf_file = base + '.pcf'

    os.environ['PGS_PC_INFO_FILE'] = self.pcf_file
    if self.proctype == "modisGEO":
        if self.entrained:
            self.kinematic_state = "MODIS Packet"
            if self.verbose:
                print("Using entrained attitude/ephemeris information")

    pcf = [line for line in open(self.pcf_template, 'r')]

    sed = open(self.pcf_file, 'w')
    for line in pcf:
        if self.proctype == "modisL1A":
            line = line.replace('L0DIR', self.dirs['run'])
            line = line.replace('CURRL0GRAN0',
                                '.'.join([self.l0file, 'constr']))
            line = line.replace('CURRL0GRAN1', self.l0file)
            line = line.replace('L1ADIR', self.dirs['run'])
            line = line.replace('L1AFILE', os.path.basename(self.l1a))
            line = line.replace('MCFDIR', self.dirs['mcf'])
            line = line.replace('L1A_MCF', self.l1amcf)
            line = line.replace('CALDIR', self.dirs['cal'])
            line = line.replace('ENGLUTFILE', self.englutfile)
            line = line.replace('ENGLUTVER', self.englutver)
            line = line.replace('STARTTIME', self.start)
            line = line.replace('STOPTIME', self.stop)
            line = line.replace('GRANMIN', self.granmin)
            # since no previous granule, delete PREVL0GRAN0 lines from PCF file
            if '599001' in line:
                continue

        if self.proctype == "modisGEO":
            line = line.replace("MCFDIR", self.dirs['mcf'])
            line = line.replace("L1A_MCF", self.l1amcf)
            line = line.replace("GEO_MCF", self.geomcf)
            line = line.replace("GEOLUTFILE", self.geolutfile)
            line = line.replace("GEOLUTVER", self.geolutver)
            line = line.replace("GEOMVRFILE", self.geomvrfile)
            line = line.replace("GEOMVRVER", self.geomvrver)
            line = line.replace("GEOMVRLIST", '')
            line = line.replace("PLANETFILE", self.planetfile)
            line = line.replace("KINEMATIC_STATE", self.kinematic_state)
            line = line.replace("DEMDIR", self.dirs['dem'])

            if self.terrain:
                line = line.replace("TERRAIN_CORRECT", "TRUE")
            else:
                line = line.replace("TERRAIN_CORRECT", "FALSE")

            if self.entrained:
                if "ATTDIR" in line:
                    continue

                if "EPHDIR" in line:
                    continue
            else:
                if "ATTDIR" in line:
                    if self.attdir2 == "NULL" and re.search('2$', line):
                        continue
                    if self.attdir1 == 'NULL' and re.search('1$', line):
                        continue

                if "EPHDIR" in line:
                    if self.ephdir2 == "NULL" and re.search('2$', line):
                        continue
                    if self.ephdir1 == 'NULL' and re.search('1$', line):
                        continue

                line = line.replace("ATTDIR1", self.attdir2)
                line = line.replace("ATTFILE1", self.attfile2)
                line = line.replace("ATTDIR2", self.attdir1)
                line = line.replace("ATTFILE2", self.attfile1)
                line = line.replace("EPHDIR1", self.ephdir2)
                line = line.replace("EPHFILE1", self.ephfile2)
                line = line.replace("EPHDIR2", self.ephdir1)
                line = line.replace("EPHFILE2", self.ephfile1)

        if self.proctype == "modisL1B":
            line = line.replace('L1BDIR', self.dirs['run'])
            line = line.replace('QKMFILE', os.path.basename(self.qkm))
            line = line.replace('1KMFILE', os.path.basename(self.okm))
            line = line.replace('HKMFILE', os.path.basename(self.hkm))
            line = line.replace('OBCFILE', os.path.basename(self.obc))
            line = line.replace('QKM_MCF', os.path.basename(self.qkm_mcf))
            line = line.replace('HKM_MCF', os.path.basename(self.hkm_mcf))
            line = line.replace('1KM_MCF', os.path.basename(self.okm_mcf))
            line = line.replace('OBC_MCF', os.path.basename(self.obc_mcf))
            line = line.replace('CALDIR', self.dirs['cal'])
            line = line.replace('REFL_LUT', self.refl_lut)
            line = line.replace('EMIS_LUT', self.emis_lut)
            line = line.replace('QA_LUT', self.qa_lut)
            line = line.replace('LUTVERSION', self.lutversion)

        if re.search('(GEO|L1B)', self.proctype):
            line = line.replace("GEODIR",
                                os.path.abspath(os.path.dirname(self.geofile)))
            line = line.replace("GEOFILE", os.path.basename(self.geofile))

        line = line.replace('MCFDIR', self.dirs['mcf'])
        line = line.replace("CALDIR", self.dirs['cal'])
        line = line.replace("STATIC", self.dirs['static'])
        line = line.replace("L1ADIR",
                            os.path.abspath(os.path.dirname(self.file)))
        line = line.replace("L1AFILE", os.path.basename(self.file))

        line = line.replace("VARDIR", os.path.join(self.dirs['var'], 'modis'))
        line = line.replace('LOGDIR', self.dirs['run'])
        line = line.replace('SAT_INST', self.sat_inst)
        line = line.replace('PGEVERSION', self.pgeversion)

        sed.write(line)
    sed.close()


def modis_timestamp(arg):
    """
        Determine the start time, stop time, and platform of a MODIS hdf4 file.
    """

    meta = readMetadata(arg)
    sat_name = meta['ASSOCIATEDPLATFORMSHORTNAME'].lower()
    start_time = meta['RANGEBEGINNINGDATE'] + ' ' + meta['RANGEBEGINNINGTIME']
    end_time = meta['RANGEENDINGDATE'] + ' ' + meta['RANGEENDINGTIME']
    # at this point datetimes are formatted as YYYY-MM-DD HH:MM:SS.uuuuuu

    # return values formatted as YYYYDDDHHMMSS
    return (ProcUtils.date_convert(start_time, 'h', 'j'),
            ProcUtils.date_convert(end_time, 'h', 'j'),
            sat_name)


def getversion(file_name):
    """
    Returns the version of the file named filename.
    """
    clean = ""
    if os.path.exists(file_name):
        for line in open(file_name):
            if "$Revision" in line:
                sidx = line.find('$Revision')
                eidx = line.rfind('$')
                clean = line[sidx + 10:eidx - 1].lstrip()
                break

    return clean


def sortLUT(lut, length):
    """
        Version comparison for LUTs
    """
    lut = lut.split("\n")
    for ndx in range(len(lut)):
        lut[ndx] = lut[ndx][length:].rstrip('.hdf')

    lut = sorted(lut, cmp=cmpver)
    return lut[0]


def cmpver(a, b):
    """
        Version comparison algorithm
    """

    def fixup(i):
        """
        Returns i as an int if possible, or in its original form otherwise.
        """
        try:
            return int(i)
        except ValueError:
            return i

    a = list(map(fixup, re.findall(r'\d+|\w+', a)))
    b = list(map(fixup, re.findall(r'\d+|\w+', b)))
    return cmp(b, a)


def cleanup(lut):
    clean = ""
    for ndx in range(len(lut)):
        if ndx % 2:
            clean = clean + lut[ndx] + "\n"
    return clean


def modis_env(self):
    """
    Set up the  MODIS processing environment
    """

    if not os.path.exists(os.path.join(os.getenv("OCDATAROOT"), "modis")):
        print("ERROR: The " + os.path.join(os.getenv("OCDATAROOT"), "modis") + "directory does not exist.")
        sys.exit(1)

    os.environ["PGSMSG"] = os.path.join(os.getenv("OCDATAROOT"),
                                        "modis", "static")

    # MODIS L1A
    if self.proctype == "modisL1A":
        aqua = re.compile(r'''(
            ^[aA]|      # [Aa]*
            ^MOD00.P|   # MOD00.P*
            ^MYD\S+.A|  # MYD*.A*
            ^P1540064   # P1540064*
            )''', re.VERBOSE)
        terra = re.compile(r'''(
            ^[tT]|      # [tT]*
            ^MOD\S+.A|  # MOD*.A*
            ^P0420064   # P0420064*
            )''', re.VERBOSE)

        if self.sat_name is not None:
            if aqua.search(self.sat_name) is not None:
                self.sat_name = 'aqua'
            elif terra.search(self.sat_name) is not None:
                self.sat_name = 'terra'
        else:
            if aqua.search(os.path.basename(self.file)) is not None:
                self.sat_name = 'aqua'
            elif terra.search(os.path.basename(self.file)) is not None:
                self.sat_name = 'terra'
            else:
                print("ERROR: Unable to determine platform type for " + self.file)
                print("")
                print("Please use the '--satellite' argument to specify the platform as 'aqua' or 'terra',")
                print("or rename your input file to match one of the following formats:")
                print("")
                print("\tAqua:  'a*' or 'A*' or 'MOD00.P*' or 'P1540064* or 'MYD*.A*''")
                print("\tTerra: 't*' or 'T*' or 'MOD00.A*' or 'P0420064*'")
                sys.exit(1)
    else:
        # Determine pass start time and platform
        self.start, self.stop, self.sat_name = modis_timestamp(self.file)

    # set sensor specific variables
    if self.sat_name == 'aqua':
        self.sensor = 'modisa'
        self.sat_inst = 'PM1M'
        self.prefix = 'MYD'
        if self.proctype == 'modisL1B':
            self.pgeversion = "6.2.1_obpg"
    elif self.sat_name == 'terra':
        self.sensor = 'modist'
        self.sat_inst = 'AM1M'
        self.prefix = 'MOD'
        if self.proctype == 'modisL1B':
            self.pgeversion = "6.2.2_obpg"

    else:
        print("ERROR: Unable to determine platform type for", self.file)
        sys.exit(1)

    # Static input directories
    self.dirs['cal'] = os.path.join(os.getenv("OCDATAROOT"), 'modis', self.sat_name, 'cal')
    self.dirs['mcf'] = os.path.join(os.getenv("OCDATAROOT"), 'modis', self.sat_name, 'mcf')
    self.dirs['static'] = os.path.join(os.getenv("OCDATAROOT"), 'modis', 'static')
    self.dirs['dem'] = os.path.join(os.getenv("OCDATAROOT"), 'modis', 'dem')
    if not os.path.exists(self.dirs['dem']):
        self.dirs['dem'] = self.dirs['static']
    self.dirs['pcf'] = os.path.join(os.getenv("OCDATAROOT"), 'modis', 'pcf')

    # MODIS L1A
    if self.proctype == "modisL1A":
        self.pcf_template = os.path.join(self.dirs['pcf'], 'L1A_template.pcf')
        if not os.path.exists(self.pcf_template):
            print("ERROR: Could not find the L1A PCF template: " + self.pcf_template)
            sys.exit(1)

        self.l1amcf = ''.join([self.prefix, '01_', self.collection_id, '.mcf'])
        self.englutfile = 'ENG_DATA_LIST_' + self.sat_name.upper() + '_V' + self.pgeversion
        if self.lutversion:
            self.englutfile += '.' + self.lutversion
        self.englutver = getversion(os.path.join(self.dirs['cal'],
                                                 self.englutfile))

    # MODIS GEO
    if self.proctype == "modisGEO":
        self.pcf_template = os.path.join(self.dirs['pcf'], 'GEO_template.pcf')
        if not os.path.exists(self.pcf_template):
            print("ERROR: Could not find GEO PCF template " + self.pcf_template)
            sys.exit(1)

        self.l1amcf = ''.join([self.prefix, '01_', self.collection_id, '.mcf'])
        self.geomcf = ''.join([self.prefix, '03_', self.collection_id, '.mcf'])
        self.geolutfile = ''.join([self.prefix, '03LUT.coeff_V', self.pgeversion])
        self.geomvrfile = ''.join(['maneuver_', self.sat_name, '.coeff_V', self.pgeversion])
        if self.lutversion:
            self.geolutfile += '.' + self.lutversion
            self.geomvrfile += '.' + self.lutversion
        self.geolutver = getversion(os.path.join(self.dirs['cal'],
                                                 self.geolutfile))
        self.geomvrver = getversion(os.path.join(self.dirs['cal'],
                                                 self.geomvrfile))

        self.planetfile = "de200.eos"
        if not os.path.exists(os.path.join(self.dirs['static'],
                                           self.planetfile)):
            if not os.path.exists(os.path.join(self.dirs['static'],
                                               'de200.dat')):
                print("ERROR: File " + os.path.join(self.dirs['static'], self.planetfile) + "does not exist.")
                print("       nor does " + os.path.join(self.dirs['static'], 'de200.dat') + "...")
                print("       Something is amiss with the environment...")
                sys.exit(1)
            else:
                if self.verbose:
                    print("Creating binary planetary ephemeris file...")
                planetfile = os.path.join(self.dirs['static'], 'de200.dat')
                cmd = ' '.join([os.path.join(self.dirs['bin3'], 'ephtobin'), planetfile])
                status = subprocess.call(cmd, shell=True)

                if status:
                    print(status)
                    print("Error creating binary planetary ephemeris file")
                    sys.exit(1)
                else:
                    shutil.move('de200.eos', os.path.join(self.dirs['static'],
                                                          'de200.eos'))

        # determine output file name
        if not self.geofile:
            file_typer = get_obpg_file_type.ObpgFileTyper(self.file)
            ftype, sensor = file_typer.get_file_type()
            stime, etime = file_typer.get_file_times()
            data_files_list = list([obpg_data_file.ObpgDataFile(self.file,
                                                                ftype, sensor,
                                                                stime, etime)])
            name_finder = next_level_name_finder.ModisNextLevelNameFinder(
                data_files_list, 'geo')
            self.geofile = name_finder.get_next_level_name()

    # MODIS L1B
    if self.proctype == "modisL1B":
        self.pcf_template = os.path.join(self.dirs['pcf'], 'L1B_template.pcf')
        if not os.path.exists(self.pcf_template):
            print("ERROR: Could not find the L1B PCF template", self.pcf_template)
            sys.exit(1)

        # Search LUTDIR for lut names
        if not self.lutdir:
            self.lutdir = os.path.join(self.dirs['var'], self.sensor, 'cal', 'OPER')

        if not self.lutversion:
            try:
                from LutUtils import lut_version
                versions = [lut_version(f) for f in os.listdir(self.lutdir) if f.endswith('.hdf')]
                self.lutversion = sorted(versions)[-1][1:]  # highest version number
            except:
                print("ERROR: Could not find LUTs in".self.lutdir)
                sys.exit(1)

        self.refl_lut = self.prefix + '02_Reflective_LUTs.V' + self.lutversion + '.hdf'
        self.emis_lut = self.prefix + '02_Emissive_LUTs.V' + self.lutversion + '.hdf'
        self.qa_lut = self.prefix + '02_QA_LUTs.V' + self.lutversion + '.hdf'

        if self.verbose:
            print("")
            print("LUT directory: %s" % self.lutdir)
            print("LUT version: %s" % self.lutversion)
            print("Reflective LUT: %s" % self.refl_lut)
            print("Emissive LUT: %s" % self.emis_lut)
            print("QA LUT: %s" % self.qa_lut)
            print("")

        self.qkm_mcf = ''.join([self.prefix, '02QKM_',
                                self.collection_id, '.mcf'])
        self.hkm_mcf = ''.join([self.prefix, '02HKM_',
                                self.collection_id, '.mcf'])
        self.okm_mcf = ''.join([self.prefix, '021KM_',
                                self.collection_id, '.mcf'])
        self.obc_mcf = ''.join([self.prefix, '02OBC_',
                                self.collection_id, '.mcf'])

        # set output file name
        file_typer = get_obpg_file_type.ObpgFileTyper(self.file)
        ftype, sensor = file_typer.get_file_type()
        stime, etime = file_typer.get_file_times()
        data_files_list = list([obpg_data_file.ObpgDataFile(self.file,
                                                            ftype, sensor,
                                                            stime, etime)])
        name_finder = next_level_name_finder.ModisNextLevelNameFinder(
            data_files_list, 'l1bgen')
        l1b_name = name_finder.get_next_level_name()
        self.base = os.path.join(self.dirs['run'],
                                 os.path.basename(l1b_name).split('.')[0])

        if self.okm is None:
            if re.search('L1A_LAC', self.file):
                self.okm = self.file.replace("L1A_LAC", "L1B_LAC")
            else:
                self.okm = '.'.join([self.base, 'L1B_LAC'])
        if self.hkm is None:
            if re.search('L1A_LAC', self.file):
                self.hkm = self.file.replace("L1A_LAC", "L1B_HKM")
            else:
                self.hkm = '.'.join([self.base, 'L1B_HKM'])
        if self.qkm is None:
            if re.search('L1A_LAC', self.file):
                self.qkm = self.file.replace("L1A_LAC", "L1B_QKM")
            else:
                self.qkm = '.'.join([self.base, 'L1B_QKM'])
        if self.obc is None:
            if re.search('L1A_LAC', self.file):
                self.obc = self.file.replace("L1A_LAC", "L1B_OBC")
            else:
                self.obc = '.'.join([self.base, 'L1B_OBC'])

        if not os.path.exists(os.path.join(self.lutdir, self.refl_lut)) \
                or not os.path.exists(os.path.join(self.lutdir, self.emis_lut)) \
                or not os.path.exists(os.path.join(self.lutdir, self.qa_lut)):
            print("ERROR: One or more of the required LUTs does not exist in %s:" % self.lutdir)
            print("")
            print("Reflective LUT:", self.refl_lut)
            print("Emissive LUT:", self.emis_lut)
            print("QA LUT:", self.qa_lut)
            sys.exit(1)

        self.dirs['rlut'] = os.path.abspath(os.path.dirname(self.refl_lut))
        self.refl_lut = os.path.basename(self.refl_lut)
        self.dirs['elut'] = os.path.abspath(os.path.dirname(self.emis_lut))
        self.emis_lut = os.path.basename(self.emis_lut)
        self.dirs['qlut'] = os.path.abspath(os.path.dirname(self.qa_lut))
        self.qa_lut = os.path.basename(self.qa_lut)

        self.dirs['cal'] = self.lutdir
