#! /usr/bin/env python
# Retrieve files from an OBPG data subscription

from __future__ import print_function
from optparse import OptionParser
import os
import sys
from modules.ProcUtils import httpdl
import ftplib

if __name__ == "__main__":

    req_version = (2,5)
    cur_version = sys.version_info

    if (cur_version[0] > req_version[0] or
        (cur_version[0] == req_version[0] and
        cur_version[1] >= req_version[1])):
            from sqlite3 import *
            pass
    else:
        print("Your python interpreter is too old.")
        print("This script requires at least version 2.5.")
        print("Please consider upgrading.")
        sys.exit(1)


    database = 'retrievedFiles.db'
    getfileurl = 'http://oceandata.sci.gsfc.nasa.gov/cgi/getfile'
    ftpurl = 'oceans.domain.pub'


    initiate = False
    verbose = False
    subscriptionID = None
    regetdate = None
    outputdir = '.'

# Read commandline options...
    version = "%prog 1.0"
    usage = '''usage: %prog [options] orderID

    Requires ProcUtils module, be sure to include it in the $PYTHONPATH
    Requires at least python version 2.5 - as it uses the built-in sqlite3'''
    parser = OptionParser(usage=usage, version=version)

    parser.add_option("-i", "--initiate", action="store_true", dest="initiate",
                      help="initiate retreived file database - deletes previous data",
                      )

    parser.add_option("-v", "--verbose", action="store_true", dest="verbose",
                      help="Little Miss Chatterbox...",
                      )

    parser.add_option("-o", "--output-dir", dest="outputdir",
                      help="local download directory, default is the current working directory",
                      metavar="outdir")
    parser.add_option("-f", "--ftpURL", dest="ftpurl",
                      help="base FTP url, default ftp://oceans.gsfc.nasa.gov/subscriptions", metavar="ftpurl")
    parser.add_option("-g", "--getfileURL", dest="getfileurl",
                      help="base getfile url, default http://oceandata.sci.gsfc.nasa.gov/cgi/getfile", metavar="getfileurl")
    parser.add_option("-r", "--reget-date", dest="regetdate",
                      help="re-retrieve files since date", metavar="regetdate")
    parser.add_option("-d", "--database", dest="database",
                      help="database file", metavar="database")


    (options, args) = parser.parse_args()


    if len(args):
        subscriptionID = args[0]

    if options.verbose:
        verbose = options.verbose
    if options.initiate:
        initiate = options.initiate
    if options.regetdate:
        regetdate = options.regetdate
    if options.outputdir:
        outputdir = options.outputdir
    if options.ftpurl:
        ftpurl = options.ftpurl
    if options.getfileurl:
        getfileurl = options.getfileurl
    if options.database:
        database = options.database

    if initiate:
        try:
            if verbose:
                print ("Removing %s database" % database)
                os.remove(database)
        except Exception:
            pass


    if subscriptionID is None:
        print ("Subscription ID required!\nExiting...")
        exit(1)

    suburl = '/'.join(['subscriptions', subscriptionID, ''])
    if verbose:
        print ("Searching %s for new files..." % suburl)

    ftp = ftplib.FTP(ftpurl)
    ftp.login()
    files = []

    try:
        files = ftp.nlst(suburl)
    except ftplib.error_perm as resp:
        if str(resp) == "550 No files found":
            print ("no files in this directory")
            exit(1)
        else:
            raise

    if os.path.isfile(database):
        conn = connect(database)
        curs = conn.cursor()
        if verbose:
            print ("Using database: %s" % database)
    else:
        conn = connect(database)
        curs = conn.cursor()
        if verbose:
            print ("creating database %s..." % database)
        curs.execute('''create table ftpFiles
                    (createDate datetime,
                     filename text)''')
        conn.commit()

    if regetdate:
        curs.execute('delete from ftpFiles where createDate >= ?', [regetdate])
        conn.commit()
        if verbose:
            print ("deleted records retrieved after %s" % regetdate)

    for file in files:
        dt = datetime.datetime.utcnow()
        file.strip()
        filestr = file.replace('@', '')
        filestr = file.replace(suburl, '')
        cmd = 'select filename from ftpFiles where filename = "%s"' % filestr
        result = curs.execute(cmd)

        count = result.fetchone()
        if count is None:
            curs.execute('insert into ftpFiles values (?,?)', [dt, filestr])
            conn.commit()
            url = '/'.join([getfileurl, filestr])
            outfile = '/'.join([outputdir, filestr])
            status = httpdl(url, localpath=outputdir)
            if status != filestr:
                curs.execute('delete from ftpFiles where filename = ?', [filestr])
                conn.commit()
                if verbose:
                    print ("Trouble retrieving %s" % url)
            else:
                if verbose:
                    print ("Sucessfully retrieved %s" % url)
        else:
            if verbose:
                print ("Duplicate file, skipping download: %s" % filestr)
    conn.close()
