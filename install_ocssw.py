#! /usr/bin/env python

from optparse import OptionParser
import os
import urllib

verbose = False
installDir = None
gitBase =  'http://oceandata.sci.gsfc.nasa.gov/ocssw/'

def makeDir(dir):
    """
    Creates the directory if needed.
    """
    fullDir = os.path.join(installDir, dir)
    if os.path.isdir(fullDir) == False:
        if verbose:
            print 'creating dir', fullDir
        os.mkdir(fullDir)


def installGitRepo(repoName, dir):
    """
    Installs or updates the repo into dir.
    """
    fullDir = os.path.join(installDir, dir)
    if os.path.isdir(fullDir):
        # directory exists try a git update
        if verbose:
            print "updating existing directory -", fullDir
        commandStr = 'cd ' + fullDir + '; git pull'
    else:
        # directory does not exist
        if verbose:
            print "downloading new directory -", fullDir
        commandStr = 'git clone ' + gitBase + repoName + ' ' + fullDir

    retval = os.system(commandStr)
    if retval != 0:
        print 'Error - Could not execute system command \"', commandStr, '\"'
        exit(1)

        
def getArch():
    """
    Return the system arch string.
    """
    #
    # mac = ('Darwin',
    #        'gs616-shea',
    #        '11.4.2',
    #        'Darwin Kernel Version 11.4.2: Thu Aug 23 16:25:48 PDT 2012; root:xnu-1699.32.7~1/RELEASE_X86_64',
    #        'x86_64')
    #
    # linux_64 = ('Linux',
    #             'crab',
    #             '3.2.0-38-generic',
    #             '#61-Ubuntu SMP Tue Feb 19 12:18:21 UTC 2013',
    #             'x86_64')
    #
    # linux = ('Linux',
    #          'swdev102',
    #          '3.2.0-34-generic-pae',
    #          '#53-Ubuntu SMP Thu Nov 15 11:11:12 UTC 2012',
    #          'i686')
    #

    (sysname, nodename, release, version, machine) = os.uname()
    if sysname == 'Darwin':
        if machine == 'x86_64':
            return 'macosx_intel'
        print "unrecognized Mac machine =", machine
        exit(1)
    if sysname == 'Linux':
        if machine == 'x86_64':
            return 'linux_64'
        return 'linux'
    print '***** unrecognized system =', sysname, ', machine =', machine
    print '***** defaulting to linux_64'
    return 'linux_64'



