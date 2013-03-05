"""
Class to hold data about OBPG data files and allow sorting, etc. of those files.
"""

__author__ = 'melliott'

import datetime

class ObpgDataFile(object):
    """
    A class for holding data about OBPG data files.
    """
    def __init__(self, fname, ftype, sensr, stime, etime, meta=None):
        self.name = fname
        self.file_type = ftype
        self.sensor = sensr
        self.start_time = stime
        self.end_time = etime
        self.metadata = meta

    def __cmp__(self, other):
        """
        Compares 2 data files by comparing their start times.  The file with
        the earlier start time should be "less" than the other file.
        """
        self_st = datetime.datetime.strptime(self.start_time, '%Y%j%H%M%S')
        other_st = datetime.datetime.strptime(other.start_time, '%Y%j%H%M%S')
        if self_st < other_st:
            return -1
        elif self_st == other_st:
            return 0
        else:
            return 1

    def __repr__(self):
        return self.name

    def __str__(self):
        return self.name
