#! /usr/bin/env python
from __future__ import print_function

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
downloadCommand = ''
downloadContinueStr = ''
checksumFileName = 'bundles.sha256sum'
checksumDict = {}
downloadTries = 5
local = None
doNotUpdateRepos = False
FNULL = open(os.devnull, 'w')
newDirStructure = True
saveDir = None

# globals for progress display
numThings = 1
currentThing = 1

def setupCurlDownload():
    """
    set the global variables to use curl for downloading files.
    """
    global downloadCommand, downloadContinueStr
    downloadCommand = 'curl -O --retry 5 --retry-delay 5 '
    downloadContinueStr = '-C - '
  
def setupWgetDownload():
    """
    set the global variables to use wget for downloading files.
    """
    global downloadCommand, downloadContinueStr
    downloadCommand = 'wget --tries=5 --wait=5 '
    downloadContinueStr = '--continue '

def loadChecksums():
    """
    Download and read the bundle checksums into checksumDict.
    """
    global checksumDict, csFile
    installFile(checksumFileName, continueFlag=False)

    if verbose:
        print('Loading checksum file.')
    try:
        csFile = open(os.path.join(installDir, checksumFileName), 'r')
    except IOError:
        print("Bundle checksum file (" + checksumFileName + ") not downloaded")
        exit(1)
    for line in csFile:
        parts = line.strip().split()
        if len(parts) == 2:
            checksumDict[parts[1]] = parts[0]
    csFile.close()
    deleteFile(checksumFileName)

def testFileChecksum(fileName):
    """
    test the checksum on the given bundle file.
    """
    global checksumDict, bundleFile
    if verbose:
        print('comparing checksum for ' + fileName)
    if fileName not in checksumDict:
        print(fileName + ' is not in the checksum file.')
        exit(1)

    bundleDigest = checksumDict[fileName]
    blocksize = 65536
    hasher = hashlib.sha256()
    try:
        bundleFile = open(os.path.join(installDir, fileName), 'rb')
    except IOError:
        print("Bundle file (" + fileName + ") not downloaded")
        exit(1)

    buf = bundleFile.read(blocksize)
    while len(buf) > 0:
        hasher.update(buf)
        buf = bundleFile.read(blocksize)
    digest = hasher.hexdigest()
    bundleFile.close()
    if digest != bundleDigest:
        print('Checksum for ' + fileName + ' does not match')
        return False
    return True

def makeDir(dirName):
    """
    Creates the directory if needed.
    """
    fullDir = os.path.join(installDir, dirName)
    if not os.path.isdir(fullDir):
        if verbose:
            print('Creating directory', fullDir)
        os.makedirs(fullDir)

def deleteFile(fileName):
    """
    Delete file from the install dir
    """
    try:
        if saveDir:
            shutil.move(os.path.join(installDir, fileName), saveDir)
        else:
            os.remove(os.path.join(installDir, fileName))
    except Exception:
        pass

def installFile(fileName, continueFlag=True):
    """
    Downloads the file to the install dir
    """
    if verbose:
        if local:
            print('Installing', fileName, ' from ', local)
        else:
            print('Downloading', fileName)
    if not continueFlag:
        deleteFile(fileName)
    commandStr = 'cd ' + installDir + '; ' + downloadCommand
    if continueFlag:
        commandStr += downloadContinueStr
    commandStr += gitBase + fileName
    if local:
        commandStr = "cp %s %s" % (os.path.join(local, fileName), installDir)
    retval = os.system(commandStr)
    if retval != 0:
        print('Error - Executing command \"' + commandStr + '\"')
        return False
    return True