if __name__ == "__main__":
    
    # Read commandline options...
    version = "%prog 1.0"
    usage = '''usage: %prog [options] FILE pixel line'''
    parser = OptionParser(usage=usage, version=version)

    parser.add_option("-v", "--verbose", action="store_true", dest="verbose", 
                      default=False, help="Print more information whle running")
    parser.add_option("-i", "--install-dir", action="store", 
                      dest="install_dir", default="ocssw",
                      help="destination directory for install")
    parser.add_option("-g", "--git-base", action="store",  dest="git_base", 
                      default="http://oceandata.sci.gsfc.nasa.gov/ocssw/",
                      help="Web location for the git repositories")
    parser.add_option("-a", "--arch", action="store",dest='arch', 
           help="set system architecture (linux, linux_64, macosx_intel")
    parser.add_option("-s", "--src", action="store_true",dest='src', 
                      default=False, help="install source code")

    # add missions
    parser.add_option("--aquarius", action="store_true", dest="aquarius", 
                      default=False, help="install Aquarius files")
    parser.add_option("--avhrr", action="store_true", dest="avhrr", 
                      default=False, help="install AVHRR files")
    parser.add_option("--czcs", action="store_true", dest="czcs", default=False,
                      help="install CZCS files")
    parser.add_option("--goci", action="store_true", dest="goci", default=False,
                      help="install GOCI files")
    parser.add_option("--hico", action="store_true", dest="hico", default=False,
                      help="install HICO files")
    parser.add_option("--meris", action="store_true", dest="meris", 
                      default=False, help="install MERIS files")
    parser.add_option("--aqua", action="store_true", dest="aqua", default=False,
                      help="install MODIS Aqua files")
    parser.add_option("--terra", action="store_true", dest="terra", 
                      default=False, help="install MODIS Terra files")
    parser.add_option("--mos", action="store_true", dest="mos", default=False,
                      help="install MOS files")
    parser.add_option("--ocm1", action="store_true", dest="ocm1", default=False,
                      help="install OCM1 files")
    parser.add_option("--ocm2", action="store_true", dest="ocm2", default=False,
                      help="install OCM2 files")
    parser.add_option("--ocrvc", action="store_true", dest="ocrvc", 
                      default=False, help="install ocrvc files")
    parser.add_option("--octs", action="store_true", dest="octs", default=False,
                      help="install OCTS files")
    parser.add_option("--osmi", action="store_true", dest="osmi", default=False,
                      help="install OSMI files")
    parser.add_option("--seawifs", action="store_true", dest="seawifs", 
                      default=False, help="install SeaWiFS files")
    parser.add_option("--viirsn", action="store_true", dest="viirsn", 
                      default=False, help="install VIIRSN files")
    parser.add_option("--direct-broadcast", action="store_true",
                      dest='direct_broadcast', 
                      default=False, help="install direct broadcast files")
    parser.add_option("--eval", action="store_true", dest="eval", default=False,
                      help="install evaluation sensor files")

    (options, args) = parser.parse_args()

    # set global variables
    gitBase = options.git_base
    verbose = options.verbose
    installDir = os.path.abspath(options.install_dir)
    if options.arch:
        arch = options.arch
    else:
        arch = getArch()

    # set direct broadcast
    if options.direct_broadcast:
        options.aqua = True
        options.terra = True

    # print out info if in verbose mode
    if verbose:
        print '\ngitBase     =', gitBase
        print 'install dir =', installDir
        print 'arch        =', arch
        print

    # create directory structure
    makeDir('')
    makeDir('run')
    makeDir('run/data')
    makeDir('run/bin')
    makeDir('run/bin3')

    # download OCSSW_bash.env and README
    fileName='OCSSW_bash.env'
    urllib.urlretrieve (gitBase+fileName, os.path.join(installDir, fileName))
    fileName='README'
    urllib.urlretrieve (gitBase+fileName, os.path.join(installDir, fileName))

    # download run/scripts
    installGitRepo('scripts.git', 'run/scripts')

    # install build source directory
    if options.src:
        installGitRepo('build.git', 'build')
        
    # install run/data/common
    installGitRepo('common.git', 'run/data/common')
    
    # install run/data/aquarius
    if options.aquarius:
        installGitRepo('aquarius.git', 'run/data/aquarius')

    # install run/data/avhrr
    if options.avhrr:
        installGitRepo('avhrr.git', 'run/data/avhrr')

    # install run/data/czcs
    if options.czcs:
        installGitRepo('czcs.git', 'run/data/czcs')

    # install run/data/eval
    if options.eval:
        installGitRepo('eval.git', 'run/data/eval')

    # install run/data/goci
    if options.goci:
        installGitRepo('goci.git', 'run/data/goci')

    # install run/data/hico
    if options.hico:
        installGitRepo('hico.git', 'run/data/hico')
        installGitRepo('hicohs.git', 'run/data/hicohs')

    # install run/data/meris
    if options.meris:
        installGitRepo('meris.git', 'run/data/meris')

    # install run/data/modis
    if options.aqua or options.terra:
        installGitRepo('modis.git', 'run/data/modis')

    # install run/data/aqua
    if options.aqua:
        installGitRepo('modisa.git', 'run/data/modisa')
        installGitRepo('hmodisa.git', 'run/data/hmodisa')

    # install run/data/terra
    if options.terra:
        installGitRepo('modist.git', 'run/data/modist')
        installGitRepo('hmodist.git', 'run/data/hmodist')

    # install run/data/mos
    if options.mos:
        installGitRepo('mos.git', 'run/data/mos')

    # install run/data/ocm1
    if options.ocm1:
        installGitRepo('ocm1.git', 'run/data/ocm1')

    # install run/data/ocm2
    if options.ocm2:
        installGitRepo('ocm2.git', 'run/data/ocm2')

    # install run/data/ocrvc
    if options.ocrvc:
        installGitRepo('ocrvc.git', 'run/data/ocrvc')

    # install run/data/octs
    if options.octs:
        installGitRepo('octs.git', 'run/data/octs')

    # install run/data/osmi
    if options.osmi:
        installGitRepo('osmi.git', 'run/data/osmi')

    # install run/data/seawifs
    if options.seawifs:
        installGitRepo('seawifs.git', 'run/data/seawifs')

    # install run/data/viirsn
    if options.viirsn:
        installGitRepo('viirsn.git', 'run/data/viirsn')

    # download bin dir
    repo = 'bin-' + arch + '.git'
    dirStr = 'run/bin/' + arch
    installGitRepo(repo, dirStr)
   
    # download bin dir3
    repo = 'bin3-' + arch + '.git'
    dirStr = 'run/bin3/' + arch
    installGitRepo(repo, dirStr)
   
    # install the luts
    commandStr = os.path.join(installDir, 'run/scripts/ocssw_runner')
    commandStr += ' --ocsswroot ' + installDir
    commandStr += ' update_luts.py '
    if options.seawifs:
        retval = os.system(commandStr + 'seawifs')
        if retval != 0:
            print 'Error - Could not install luts for seawifs'
            exit(1)

    if options.aqua:
        retval = os.system(commandStr + 'aqua')
        if retval != 0:
            print 'Error - Could not install luts for aqua'
            exit(1)

    if options.terra:
        retval = os.system(commandStr + 'terra')
        if retval != 0:
            print 'Error - Could not install luts for terra'
            exit(1)

    if options.viirsn:
        retval = os.system(commandStr + 'viirsn')
        if retval != 0:
            print 'Error - Could not install luts for viirsn'
            exit(1)

    if options.aquarius:
        retval = os.system(commandStr + 'aquarius')
        if retval != 0:
            print 'Error - Could not install luts for aquarius'
            exit(1)

    exit(0)
    
