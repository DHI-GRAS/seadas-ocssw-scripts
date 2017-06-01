""" Module for classes for manipulating data from NASA GSFC SeaBASS files.

author: Joel Scott, SAIC / NASA GSFC Ocean Ecology Lab

included classes:

class:   readsb is designed to open and read data files that are in a SeaBASS
         format (http://seabass.gsfc.nasa.gov/), having passed FCHECK-verification.
syntax:  dataset = readsb(filename)

Notes:
* This module is designed to work with files that have been properly
  formatted according to SeaBASS guidelines (i.e. Files that passed FCHECK).
  Some error checking is performed, but improperly formatted input files
  could cause this script to error or behave unexpectedly. Files
  downloaded from the SeaBASS database should already be properly formatted, 
  however, please email seabass@seabass.gsfc.nasa.gov and/or the contact listed
  in the metadata header if you identify problems with specific files.

* It is always HIGHLY recommended that you check for and read any metadata
  header comments and/or documentation accompanying data files. Information 
  from those sources could impact your analysis.

* Compatibility: This module was developed for Python 2.7, using Python 2.7.3.

/*=====================================================================*/
                 NASA Goddard Space Flight Center (GSFC) 
         Software distribution policy for Public Domain Software

 The readsb code is in the public domain, available without fee for 
 educational, research, non-commercial and commercial purposes. Users may 
 distribute this code to third parties provided that this statement appears
 on all copies and that no charge is made for such copies.

 NASA GSFC MAKES NO REPRESENTATION ABOUT THE SUITABILITY OF THE SOFTWARE
 FOR ANY PURPOSE. IT IS PROVIDED "AS IS" WITHOUT EXPRESS OR IMPLIED
 WARRANTY. NEITHER NASA GSFC NOR THE U.S. GOVERNMENT SHALL BE LIABLE FOR
 ANY DAMAGE SUFFERED BY THE USER OF THIS SOFTWARE.
/*=====================================================================*/


Changelog:
    created 2016/04/26, jscott
    updated 2016/08/30, jscott, added support for files that lack units (i.e. - validation csv files)
    updated 2016/09/20, jscott, removed sys module dependency and all sys.exit() calls, changed header to be returned as a OrderedDict
    updated 2016/10/07, jscott, optimized testing for membership
    updated 2016/11/29, jscott, updated handling of end_header and added try-except for fd_datetime function
    updated 2016/12/21, jscott, removed numpy dependency
    updated 2017/05/04, jscott, consolidated date time parser functions in a single function fd_datetime of class readSB

"""

import re
from datetime import datetime
from collections import OrderedDict

def is_number(s):
    try:
        complex(s) # for int, long, float and complex
    except ValueError:
        return False
    return True

def is_int(s):
    try:
        int(s) # for int, long, float and complex
    except ValueError:
        return False
    return True

