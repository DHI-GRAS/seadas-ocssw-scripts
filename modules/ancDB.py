#! /usr/bin/env python
__author__ = 'sbailey'

import sqlite3
import re

class ancDB:
    def __init__(self, dbfile=None, local=False):
        """A small set of functions to generate, update, and read from a local SQLite database of ancillary
        file information"""
        self.dbfile = dbfile
        self.local = local
        self.conn = None
        self.cursor = None

    def openDB(self):
        """
        Open connection to the ancillary DB and initiate a cursor
        """
        conn = sqlite3.connect(self.dbfile, timeout=30)
        self.conn = conn
        c = conn.cursor()
        c.execute('''PRAGMA foreign_keys = ON''')
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
            (satid INTEGER PRIMARY KEY,
            filename TEXT ,
            starttime TEXT,
            stoptime TEXT,
            status INTEGER,
            attephstat INTEGER)''')

        # Create  ancfiles table
        c.execute('''CREATE  TABLE IF NOT EXISTS ancfiles
            (ancid INTEGER PRIMARY KEY,
            filename TEXT ,
            path TEXT  ,
            type TEXT)''')

        # Create  satancinfo table
        c.execute('''CREATE  TABLE IF NOT EXISTS satancinfo
            (satid INTEGER  ,
            ancid INTEGER  ,
            optimal INTEGER,
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

            c.execute('INSERT INTO satfiles VALUES (NULL,?,?,?,?,?)',
                [satfile, starttime, stoptime, inputdbstat, attephstat])
            self.conn.commit()
            satid = ancDB.check_file(self, satfile)

        else:
            if atteph:
                c.execute('UPDATE satfiles set attephstat = ?', [dbstat])
            else:
                c.execute('UPDATE satfiles set status = ?', [dbstat])

            self.conn.commit()

        if ancid is None:
            c.execute('INSERT INTO ancfiles VALUES (NULL,?,?,?)', [ancfile, ancpath, anctype])
            self.conn.commit()
            ancid = ancDB.check_file(self, ancfile, anctype=anctype)

        opt = self.check_dbrtn_status(dbstat, anctype)

        result = c.execute('SELECT * from satancinfo where satid = ? and ancid = ?', [satid, ancid])
        r = result.fetchone()

        if r is None:
            c.execute('INSERT INTO satancinfo VALUES (?,?,?)', [satid, ancid, opt])


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
            c.execute('DELETE from satancinfo where ancid = ?', [ancid])
            c.execute('DELETE from ancfiles where ancid = ?', [ancid])

        else:
            satid = self.check_file(filename)
            ancids = conn.execute('select ancid from satancinfo where satid = ?', [satid])
            for a in ancids:
                c.execute('DELETE from satancinfo where ancid = ?', [a[0]])
                c.execute('DELETE from ancfiles where ancid = ?', [a[0]])

            c.execute('DELETE from satfiles where satid = ?', [satid])

        conn.commit()

    def check_dbrtn_status(self, dbstat, anctype):
        """
        Check the database return status.
        DB return status bitwise values:
            all bits off means all is well in the world
            value of -1 means have not checked for ancfiles yet
            Ancillary:
                bit 0 - missing one or more MET
                bit 1 - missing one or more OZONE
                bit 2 - missing SST
                bit 3 - missing NO2
                bit 4 - missing ICE
            Attitude-Ephemeris
                bit 0 - predicted attitude selected
                bit 1 - predicted ephemeris selected
                bit 2 - no attitude found
                bit 3 - no ephemeris found
                bit 4 - invalid mission
        """

        statchk = {'atm': 1, 'met': 1,  # bit 0
                   'ozone': 2,
                   'sstfile': 4,
                   'no2file': 8,
                   'icefile': 16,    # bit 4
                   # atteph
                   'att': 1,
                   'eph': 2,
                   # aquarius
                   'sssfile': 32,
                   'xrayfile': 64,
                   'scat': 128,
                   'tecfile': 256,
                   'swhfile': 512,
                   'frozenfile': 1024,
                   'geosfile': 2048,
                   'argosfile': 4096,
                   'sif': 8192,  # sif_file
                   'pert': 16384, # l2_uncertainties_file
                   'sssmatchup': 32768, # sss_matchup_file
                   'rim_file': 65536 }

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
        r = result.fetchone()

        if r is None:
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
        r = result.fetchone()

        if r is None:
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
        r = result.fetchone()
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
        result = c.execute(
            'SELECT a.type, a.path, a.filename from ancfiles a, satancinfo s where a.ancid = s.ancid and s.satid = ?',
            [satID])
        for row in result:
            anctype = row[0]
            if atteph and not re.search('(att|eph)', anctype, re.IGNORECASE):
                continue
            elif not atteph and re.search('(att|eph)', anctype, re.IGNORECASE):
                continue

            filehash[row[0]] = os.path.join(row[1], row[2])

        return filehash

if __name__ == "__main__":
    db = ancDB(dbfile='/tmp/testDB.sqlite.db')

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