def installGitRepo(repoName, dirName):
    """
    Installs or updates the repo into dirName.
    """
    fullDir = os.path.join(installDir, dirName)
    if os.path.isdir(fullDir):
        if doNotUpdateRepos:
            print("Not updating Git Repository, no-update requested")
        else:
            # save any local modifications using git stash
            cmd = ['git', 'stash']
            stashOutput = subprocess.Popen(cmd, stdout=subprocess.PIPE, cwd=fullDir).communicate()[0].decode("utf-8")
            if not stashOutput.startswith('No local changes to save'):
                if verbose:
                    print("Saved local changes with \"git stash\"")
    
            # set remote repo to http location
            commandStr = 'cd ' + fullDir + '; '
            commandStr += 'git remote set-url origin ' + gitBase + repoName + '.git'
            retval = os.system(commandStr)
            # directory exists try a git fetch.
            commandStr = 'cd ' + fullDir + '; git fetch'
            if verbose:
                print("Updating (fetch) existing repository - ", fullDir)
            else:
                commandStr += ' -q > /dev/null'
            retval = os.system(commandStr)
            if retval:
                print('Error - Could not run \"' + commandStr + '\"')
                exit(1)

            # try a git chechout.
            commandStr = 'cd ' + fullDir + '; git checkout -t -B ' + gitBranch + ' remotes/origin/' + gitBranch
            if verbose:
                print("Switching to branch - ", gitBranch)
            else:
                commandStr += ' -q > /dev/null'
            retval = os.system(commandStr)
            if retval:
                print('Error - Could not run \"' + commandStr + '\"')
                exit(1)
            
            # try a git pull.
            commandStr = 'cd ' + fullDir + '; git pull --progress'
            if verbose:
                print("Pulling from remote repository")
            else:
                commandStr += ' -q > /dev/null'
            retval = os.system(commandStr)
            if retval:
                print('Error - Could not run \"' + commandStr + '\"')
                exit(1)
                
    else:
        # directory does not exist
        if verbose:
            if local:
                print("Installing new directory - ", fullDir)
            else:
                print("Downloading new directory - ", fullDir)

        # download bundle
        testFailed = True
        count = 0
        while count < downloadTries:
            count += 1
            retval = installFile(repoName + '.bundle')
            if retval == False:
                continue
            if testFileChecksum(repoName + '.bundle'):
                testFailed = False
                break
            deleteFile(repoName + '.bundle')

        if testFailed:
            print("Tried to download " + repoName + ".bundle " + str(downloadTries) + " times, but failed checksum")
            exit(1)

        # git clone
        commandStr = 'cd ' + installDir + '; '
        commandStr += 'git clone --progress -b master ' + repoName + '.bundle ' + fullDir
        retval = os.system(commandStr)
        if retval:
            print('Error - Could not run \"' + commandStr + '\"')
            exit(1)

        # remove bundle
        deleteFile(repoName + '.bundle')

        # set remote repo to http location
        commandStr = 'cd ' + fullDir + '; '
        commandStr += 'git remote set-url origin ' + gitBase + repoName + '.git'
        retval = os.system(commandStr)
        if retval:
            print('Error - Could not run \"' + commandStr + '\"')
            exit(1)

        # git pull to make sure we are up to date
        if doNotUpdateRepos:
            print('Not updating Git Repository, no-update requested')
        else:
            # try a git fetch.
            commandStr = 'cd ' + fullDir + '; git fetch'
            if verbose:
                print("Updating (fetch) existing repository -", fullDir)
            else:
                commandStr += ' -q > /dev/null'
            retval = os.system(commandStr)
            if retval:
                print('Error - Could not run \"' + commandStr + '\"')
                exit(1)

            # try a git chechout.
            commandStr = 'cd ' + fullDir + '; git checkout -t -B ' + gitBranch + ' remotes/origin/' + gitBranch
            if verbose:
                print("Switching to branch - ", gitBranch)
            else:
                commandStr += ' -q > /dev/null'
            retval = os.system(commandStr)
            if retval:
                print('Error - Could not run \"' + commandStr + '\"')
                exit(1)
            
            # try a git pull.
            commandStr = 'cd ' + fullDir + '; git pull --progress > /dev/null'
            if verbose:
                print("Pulling from remote repository -", fullDir)
            else:
                commandStr += ' -q > /dev/null'
            retval = os.system(commandStr)
            if retval:
                print('Error - Could not run \"' + commandStr + '\"')
                exit(1)