class readSB:
    """ Read an FCHECK-verified SeaBASS formatted data file.

        Returned data structures:
        filename  = name of data file
        headers   = dictionary of header entry and value, keyed by header entry
        comments  = list of strings containing the comment lines from the header information
        missing   = fill value as a float used for missing data, read from header
        variables = dictionary of field name and unit, keyed by field name
        data      = dictionary of data values, keyed by field name, returned as a list

        bdl       = fill value as a float used for below detection limit, read from header (empty if missing or N/A)
        adl       = fill value as a float used for above detection limit, read from header (empty if missing or N/A)
    """

    def __init__(self, filename, mask_missing=1, mask_above_detection_limit=1, mask_below_detection_limit=1):
        """
        Required arguments:
        filename = name of SeaBASS input file (string)

        Optional arguments:
        mask_missing               = flag to set missing values to NaN, default set to 1 (turned on)
        mask_above_detection_limit = flag to set above_detection_limit values to NaN, default set to 1 (turned on)
        mask_below_detection_limit = flag to set below_detection_limit values to NaN, default set to 1 (turned on)
        """
        self.filename  = filename
        self.headers   = OrderedDict()
        self.comments  = []
        self.variables = OrderedDict()
        self.data      = OrderedDict()
        self.missing   = ''
        self.adl       = ''
        self.bdl       = ''

        end_header    = False

        try:
            fileobj = open(self.filename,'r')
        except Exception, e:
            print('Exception: ', e)
            print 'Error: unable to open file for reading: ' + self.filename 
            return

        try:
            lines = fileobj.readlines()
            fileobj.close()
        except Exception, e:
            print('Exception: ', e)
            print 'Error: Unable to read data from file: ' + self.filename
            return

        for line in lines:

            """ Remove any/all newline and carriage return characters """
            newline = re.sub("[\r\n]+",'',line).strip()

            """ Extract header """
            if not end_header \
                and not '/begin_header' in newline \
                and not '/end_header' in newline \
                and not '!' in newline:
                try:
                    [h,v] = newline.split('=')
                except:
                    print 'Warning: Unable to parse header key/value pair from file: ' + self.filename
                    print newline
                h = h[1:]
                self.headers[h] = v

            """ Extract fields """
            if '/fields=' in newline:
                try:
                    _vars = newline.split('=')[1].split(',')
                    for var in _vars:
                        self.data[var] = []
                except:
                    print 'Error: Unable to parse fields in file: ' + self.filename
                    print newline
                    return

            """ Extract units """
            if '/units=' in newline:
                _units = newline.split('=')[1].split(',')

            """ Extract missing val """
            if '/missing=' in newline:
                try:
                    self.missing = float(newline.split('=')[1])
                except:
                    print 'Error: Unable to parse missing value in file: ' + self.filename
                    print newline
                    return

            """ Extract below detection limit """
            if '/below_detection_limit=' in newline:
                try:
                    self.bdl = float(newline.split('=')[1])
                except:
                    print 'Error: Unable to parse below_detection_limit in file: ' + self.filename
                    print newline
                    return

            """ Extract below detection limit """
            if '/above_detection_limit=' in newline:
                try:
                    self.adl = float(newline.split('=')[1])
                except:
                    print 'Error: Unable to parse above_detection_limit in file: ' + self.filename
                    print newline
                    return

            """ Extract delimiter """
            if '/delimiter=' in newline:
                if 'comma' in newline:
                    delim = ',+'
                elif 'space' in newline:
                    delim = '\s+'
                elif 'tab'   in newline:
                    delim = '\t+'
                else:
                    print 'Error: Invalid delimiter detected in file: ' + self.filename
                    print newline
                    return

            """ Extract comments, but not history of metadata changes """
            if '!' in newline and not '!/' in newline:
                self.comments.append(newline[1:])

            """ Check for required SeaBASS file header elements before parsing data matrix """
            if '/end_header' in newline:
                if not delim:
                    print 'Error: No valid delimiter detected in file: ' + self.filename
                    return

                if not self.missing:
                    print 'Error: No missing value detected in file: ' + self.filename
                    return

                if not _vars:
                    print 'Error: No fields detected in file: ' + self.filename
                    return

                if mask_above_detection_limit == 1 and not self.adl:
                    print 'Warning: No above_detection_limit in file header. Use mask_above_detection_limit=0 to suppress this message.'
                    print '         Unable to mask vales as NaNs for file: ' + self.filename

                if mask_below_detection_limit == 1 and not self.bdl:
                    print 'Warning: No below_detection_limit in file header. Use mask_below_detection_limit=0 to suppress this message.'
                    print '         Unable to mask vales as NaNs for file: ' + self.filename

                end_header = True
                continue

            """ Extract data after headers """
            if end_header and newline:
                try:
                    for var,dat in zip(_vars,re.split(delim,newline)):
                        if is_number(dat):
                            if is_int(dat):
                                dat = int(dat)
                            else:
                                dat = float(dat)
                            if mask_above_detection_limit == 1 and self.adl != '':
                                if dat == float(self.adl):
                                    dat = float('nan')
                            if mask_below_detection_limit == 1 and self.bdl != '':
                                if dat == float(self.bdl):
                                    dat = float('nan')
                            if mask_missing == 1 and dat == self.missing:
                                dat = float('nan')
                        self.data[var].append(dat)
                except Exception, e:
                    print('Exception: ', e)
                    print 'Error: Unable to parse data from line in file: ' + self.filename
                    print newline
                    return

        try:
            self.variables = OrderedDict(zip(_vars,zip(_vars,_units)))
        except:
            #print 'Warning: No valid units were detected in the SeaBASS file header.'
            self.variables = OrderedDict(zip(_vars,_vars))

    def fd_datetime(self):
        """ Convert date and time information from the file's data to a Python list of datetime objects.

            Returned data structure:
            dt = a list of Python datetime objects

            Looks for these fields/keys:
                date/time,
                year/month/day/hour/minute/second,
                year/month/day/time,
                date/hour/minute/second, OR
                date_time
            in the SELF.data OrderedDict Python structure.
        """
        dt = []

        try:
            for d,t in zip([str(d) for d in self.data['date']],self.data['time']):
                da = re.search("(\d{4})(\d{2})(\d{2})", d)
                ti = re.search("(\d{1,2})\:(\d{2})\:(\d{2})", t)
                try:
                    dt.append(datetime(int(da.group(1)), \
                            int(da.group(2)), \
                            int(da.group(3)), \
                            int(ti.group(1)), \
                            int(ti.group(2)), \
                            int(ti.group(3))))
                except Exception, e:
                    print('Exception: ', e)
                    print 'Error: date/time fields not formatted correctly; unable to parse.'

        except:
            try:
                for y,m,d,h,mn,s in zip(self.data['year'], self.data['month'], self.data['day'], self.data['hour'], self.data['minute'], self.data['second']):
                    dt.append(datetime(int(y), int(m), int(d), int(h), int(mn), int(s)))

            except:
                try:
                    for y,m,d,t in zip(self.data['year'], self.data['month'], self.data['day'], self.data['time']):
                        ti = re.search("(\d{1,2})\:(\d{2})\:(\d{2})", t)
                        try:
                            dt.append(datetime(int(y), \
                                    int(m), \
                                    int(d), \
                                    int(ti.group(1)), \
                                    int(ti.group(2)), \
                                    int(ti.group(3))))
                        except Exception, e:
                            print('Exception: ', e)
                            print 'Error: year/month/day/time fields not formatted correctly; unable to parse.'

                except:
                    try:
                        for d,h,mn,s in zip(self.data['date'], self.data['hour'], self.data['minute'], self.data['second']):
                            da = re.search("(\d{4})(\d{2})(\d{2})", d)
                            try:
                                dt.append(datetime(int(da.group(1)), \
                                        int(da.group(2)), \
                                        int(da.group(3)), \
                                        int(h), \
                                        int(mn), \
                                        int(s)))
                            except Exception, e:
                                print('Exception: ', e)
                                print 'Error: date/hour/minute/second fields not formatted correctly; unable to parse.'

                    except:
                        try:
                            for i in self.data('date_time'):
                                da = re.search("(\d{4})-(\d{2})-(\d{2})\s(\d{1,2})\:(\d{2})\:(\d{2})", i)
                                try:
                                    dt.append(datetime(int(da.group(1)), \
                                            int(da.group(2)), \
                                            int(da.group(3)), \
                                            int(da.group(4)), \
                                            int(da.group(5)), \
                                            int(da.group(6))))
                                except Exception, e:
                                    print('Exception: ', e)
                                    print 'Error: date_time field not formatted correctly; unable to parse.'

                        except:
                            print 'Error: Missing fields in SeaBASS file.'
                            print 'File must contain date/time, date/hour/minute/second, year/month/day/time, OR year/month/day/hour/minute/second'
        return(dt)

