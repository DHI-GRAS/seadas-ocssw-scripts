#! /usr/bin/env python

from optparse import OptionParser
import os
import subprocess
import sys
import hashlib
import shutil

verbose = False
installDir = None
gitBase = None
gitBranch = None
curlCommand = 'curl -O --retry 5 --retry-delay 5 '
checksumFileName = 'bundles.sha256sum'
checksumDict = {}
downloadTries = 2
local = None
FNULL = open(os.devnull, 'w')


# globals for progress display
numThings = 1
currentThing = 1

def loadChecksums():
    """
    Download and read the bundle checksums into checksumDict.
    """
    global checksumDict, csFile
    installFile(checksumFileName, continueFlag=False)

    if verbose:
        print 'Loading checksum file.'
    try:
        csFile = open(os.path.join(installDir, checksumFileName), 'r')
    except IOError:
        print "Bundle checksum file (" + checksumFileName + ") not downloaded"
        exit(1)
    for line in csFile:
        parts = line.strip().split()
        if len(parts) == 2:
            checksumDict[parts[1]] = parts[0]
    csFile.close()

def testFileChecksum(fileName):
    """
    test the checksum on the given bundle file.
    """
    global checksumDict, bundleFile
    if verbose:
        print 'comparing checksum for ' + fileName
    if fileName not in checksumDict:
        print fileName + ' is not in the checksum file.'
        exit(1)

    bundleDigest = checksumDict[fileName]
    blocksize = 65536
    hasher = hashlib.sha256()
    try:
        bundleFile = open(os.path.join(installDir, fileName), 'rb')
    except IOError:
        print "Bundle file (" + fileName + ") not downloaded"
        exit(1)

    buf = bundleFile.read(blocksize)
    while len(buf) > 0:
        hasher.update(buf)
        buf = bundleFile.read(blocksize)
    digest = hasher.hexdigest()
    bundleFile.close()
    if digest != bundleDigest:
        print 'Checksum for ' + fileName + ' does not match'
        return False
    return True

def makeDir(dirName):
    """
    Creates the directory if needed.
    """
    fullDir = os.path.join(installDir, dirName)
    if not os.path.isdir(fullDir):
        if verbose:
            print 'Creating directory', fullDir
        os.makedirs(fullDir)

def deleteFile(fileName):
    """
    Delete file from the install dir
    """
    try:
        os.remove(os.path.join(installDir, fileName))
    except Exception:
        pass

def installFile(fileName, continueFlag=True):
    """
    Downloads the file to the install dir
    """
    if verbose:
        if local:
            print 'Installing', fileName, ' from ', local
        else:
            print 'Downloading', fileName

    commandStr = 'cd ' + installDir + '; ' + curlCommand
    if continueFlag:
        commandStr += '-C - '
    commandStr += gitBase + fileName
    if local:
        commandStr = "cp %s %s" % (os.path.join(local, fileName), installDir)
    retval = os.system(commandStr)
    if retval:
        print 'Error - Could not run \"' + commandStr + '\"'
        exit(1)