def getArch():
    """
    Return the system arch string.
    """
    (sysname, nodename, release, version, machine) = os.uname()
    if sysname == 'Darwin':
        if machine == 'x86_64' or machine == 'i386':
            return 'macosx_intel'
        print("unsupported Mac machine =", machine)
        exit(1)
    if sysname == 'Linux':
        if machine == 'x86_64':
            return 'linux_64'
        return 'linux'
    if sysname == 'Windows':
        print("Error: can not install OCSSW software on Windows")
        exit(1)
    print('***** unrecognized system =', sysname, ', machine =', machine)
    print('***** defaulting to linux_64')
    return 'linux_64'

def printProgress(name):
    """
    Prints out a progress string and incriments currentThing global.
    """
    global currentThing
    global numThings
    print('Installing ' + name + ' (' + str(currentThing) + ' of ' + str(numThings) + ')')
    sys.stdout.flush()
    currentThing += 1

def convertToNewDirStructure():
    if newDirStructure:
        # see if the current installation is the old dir structure
        # use scripts dir as the test
        if os.path.isdir(os.path.join(installDir, 'run', 'scripts')):
            print('Converting to new directory structure')

            # need to delete Aqua Terra VIIRS and MSI since those directories were reworked
            shutil.rmtree(os.path.join(installDir, 'run', 'data', 'hmodisa'), True)
            shutil.rmtree(os.path.join(installDir, 'run', 'data', 'hmodist'), True)
            shutil.rmtree(os.path.join(installDir, 'run', 'data', 'modis'), True)
            shutil.rmtree(os.path.join(installDir, 'run', 'data', 'modisa'), True)
            shutil.rmtree(os.path.join(installDir, 'run', 'data', 'modist'), True)
            shutil.rmtree(os.path.join(installDir, 'run', 'data', 'viirsn'), True)
            shutil.rmtree(os.path.join(installDir, 'run', 'data', 'msi'), True)
            
            # now move around the rest
            shutil.move(os.path.join(installDir, 'run', 'bin', getArch()), os.path.join(installDir, 'bin'))
            shutil.move(os.path.join(installDir, 'run', 'data'), os.path.join(installDir, 'share'))
            shutil.move(os.path.join(installDir, 'run', 'scripts'), os.path.join(installDir, 'scripts'))
            shutil.move(os.path.join(installDir, 'run', 'var'), os.path.join(installDir, 'var'))
            shutil.rmtree(os.path.join(installDir, 'run'), True)

            if os.path.isdir(os.path.join(installDir, 'build')):
                print('WARNING - old style build directory exists')
                print('WARNING - the directory has been moved to "build.old"')
                shutil.move(os.path.join(installDir, 'build'), os.path.join(installDir, 'build.old'))


