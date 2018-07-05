#! /usr/bin/env python
__author__ = 'sbailey'

import MySQLdb
import re
import os
import inspect
from modules.ParamUtils import ParamProcessing


class ancDB:
    def __init__(self, dbfile=None, local=False):
        """A small         self.dbfile = dbfile
set of functions to generate, update, and read from a local SQLite database of ancillary
        file information"""
        self.dbfile = dbfile
        self.local = local
        self.conn = None
        self.cursor = None

    def openDB(self,dbInitFile=".ancDBinit"):
        """
        Open connection to the ancillary DB and initiate a cursor
        """

        hostname="localhost"
        username="ancUser"
        password=""
        database="seadas_ancillary_data"
        socket="/tmp/mysql.sock"
        initpath = os.path.dirname(inspect.getfile(ancDB))
        pfile= '/'.join([initpath,dbInitFile])
        p = ParamProcessing(parfile=pfile)
        p.parseParFile()
        hash = p.params['main']
        if hash['hostname']:
            hostname = hash['hostname']
        if hash['username']:
            username = hash['username']
        if hash['password']:
            password = hash['password']
        if hash['database']:
            database = hash['database']
        if hash['socket']:
            socket = hash['socket']

        conn = MySQLdb.connect(host=hostname,user=username,passwd=password,db=database,unix_socket=socket)
        self.conn = conn
        c = conn.cursor()
        self.cursor = c
        return

    def closeDB(self):
        """
        Close the DB connection, committing changes.
        """
        conn = self.conn
        cursor = self.cursor
        conn.commit()
        cursor.close()

    def create_db(self):
        """
        Create the ancillary DB
        """
        if self.conn is None:
            print("No connection to database!")
            return 110

        c = self.cursor
        # Create  satfiles table
        c.execute('''CREATE TABLE IF NOT EXISTS satfiles
            (satid INT UNSIGNED PRIMARY KEY auto_increment,
            filename varchar(120) ,
            starttime BIGINT UNSIGNED,
            stoptime BIGINT UNSIGNED,
            status TINYINT,
            attephstat TINYINT)''')

        # Create  ancfiles table
        c.execute('''CREATE  TABLE IF NOT EXISTS ancfiles
            (ancid INT UNSIGNED PRIMARY KEY auto_increment,
            filename varchar(120) ,
            path varchar(256)  ,
            type varchar(10))''')

        # Create  satancinfo table
        c.execute('''CREATE  TABLE IF NOT EXISTS satancinfo
            (satid INT UNSIGNED ,
            ancid INT UNSIGNED  ,
            optimal tinyINT UNSIGNED,
            FOREIGN KEY(satID) REFERENCES satfiles(satid),
            FOREIGN KEY(ancID) REFERENCES ancfiles(ancid))''')

    def insert_record(self, satfile=None, starttime=None, stoptime=None, dbstat=0,
                      ancfile=None, ancpath=None, anctype=None, atteph=False):
        """
        Insert record into ancillary DB
        """
        if self.conn is None:
            print("No connection to database!")
            return 110

        c = self.cursor
        satid = self.check_file(satfile)
        ancid = self.check_file(ancfile, anctype=anctype)

        if satid is None:
            inputdbstat = dbstat
            attephstat = -1
            if atteph:
                attephstat = dbstat
                inputdbstat = -1
            print(satfile, starttime, stoptime, inputdbstat, attephstat)
            sqlcmd = 'INSERT INTO satfiles VALUES (NULL,"%s",%d,%d,%d,%d)' % (satfile, long(starttime), long(stoptime), int(inputdbstat), int(attephstat))
            print(sqlcmd)
            c.execute(sqlcmd)
            self.conn.commit()
            satid = ancDB.check_file(self, satfile)

        else:
            if atteph:
                sqlcmd = 'UPDATE satfiles set attephstat = %d' % int(dbstat)
                c.execute(sqlcmd)
            else:
                sqlcmd = 'UPDATE satfiles set status = %d' % int(dbstat)
                c.execute(sqlcmd)

            self.conn.commit()

        if ancid is None:
            sqlcmd = 'INSERT INTO ancfiles VALUES (NULL,"%s","%s","%s")' % (ancfile, ancpath, anctype)
            c.execute(sqlcmd)
            self.conn.commit()
            ancid = ancDB.check_file(self, ancfile, anctype=anctype)

        opt = self.check_dbrtn_status(dbstat, anctype)
        sqlcmd = 'SELECT * from satancinfo where satid = %d and ancid = %d' % (int(satid), int(ancid))
        result = c.execute(sqlcmd)

        if not result:
            sqlcmd = 'INSERT INTO satancinfo VALUES (%d,%d,%d)' % (int(satid), int(ancid), int(opt))
            c.execute(sqlcmd)


    def delete_record(self, filename, anctype=None):
        """
        Deletes records from ancillary DB
        If given a satellite filename, deletes all records associated with it
        If given an ancillary filename and keyword anc is set true, deletes only that ancillary record
        """
        if self.conn is None:
            print("No connection to database!")
            return 110

        c = self.cursor
        conn = self.conn

        if anctype:
            ancid = self.check_file(filename, anctype=anctype)
            sqlcmd = 'DELETE from satancinfo where ancid = %d' % int(ancid)
            c.execute(sqlcmd)
            sqlcmd = 'DELETE from ancfiles where ancid = %d' % int(ancid)
            c.execute(sqlcmd)

        else:
            satid = self.check_file(filename)
            sqlcmd = 'select ancid from satancinfo where satid = %d' % int(satid)
            c.execute(sqlcmd)
            ancids = c.fetchall()
            for a in ancids:
                sqlcmd = 'DELETE from satancinfo where ancid = %d'% int(a[0])
                c.execute(sqlcmd)
                sqlcmd = 'DELETE from ancfiles where ancid = %d' % int(a[0])
                c.execute(sqlcmd)
            sqlcmd = 'DELETE from satfiles where satid = %d' % int(satid)
            c.execute(sqlcmd)

        conn.commit()

    def check_dbrtn_status(self, dbstat, anctype):
        """
        Check the database return status.
        DB return status bitwise values:
            all bits off means all is well in the world
            value of -1 means have not checked for ancfiles yet
            Ancillary:
                bit 1 - missing one or more MET
                bit 2 - missing one or more OZONE
                bit 3 - missing SST
                bit 4 - missing NO2
                bit 5 - missing ICE
            Attitude-Ephemeris
                bit 1 - predicted attitude selected
                bit 2 - predicted ephemeris selected
                bit 4 - no attitude found
                bit 8 - no ephemeris found
                bit 16 - invalid mission
        """

        statchk = {'met': 1, 'ozone': 2, 'sstfile': 4, 'no2file': 8, 'icefile': 16, 'att': 1, 'eph': 2}

        if re.search("\d$", anctype):
            anctype = anctype[0:len(anctype) - 1]
        if dbstat & statchk[anctype]:
            return 0
        else:
            return 1


    def check_file(self, filename, anctype=None):
        """
        Check database for existing file, return ID if exists
        """
        if self.conn is None:
            print("No connection to database!")
            return 110

        c = self.cursor

        table = 'satfiles'
        id = 'satid'
        if anctype is None:
            query = ' '.join(['select', id, 'from', table, 'where filename =', '"' + filename + '"'])
        else:
            table = 'ancfiles'
            id = 'ancid'
            query = ' '.join(['select', id, 'from', table, 'where filename =', '"' + filename + '"', " and type = ",
                              '"' + anctype + '"'])


        result = c.execute(query)
        r = c.fetchone()

        if not result:
            return None
        else:
            return r[0]

    def get_status(self, filename, atteph=False):
        """
        Check the stored database return status
        """
        if self.conn is None:
            print("No connection to database!")
            return 110

        c = self.cursor
        if atteph:
            query = ' '.join(['select attephstat from satfiles where filename =', '"' + filename + '"'])
        else:
            query = ' '.join(['select status from satfiles where filename =', '"' + filename + '"'])

        result = c.execute(query)
        r = c.fetchone()

        if not result:
            return None
        else:
            return r[0]

    def get_filetime(self, filename):
        """
        return the stored file start and stop times
        """
        if self.conn is None:
            print("No connection to database!")
            return 110

        c = self.cursor
        query = ' '.join(['select starttime,stoptime from satfiles where filename =', '"' + filename + '"'])

        result = c.execute(query)
        if result:
            r = c.fetchone()
            return [r[0],r[1]]

    def get_ancfiles(self, filename, atteph=False):
        """
        Return the ancillary files associated with a given input file
        """
        import os
        if self.conn is None:
            print("No connection to database!")
            return None

        c = self.cursor

        satID = self.check_file(filename)
        if satID is None:
            return None

        filehash = {}
        sqlcmd = 'SELECT a.type, a.path, a.filename from ancfiles a, satancinfo s where a.ancid = s.ancid and s.satid = %d' % int(satID)
        c.execute(sqlcmd)
        result = c.fetchall()
        for row in result:
            anctype = row[0]
            if atteph and not re.search('(att|eph)', anctype, re.IGNORECASE):
                continue
            elif not atteph and re.search('(att|eph)', anctype, re.IGNORECASE):
                continue
        
            filehash[row[0]] = os.path.join(row[1], row[2])

        return filehash

if __name__ == "__main__":
    db = ancDB()

    db.openDB()
    db.create_db()
    db.insert_record(satfile='A2002365234500.L1A_LAC', starttime='2002365234500', stoptime='2002365235000',
                     ancfile='N200236518_MET_NCEPN_6h.hdf', ancpath='/Users/Shared/python/OCSSW_Scripts',
                     anctype='met1')
    db.insert_record(satfile='A2002365234500.L1A_LAC', starttime='2002365234500', stoptime='2002365235000',
                     ancfile='N200300100_MET_NCEPN_6h.hdf', ancpath='/Users/Shared/python/OCSSW_Scripts',
                     anctype='att1', atteph=True)
    print(db.check_file('A2002365234500.L1A_LAC'))
    print(db.check_file('N200236518_MET_NCEPN_6h.hdf', anctype='met1'))
    files = db.get_ancfiles('A2002365234500.L1A_LAC', atteph=True)
    print(files)
    db.delete_record(filename='A2002365234500.L1A_LAC')
    print(db.check_file('N200236518_MET_NCEPN_6h.hdf', anctype='met1'))
    db.closeDB()