def installGitRepo(repoName, dirName):
    """
    Installs or updates the repo into dirName.
    """
    fullDir = os.path.join(installDir, dirName)
    if os.path.isdir(fullDir):
        if local:
            print "Not updating Git Repository, in local mode"
        else:
            if subprocess.call(['svn', 'info'], cwd=fullDir, stdout=FNULL, stderr=subprocess.STDOUT) == 0:
                print "aborting - " + fullDir + " is an svn repository."
                exit(1)
    
            # save any local modifications using git stash
            cmd = ['git', 'stash']
            stashOutput = subprocess.Popen(cmd, stdout=subprocess.PIPE, cwd=fullDir).communicate()[0]
            if not stashOutput.startswith('No local changes to save'):
                if verbose:
                    print "Saved local changes with \"git stash\""
    
            # directory exists try a git fetch.
            commandStr = 'cd ' + fullDir + '; git fetch'
            if verbose:
                print "Updating (fetch) existing repository - ", fullDir
            else:
                commandStr += ' -q > /dev/null'
            retval = os.system(commandStr)
            if retval:
                print 'Error - Could not run \"' + commandStr + '\"'
                exit(1)

            # try a git chechout.
            commandStr = 'cd ' + fullDir + '; git checkout -t -B ' + gitBranch + ' remotes/origin/' + gitBranch
            if verbose:
                print "Switching to branch - ", gitBranch
            else:
                commandStr += ' -q > /dev/null'
            retval = os.system(commandStr)
            if retval:
                print 'Error - Could not run \"' + commandStr + '\"'
                exit(1)
            
            # try a git pull.
            commandStr = 'cd ' + fullDir + '; git pull --progress'
            if verbose:
                print "Pulling from remote repository"
            else:
                commandStr += ' -q > /dev/null'
            retval = os.system(commandStr)
            if retval:
                print 'Error - Could not run \"' + commandStr + '\"'
                exit(1)
    
            # restore local modifications using git stash pop
            if not stashOutput.startswith('No local changes to save'):
                cmd = ['git', 'stash', 'pop']
                if verbose:
                    print "Restoring local changes with \"git stash pop\""
                    stashStatus = subprocess.Popen(cmd, cwd=fullDir).communicate()[0]
                else:
                    stashStatus = subprocess.Popen(cmd, stdout=subprocess.PIPE, cwd=fullDir).communicate()[0]

    else:
        # directory does not exist
        if verbose:
            if local:
                print "Installing new directory - ", fullDir
            else:
                print "Downloading new directory - ", fullDir

        # download bundle
        testFailed = True
        count = 0
        while count < downloadTries:
            count += 1
            installFile(repoName + '.bundle')
            if testFileChecksum(repoName + '.bundle'):
                testFailed = False
                break
            deleteFile(repoName + '.bundle')

        if testFailed:
            print "Tried to download " + repoName + ".bundle " + str(downloadTries) + " times, but failed checksum"
            exit(1)

        # git clone
        commandStr = 'cd ' + installDir + '; '
        commandStr += 'git clone --progress -b master ' + repoName + '.bundle ' + fullDir
        retval = os.system(commandStr)
        if retval:
            print 'Error - Could not run \"' + commandStr + '\"'
            exit(1)

        # remove bundle
        deleteFile(repoName + '.bundle')

        # set remote repo to http location
        commandStr = 'cd ' + fullDir + '; '
        commandStr += 'git remote set-url origin ' + gitBase + repoName + '.git'
        retval = os.system(commandStr)
        if retval:
            print 'Error - Could not run \"' + commandStr + '\"'
            exit(1)

        # git pull to make sure we are up to date
        if local:
            print 'Not updating Git Repository, in local mode'
        else:
            # try a git fetch.
            commandStr = 'cd ' + fullDir + '; git fetch'
            if verbose:
                print "Updating (fetch) existing repository -", fullDir
            else:
                commandStr += ' -q > /dev/null'
            retval = os.system(commandStr)
            if retval:
                print 'Error - Could not run \"' + commandStr + '\"'
                exit(1)

            # try a git chechout.
            commandStr = 'cd ' + fullDir + '; git checkout -t -B ' + gitBranch + ' remotes/origin/' + gitBranch
            if verbose:
                print "Switching to branch - ", gitBranch
            else:
                commandStr += ' -q > /dev/null'
            retval = os.system(commandStr)
            if retval:
                print 'Error - Could not run \"' + commandStr + '\"'
                exit(1)
            
            # try a git pull.
            commandStr = 'cd ' + fullDir + '; git pull --progress > /dev/null'
            if verbose:
                print "Pulling from remote repository -", fullDir
            else:
                commandStr += ' -q > /dev/null'
            retval = os.system(commandStr)
            if retval:
                print 'Error - Could not run \"' + commandStr + '\"'
                exit(1)