if __name__ == "__main__":

    # Read commandline options...
    version = "%prog 3.0"
    usage = '''usage: %prog [options]'''
    parser = OptionParser(usage=usage, version=version)

    parser.add_option("-v", "--verbose", action="store_true", dest="verbose",
                      default=False, help="Print more information while running")
    parser.add_option("-i", "--install-dir", action="store",
                      dest="install_dir",
                      help="destination directory for install. Defaults to $OCSSWROOT or \"$HOME/ocssw\" if neither are given.")
    parser.add_option("-g", "--git-base", action="store", dest="git_base",
                      default="https://oceandata.sci.gsfc.nasa.gov/ocssw/",
                      help="web location for the git repositories")
    parser.add_option("-b", "--git-branch", action="store", dest="git_branch",
                      default="v7.5",
                      help="branch in the git repositories to checkout")
    parser.add_option("-a", "--arch", action="store", dest='arch',
                      help="set system architecture (linux, linux_64, macosx_intel)")
    parser.add_option("-s", "--src", action="store_true", dest='src',
                      default=False, help="install source code")
    parser.add_option("-l","--local", action="store", dest="local",
                      default=None, help="local directory containing previously downloaded bundles")
    parser.add_option("-c", "--clean", action="store_true", dest="clean",
                      default=False, help="Do a clean install by deleting the install directory first, if it exists")
    parser.add_option("--curl", action="store_true", dest='curl', 
                      default=False, help="use curl for download instead of wget")
    parser.add_option("--no-update", action="store_true", dest='noUpdate', 
                      default=False, help="do not update the git repositories or luts")
    parser.add_option("--save-dir", action="store", dest="save_dir",
                      help="destination directory to save all of the install files.")

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
    parser.add_option("--msis2a", action="store_true", dest="msis2a", default=False,
                      help="install MSI S2A files")
    parser.add_option("--msis2b", action="store_true", dest="msis2b", default=False,
                      help="install MSI S2B files")
    parser.add_option("--ocm1", action="store_true", dest="ocm1", default=False,
                      help="install OCM1 files")
    parser.add_option("--ocm2", action="store_true", dest="ocm2", default=False,
                      help="install OCM2 files")
    parser.add_option("--octs", action="store_true", dest="octs", default=False,
                      help="install OCTS files")
    parser.add_option("--olcis3a", action="store_true", dest="olcis3a", default=False,
                      help="install OLCI Sentinel 3A files")
    parser.add_option("--olcis3b", action="store_true", dest="olcis3b", default=False,
                      help="install OLCI Sentinel 3B files")
    parser.add_option("--oli", action="store_true", dest="oli", default=False,
                      help="install Landsat 8 OLI files")
    parser.add_option("--osmi", action="store_true", dest="osmi", default=False,
                      help="install OSMI files")
    parser.add_option("--seawifs", action="store_true", dest="seawifs",
                      default=False, help="install SeaWiFS files")
    parser.add_option("--viirsn", action="store_true", dest="viirsn",
                      default=False, help="install VIIRS NPP files")
    parser.add_option("--viirsj1", action="store_true", dest="viirsj1",
                      default=False, help="install VIIRS JPSS1 files")
    parser.add_option("--viirsdem", action="store_true", dest="viirsdem",
                      default=False, help="install VIIRS digital elevation map (DEM) files")
    parser.add_option("--direct-broadcast", action="store_true",
                      dest='direct_broadcast',
                      default=False, help="install direct broadcast files")

    (options, args) = parser.parse_args()

    # add a few places to the path to help find git
    os.environ['PATH'] += ':' + os.environ['HOME'] + '/bin:/opt/local/bin:/usr/local/git/bin:/usr/local/bin:/sw/bin'

    # set global variables
    gitBase = options.git_base
    if not gitBase.endswith('/'):
        gitBase += '/'
    gitBranch = options.git_branch

    # figure out if we are using the new directory structure
    # anything before v7.5 is the old structure
    newDirStructure = True
    parts = gitBranch[1:].split('.')
    if int(parts[0]) < 7:
        newDirStructure = False
    else:
        if int(parts[0]) == 7:
            if int(parts[1]) < 5:
                newDirStructure = False

    verbose = options.verbose
    doNotUpdateRepos = options.noUpdate
    local = options.local
    if local:
        doNotUpdateRepos = True
    
    # setup download command
    if options.curl:
        retval = os.system("which curl > /dev/null")
        if retval == 0:
            setupCurlDownload()
        else:
            print("Error: Could not find curl.")
            exit(1)
    else:
        retval = os.system("which wget > /dev/null")
        if retval == 0:
            setupWgetDownload()
        else:
            retval = os.system("which curl > /dev/null")
            if retval == 0:
                if verbose:
                    print('Could not find wget, defaulting to using curl.')
                setupCurlDownload()
            else:
                print("Error: Could not find wget or curl in the PATH.")
                exit(1)

    # set installDir using param or a default
    if options.install_dir:
        installDir = os.path.abspath(options.install_dir)
    else:
        if os.getenv("OCSSWROOT") is None:
            installDir = os.path.abspath(os.path.join(os.getenv("HOME"), "ocssw"))
        else:

            installDir = os.path.abspath(os.getenv("OCSSWROOT"))

    # check if this is a development git repo
    # bail if it is
    try:
        if subprocess.call(['git', 'status'], cwd=installDir, stdout=FNULL, stderr=subprocess.STDOUT) == 0:
            print("aborting - " + installDir + " is a development git repository.")
            exit(1)
    except OSError:
        pass

    if options.arch:
        arch = options.arch
    else:
        arch = getArch()

    # set direct broadcast
    if options.direct_broadcast:
        options.aqua = True
        options.terra = True

    # set the save directory
    if options.save_dir:
        saveDir = options.save_dir
        if not os.path.isdir(saveDir):
            if verbose:
                print('Creating directory', saveDir)
            os.makedirs(saveDir)
    
    # print out info if in verbose mode
    if verbose:
        print('\ngitBase     =', gitBase)
        print('gitBranch   =', gitBranch)
        print('install dir =', installDir)
        print('arch        =', arch)
        if doNotUpdateRepos:
            print('no-update   =', doNotUpdateRepos)
        if local:
            print('local dir   =', local)
        print()
        
    # remove the install directory if --clean and it exists
    if options.clean:
        if os.path.exists(installDir):
            shutil.rmtree(installDir)

    # convert to new directory structure if necessary
    convertToNewDirStructure()
    
    # create directory structure
    if newDirStructure:
        makeDir('share')
    else:
        makeDir('run/data')
        makeDir('run/bin')
        makeDir('run/bin3')
        
    # make sure git exists and is setup
    commandStr = "git --version > /dev/null"
    retval = os.system(commandStr)
    if retval:
        print('Error - git is either not installed or not in the PATH.')
        exit(1)

    cmd = ['git', 'config', "--get", "user.name"]
    gitResult = subprocess.Popen(cmd, stdout=subprocess.PIPE).communicate()[0].decode("utf-8")
    if verbose:
        print("git user.name = \"" + gitResult.rstrip() + "\"")
    if gitResult == "":
        commandStr = "git config --global user.name \"Default Seadas User\""
        retval = os.system(commandStr)
        if retval:
            print('Error - Could not execute system command \"' + commandStr + '\"')
            exit(1)

    cmd = ['git', 'config', "--get", "user.email"]
    gitResult = subprocess.Popen(cmd, stdout=subprocess.PIPE).communicate()[0].decode("utf-8")
    if verbose:
        print("git user.email = \"" + gitResult.rstrip() + "\"")
    if gitResult == "":
        commandStr = "git config --global user.email \"seadas-user@localhost\""
        retval = os.system(commandStr)
        if retval:
            print('Error - Could not execute system command \"' + commandStr + '\"')
            exit(1)

    # setup progress monitor output
    currentThing = 1
    numThings = 0

    numThings += 1         # bundle checksum file
    numThings += 1         # common
    numThings += 1         # OCSSW_bash.env
    numThings += 1         # ocrvc
    if options.aquarius:
        numThings += 1     # aquarius
        if not doNotUpdateRepos:
            numThings += 1 # luts
    if options.avhrr:
        numThings += 1     # avhrr
    if options.czcs:
        numThings += 1     # czcs
    if options.goci:
        numThings += 1     # goci
    if options.hico:
        numThings += 1     # hico
    if options.meris:
        numThings += 1     # meris
    if options.aqua or options.terra:
        numThings += 1     # modis
    if options.aqua:
        numThings += 1     # modis/aqua
        if not doNotUpdateRepos:
            numThings += 1 # luts
    if options.terra:
        numThings += 1     # modis/terra
        if not doNotUpdateRepos:
            numThings += 1 # luts
    if options.mos:
        numThings += 1     # mos
    if options.msis2a or options.msis2b:
        numThings += 1     # msi
    if options.msis2a:
        numThings += 1     # msis2a
    if options.msis2b:
        numThings += 1     # msis2b
    if options.ocm1:
        numThings += 1     # ocm1
    if options.ocm2:
        numThings += 1     # ocm2
    if options.octs:
        numThings += 1     # octs
    if options.olcis3a or options.olcis3b:
        numThings += 1     # olci
    if options.olcis3a:
        numThings += 1     # olci s3a
    if options.olcis3b:
        numThings += 1     # olci s3b
    if options.osmi:
        numThings += 1     # osmi
    if options.oli:
        numThings += 1     # oli
    if options.seawifs:
        numThings += 1     # seawifs
        if not doNotUpdateRepos:
            numThings += 1 # luts
    if options.viirsn or options.viirsj1 or options.viirsdem:
        numThings += 1     # viirs
    if options.viirsn:
        numThings += 1     # viirs/npp
        if not doNotUpdateRepos:
            numThings += 1 # luts
    if options.viirsj1:
        numThings += 1     # viirs/j1
        if not doNotUpdateRepos:
            numThings += 1 # luts
    if options.viirsdem:
        numThings += 1     # viirs/dem
    numThings += 1         # bin
    numThings += 1         # opt (or bin3)
    if options.src:
        numThings += 1     # src
        if newDirStructure:
            numThings += 1 # opt/src
    numThings += 1         # scripts

    shareDir = "share/"
    if not newDirStructure:
        shareDir = "run/data/"

    # download checksum file
    printProgress(checksumFileName)
    loadChecksums()

    # install share/common
    # the git install checks to see if the dir is svn and bails
    printProgress('common')
    installGitRepo('common', shareDir + 'common')

    # download OCSSW_bash.env
    printProgress('OCSSW_bash.env')
    tmpFile = 'OCSSW_bash.env.' + gitBranch
    installFile(tmpFile, continueFlag=False)
    tmpFile = os.path.join(installDir, tmpFile)
    if saveDir:
        shutil.copy2(tmpFile, saveDir)
    os.rename(tmpFile, os.path.join(installDir, 'OCSSW_bash.env'))
    
    # install share/ocrvc
    printProgress('ocrvc')
    installGitRepo('ocrvc', shareDir + 'ocrvc')

    # install share/aquarius
    if options.aquarius:
        printProgress('aquarius')
        installGitRepo('aquarius', shareDir + 'aquarius')

    # install share/avhrr
    if options.avhrr:
        printProgress('avhrr')
        installGitRepo('avhrr', shareDir + 'avhrr')

    # install share/czcs
    if options.czcs:
        printProgress('czcs')
        installGitRepo('czcs', shareDir + 'czcs')

    # install share/goci
    if options.goci:
        printProgress('goci')
        installGitRepo('goci', shareDir + 'goci')

    # install share/hico
    if options.hico:
        printProgress('hico')
        installGitRepo('hico', shareDir + 'hico')

    # install share/meris
    if options.meris:
        printProgress('meris')
        installGitRepo('meris', shareDir + 'meris')

    # install share/modis
    if options.aqua or options.terra:
        printProgress('modis')
        installGitRepo('modis', shareDir + 'modis')

    # install share/modis/aqua
    if options.aqua:
        printProgress('modis/aqua')
        if newDirStructure:
            installGitRepo('modisaqua', shareDir + 'modis/aqua')
        else:
            installGitRepo('modisa', shareDir + 'modisa')
            installGitRepo('hmodisa', shareDir + 'hmodisa')

    # install share/terra
    if options.terra:
        printProgress('modis/terra')
        if newDirStructure:
            installGitRepo('modisterra', shareDir + 'modis/terra')
        else:
            installGitRepo('modist', shareDir + 'modist')
            installGitRepo('hmodist', shareDir + 'hmodist')

    # install share/mos
    if options.mos:
        printProgress('mos')
        installGitRepo('mos', shareDir + 'mos')

    # install share/msi
    if options.msis2a or options.msis2b:
        printProgress('msi')
        if newDirStructure:
            installGitRepo('msis2', shareDir + 'msi')

    # install share/msis2a
    if options.msis2a:
        printProgress('msis2a')
        if newDirStructure:
            installGitRepo('msis2a', shareDir + 'msi/s2a')
        else:
            installGitRepo('msi', shareDir + 'msi')

    # install share/msis2b
    if options.msis2b:
        printProgress('msis2b')
        if newDirStructure:
            installGitRepo('msis2b', shareDir + 'msi/s2b')
        else:
            print("Error - Must install v7.5 or greater for MSI S2B")
            exit(1)

    # install share/ocm1
    if options.ocm1:
        printProgress('ocm1')
        installGitRepo('ocm1', shareDir + 'ocm1')

    # install share/ocm2
    if options.ocm2:
        printProgress('ocm2')
        installGitRepo('ocm2', shareDir + 'ocm2')

    # install share/octs
    if options.octs:
        printProgress('octs')
        installGitRepo('octs', shareDir + 'octs')

    # install share/olci
    if options.olcis3a or options.olcis3b:
        if newDirStructure:
            printProgress('olci')
            installGitRepo('olci', shareDir + 'olci')
        else:
            print("Error - Must install v7.5 or greater for OLCI")
            exit(1)
        
    # install share/olci/s3a
    if options.olcis3a:
        printProgress('olci/s3a')
        installGitRepo('olcis3a', shareDir + 'olci/s3a')

    # install share/olci/s3b
    if options.olcis3b:
        printProgress('olci/s3b')
        installGitRepo('olcis3b', shareDir + 'olci/s3b')

    # install share/osmi
    if options.osmi:
        printProgress('osmi')
        installGitRepo('osmi', shareDir + 'osmi')

    # install share/oli
    if options.oli:
        printProgress('oli')
        installGitRepo('oli', shareDir + 'oli')

    # install share/seawifs
    if options.seawifs:
        printProgress('seawifs')
        installGitRepo('seawifs', shareDir + 'seawifs')

    # install share/viirs
    if options.viirsn or options.viirsj1 or options.viirsdem:
        printProgress('viirs')
        if newDirStructure:
            installGitRepo('viirs', shareDir + 'viirs')

    # install share/viirs/npp
    if options.viirsn:
        printProgress('viirs/npp')
        if newDirStructure:
            installGitRepo('viirsnpp', shareDir + 'viirs/npp')
        else:
            installGitRepo('viirsn', shareDir + 'viirsn')

    # install share/viirs/j1
    if options.viirsj1:
        printProgress('viirs/j1')
        if newDirStructure:
            installGitRepo('viirsj1', shareDir + 'viirs/j1')
        else:
            print("Error - Must install v7.5 or greater for VIIRS J1")
            exit(1)

    # install share/viirs/dem
    if options.viirsdem:
        printProgress('viirs/dem')
        if newDirStructure:
            if not os.path.isdir(os.path.join(installDir, 'share', 'viirs', 'dem')):
                srcFileName = 'dem.tar.gz'
                installFile(srcFileName)
                commandStr = 'cd ' +  os.path.join(installDir, 'share', 'viirs') + '; tar xzf ../../' + srcFileName
                retval = os.system(commandStr)
                deleteFile(srcFileName)
                if retval:
                    print('Error - Can not expand share/viirs/dem directory')
                    exit(1)
            else:
                print('  skipping... share/viirs/dem already exists.')
        else:
            print("Error - Must install v7.5 or greater for VIIRS DEM")
            exit(1)

    # download bin dir
    printProgress('bin')
    if newDirStructure:
        installGitRepo('bin-' + arch, 'bin')
    else:
        installGitRepo('bin-' + arch, 'run/bin/' + arch)

    # download opt or bin3
    if newDirStructure:
        printProgress('opt')
        installGitRepo('opt-' + arch, 'opt')
    else:
        printProgress('bin3')
        installGitRepo('bin3-' + arch, 'run/bin3/' + arch)

    # install source directory
    if options.src:
        printProgress('src')
        if newDirStructure:
            installGitRepo('ocssw-src', 'ocssw-src')
            printProgress('opt-src')
            srcFileName = 'opt-src-' + gitBranch + '.tar'
            installFile(srcFileName)
            commandStr = 'cd ' +  os.path.join(installDir, 'opt') + '; tar xf ../' + srcFileName
            retval = os.system(commandStr)
            if retval:
                print('Error - Can not expand opt/src directory')
                exit(1)
            deleteFile(srcFileName)
        else:
            installGitRepo('build', 'build')


    #####################################################
    # install the scripts last since it is used as
    # an install sanity check
    #####################################################

    # install run/scripts
    printProgress('scripts')
    if newDirStructure:
        installGitRepo('scripts', 'scripts')
    else:
        installGitRepo('scripts', 'run/scripts')
        
    # check that shared libc version will work
    if newDirStructure:
        commandStr = os.path.join(installDir, 'scripts', 'ocssw_runner')
    else:
        commandStr = os.path.join(installDir, 'run', 'scripts', 'ocssw_runner')

    commandStr += ' --ocsswroot ' +  installDir + '  hdp -H list > /dev/null'

    if verbose:
        print('Checking that an installed executable can run')
    retval = os.system(commandStr)
    if retval:
        print('Error - Can not run an installed executable')
        exit(1)

    scriptsDir = os.path.join(installDir, 'run', 'scripts')
    if newDirStructure:
        scriptsDir = os.path.join(installDir, 'scripts')
        
    # check the version of python
    commandStr = os.path.join(scriptsDir, 'ocssw_runner')
    commandStr += ' --ocsswroot ' + installDir
    commandStr += ' pyverchk.py'
    if verbose:
        print('Checking Python version')
    retval = os.system(commandStr)
    if retval:
        print('Error - Python version is not new enough to install luts')
        exit(1)

    # install the luts
    if doNotUpdateRepos:
        print("Not updating LUTs, no-update requested")
    else:
        commandStr = os.path.join(scriptsDir, 'ocssw_runner')
        commandStr += ' --ocsswroot ' + installDir
        commandStr += ' update_luts.py '
        if options.seawifs:
            printProgress('seawifs-luts')
            retval = os.system(commandStr + 'seawifs')
            if retval:
                print('Error - Could not install luts for seawifs')
                exit(1)
    
        if options.aqua:
            printProgress('aqua-luts')
            retval = os.system(commandStr + 'aqua')
            if retval:
                print('Error - Could not install luts for aqua')
                exit(1)
    
        if options.terra:
            printProgress('terra-luts')
            retval = os.system(commandStr + 'terra')
            if retval:
                print('Error - Could not install luts for terra')
                exit(1)
    
        if options.viirsn:
            printProgress('viirsnpp-luts')
            retval = os.system(commandStr + 'viirsn')
            if retval:
                print('Error - Could not install luts for viirsn')
                exit(1)
    
        if options.viirsj1:
            printProgress('viirsj1-luts')
            retval = os.system(commandStr + 'viirsj1')
            if retval:
                print('Error - Could not install luts for viirsn')
                exit(1)
    
        if options.aquarius:
            printProgress('aquarius-luts')
            retval = os.system(commandStr + 'aquarius')
            if retval:
                print('Error - Could not install luts for aquarius')
                exit(1)

    exit(0)