def getArch():
    """
    Return the system arch string.
    """
    (sysname, nodename, release, version, machine) = os.uname()
    if sysname == 'Darwin':
        if machine == 'x86_64' or machine == 'i386':
            return 'macosx_intel'
        print "unsupported Mac machine =", machine
        exit(1)
    if sysname == 'Linux':
        if machine == 'x86_64':
            return 'linux_64'
        return 'linux'
    if sysname == 'Windows':
        print "Error: can not install OCSSW software on Windows"
        exit(1)
    print '***** unrecognized system =', sysname, ', machine =', machine
    print '***** defaulting to linux_64'
    return 'linux_64'

def printProgress(name):
    """
    Prints out a progress string and incriments currentThing global.
    """
    global currentThing
    global numThings
    print 'Installing ' + name + ' (' + str(currentThing) + ' of ' + str(numThings) + ')'
    sys.stdout.flush()
    currentThing += 1


if __name__ == "__main__":

    # Read commandline options...
    version = "%prog 2.0"
    usage = '''usage: %prog [options]'''
    parser = OptionParser(usage=usage, version=version)

    parser.add_option("-v", "--verbose", action="store_true", dest="verbose",
                      default=False, help="Print more information while running")
    parser.add_option("-i", "--install-dir", action="store",
                      dest="install_dir",
                      help="destination directory for install. Defaults to $OCSSWROOT or \"$HOME/ocssw\" if neither are given.")
    parser.add_option("-g", "--git-base", action="store", dest="git_base",
                      default="http://oceandata.sci.gsfc.nasa.gov/ocssw/",
                      help="web location for the git repositories")
    parser.add_option("-b", "--git-branch", action="store", dest="git_branch",
                      default="master",
                      help="branch in the git repositories to checkout")
    parser.add_option("-a", "--arch", action="store", dest='arch',
                      help="set system architecture (linux, linux_64, macosx_intel)")
    parser.add_option("-s", "--src", action="store_true", dest='src',
                      default=False, help="install source code")
    parser.add_option("-l","--local", action="store", dest="local",
                      default=None, help="local directory containing previously downloaded bundles")
    parser.add_option("-c", "--clean", action="store_true", dest="clean",
                      default=False, help="Do a clean install by deleting the install directory first, if it exists")

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
    if not gitBase.endswith('/'):
        gitBase += '/'
    gitBranch = options.git_branch

    verbose = options.verbose
    local = options.local

    # set installDir using param or a default
    if options.install_dir:
        installDir = os.path.abspath(options.install_dir)
    else:
        if os.getenv("OCSSWROOT") is None:
            installDir = os.path.abspath(os.path.join(os.getenv("HOME"), "ocssw"))
        else:
            installDir = os.path.abspath(os.getenv("OCSSWROOT"))

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
        print 'gitBranch   =', gitBranch
        print 'install dir =', installDir
        print 'arch        =', arch
        if local:
            print 'local dir   =', local
        print

    # remove the install directory if --clean and it exists
    if options.clean:
        if os.path.exists(installDir):
            shutil.rmtree(installDir)

    # create directory structure
    makeDir('run/data')
    makeDir('run/bin')
    makeDir('run/bin3')

    # add a few places to the path to help find git
    os.environ['PATH'] += ':' + os.environ['HOME'] + '/bin:/opt/local/bin:/usr/local/git/bin:/usr/local/bin:/sw/bin'

    # make sure git exists and is setup
    commandStr = "git --version > /dev/null"
    retval = os.system(commandStr)
    if retval:
        print 'Error - Could not execute system command \"' + commandStr + '\"'
        exit(1)

    cmd = ['git', 'config', "--get", "user.name"]
    gitResult = subprocess.Popen(cmd, stdout=subprocess.PIPE).communicate()[0]
    if verbose:
        print "git user.name = \"" + gitResult.rstrip() + "\""
    if gitResult == "":
        commandStr = "git config --global user.name \"Default Seadas User\""
        retval = os.system(commandStr)
        if retval:
            print 'Error - Could not execute system command \"' + commandStr + '\"'
            exit(1)

    cmd = ['git', 'config', "--get", "user.email"]
    gitResult = subprocess.Popen(cmd, stdout=subprocess.PIPE).communicate()[0]
    if verbose:
        print "git user.email = \"" + gitResult.rstrip() + "\""
    if gitResult == "":
        commandStr = "git config --global user.email \"seadas-user@localhost\""
        retval = os.system(commandStr)
        if retval:
            print 'Error - Could not execute system command \"' + commandStr + '\"'
            exit(1)

    # setup progress monitor output
    currentThing = 1
    numThings = 1

    numThings += 1         # bundle checksum file
    numThings += 1         # common
    numThings += 1         # OCSSW_bash.env
    numThings += 1         # README
    if options.src:
        numThings += 1     # src
    numThings += 1         # ocrvc
    if options.aquarius:
        numThings += 2     # aquarius + luts
    if options.avhrr:
        numThings += 1     # avhrr
    if options.czcs:
        numThings += 1     # czcs
    if options.eval:
        numThings += 1     # eval
    if options.goci:
        numThings += 1     # goci
    if options.hico:
        numThings += 2     # hico
    if options.meris:
        numThings += 1     # meris
    if options.aqua or options.terra:
        numThings += 1     # modis
    if options.aqua:
        numThings += 3     # aqua + luts
    if options.terra:
        numThings += 3     # terra + luts
    if options.mos:
        numThings += 1     # mos
    if options.ocm1:
        numThings += 1     # ocm1
    if options.ocm2:
        numThings += 1     # ocm2
    if options.octs:
        numThings += 1     # octs
    if options.osmi:
        numThings += 1     # osmi
    if options.seawifs:
        numThings += 2     # seawifs and luts
    if options.viirsn:
        numThings += 2     # viirsn + luts
    numThings += 1         # bin
    numThings += 1         # bin3
    numThings += 1         # scripts

    # download checksum file
    printProgress(checksumFileName)
    loadChecksums()

    # install run/data/common
    # the git install checks to see if the dir is svn and bails
    printProgress('common')
    installGitRepo('common', 'run/data/common')

    # download OCSSW_bash.env
    printProgress('OCSSW_bash.env')
    installFile('OCSSW_bash.env', continueFlag=False)

    # download README
    printProgress('README')
    installFile('README', continueFlag=False)

    # install build source directory
    if options.src:
        printProgress('src')
        installGitRepo('build', 'build')

    # install run/data/ocrvc
    printProgress('ocrvc')
    installGitRepo('ocrvc', 'run/data/ocrvc')

    # install run/data/aquarius
    if options.aquarius:
        printProgress('aquarius')
        installGitRepo('aquarius', 'run/data/aquarius')

    # install run/data/avhrr
    if options.avhrr:
        printProgress('avhrr')
        installGitRepo('avhrr', 'run/data/avhrr')

    # install run/data/czcs
    if options.czcs:
        printProgress('czcs')
        installGitRepo('czcs', 'run/data/czcs')

    # install run/data/eval
    if options.eval:
        printProgress('eval')
        installGitRepo('eval', 'run/data/eval')

    # install run/data/goci
    if options.goci:
        printProgress('goci')
        installGitRepo('goci', 'run/data/goci')

    # install run/data/hico
    if options.hico:
        printProgress('hico')
        installGitRepo('hico', 'run/data/hico')
        printProgress('hicohs')
        installGitRepo('hicohs', 'run/data/hicohs')

    # install run/data/meris
    if options.meris:
        printProgress('meris')
        installGitRepo('meris', 'run/data/meris')

    # install run/data/modis
    if options.aqua or options.terra:
        printProgress('modis')
        installGitRepo('modis', 'run/data/modis')

    # install run/data/aqua
    if options.aqua:
        printProgress('modisa')
        installGitRepo('modisa', 'run/data/modisa')
        printProgress('hmodisa')
        installGitRepo('hmodisa', 'run/data/hmodisa')

    # install run/data/terra
    if options.terra:
        printProgress('modist')
        installGitRepo('modist', 'run/data/modist')
        printProgress('hmodist')
        installGitRepo('hmodist', 'run/data/hmodist')

    # install run/data/mos
    if options.mos:
        printProgress('mos')
        installGitRepo('mos', 'run/data/mos')

    # install run/data/ocm1
    if options.ocm1:
        printProgress('ocm1')
        installGitRepo('ocm1', 'run/data/ocm1')

    # install run/data/ocm2
    if options.ocm2:
        printProgress('ocm2')
        installGitRepo('ocm2', 'run/data/ocm2')

    # install run/data/octs
    if options.octs:
        printProgress('octs')
        installGitRepo('octs', 'run/data/octs')

    # install run/data/osmi
    if options.osmi:
        printProgress('osmi')
        installGitRepo('osmi', 'run/data/osmi')

    # install run/data/seawifs
    if options.seawifs:
        printProgress('seawifs')
        installGitRepo('seawifs', 'run/data/seawifs')

    # install run/data/viirsn
    if options.viirsn:
        printProgress('viirsn')
        installGitRepo('viirsn', 'run/data/viirsn')

    # download bin dir
    repo = 'bin-' + arch
    dirStr = 'run/bin/' + arch
    printProgress('bin')
    installGitRepo(repo, dirStr)

    # download bin dir3
    repo = 'bin3-' + arch
    dirStr = 'run/bin3/' + arch
    printProgress('bin3')
    installGitRepo(repo, dirStr)

    #####################################################
    # install the scripts last since it is used as
    # an install sanity check
    #####################################################

    # install run/scripts
    printProgress('scripts')
    installGitRepo('scripts', 'run/scripts')

    # check that shared libc version will work
    commandStr = os.path.join(installDir, 'run', 'bin3', arch, 'hdp')
    commandStr += ' -H list > /dev/null'
    if verbose:
        print 'Checking that an installed executable can run'
    retval = os.system(commandStr)
    if retval:
        print 'Error - Can not run an installed executable'
        exit(1)

    # check the version of python
    commandStr = os.path.join(installDir, 'run/scripts/ocssw_runner')
    commandStr += ' --ocsswroot ' + installDir
    commandStr += ' pyverchk.py'
    if verbose:
        print 'Checking Python version'
    retval = os.system(commandStr)
    if retval:
        print 'Error - Python version is not new enough to install luts'
        exit(1)

    # install the luts
    if local:
        print "Not updating LUTs, in local mode"
    else:
        commandStr = os.path.join(installDir, 'run/scripts/ocssw_runner')
        commandStr += ' --ocsswroot ' + installDir
        commandStr += ' update_luts.py '
        if options.seawifs:
            printProgress('seawifs-luts')
            retval = os.system(commandStr + 'seawifs')
            if retval:
                print 'Error - Could not install luts for seawifs'
                exit(1)
    
        if options.aqua:
            printProgress('aqua-luts')
            retval = os.system(commandStr + 'aqua')
            if retval:
                print 'Error - Could not install luts for aqua'
                exit(1)
    
        if options.terra:
            printProgress('terra-luts')
            retval = os.system(commandStr + 'terra')
            if retval:
                print 'Error - Could not install luts for terra'
                exit(1)
    
        if options.viirsn:
            printProgress('viirsn-luts')
            retval = os.system(commandStr + 'viirsn')
            if retval:
                print 'Error - Could not install luts for viirsn'
                exit(1)
    
        if options.aquarius:
            printProgress('aquarius-luts')
            retval = os.system(commandStr + 'aquarius')
            if retval:
                print 'Error - Could not install luts for aquarius'
                exit(1)

    exit(0)

