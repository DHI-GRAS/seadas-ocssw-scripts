
"""
Functions for reading the parameter file for seadas_processor.py.
"""

import os
import re
import sys

__author__ = 'melliott'

SECTION_HEADER_TEXT = 'section'

def get_sect_key(line):
    """
    Returns the section name from a line of text.
    The line is expected to be of the form '# section SECTION_NAME' (without the quotes).
    """
    sect_key = ''
    sect_key = re.sub(r'^\s*\[\s*(.*?)\s*\]\s*$', '\\1', line)
#    sect_key = re.sub('\s*\[\s*', '', line)
#    sect_key = re.sub('\s*\]\s*', '', sect_key)
    return sect_key

def is_section_header(line):
    """
    Returns True if a line is the header for a new section; returns False otherwise.
    """
    section_pattern = '\s*\[\s*\S+.*\]\s*'     # + SECTION_HEADER_TEXT + '.*\s*'
    compiled_pattern = re.compile(section_pattern, re.IGNORECASE)
    if re.search(compiled_pattern, line.strip()):
        return True
    else:
        return False

def is_whole_line_comment(line):
    """
    Returns True if an entire line is a comment; returns False otherwise.
    """
    if line.lstrip()[0:1] == '#':
        return True
    else:
        return False

class ParReader(object):
    """
    A class to perform reading of a seadas_processor.py parameter file.
    """
    def __init__(self, fname, acceptable_single_keys, section_converter=None):
        """
        Initializes the ParReader object: Confirms that the passed in file
        exists, is a regular file, and is readable.  If those are all true,
        sets the object filename value to the passed in value.
        """
        if os.path.exists(fname):
            if os.path.isfile(fname):
                if os.access(fname, os.R_OK):
                    self.filename = fname
                    self.acceptable_single_keys = acceptable_single_keys
                    self.section_converter = section_converter
                    self.par_results = {}
                else:
                    err_msg = "Error!  Unable to read {0}.".format(fname)
                    sys.exit(err_msg)
            else:
                err_msg = "Error!  {0} is not a regular file.".format(fname)
                sys.exit(err_msg)
        else:
            err_msg = "Error!  File {0} could not be found.".format(fname)
            sys.exit(err_msg)

    def _start_new_section(self, hdr_line):
        """
        Initializes a new section of the dictionary to be returned.
        """
        sect_dict = {}
        sect_key = get_sect_key(hdr_line)
        self.par_results[sect_key] = sect_dict
        if self.section_converter:
            if not (sect_key in self.section_converter.keys()):
                err_msg = 'Error! Section name "{0}"' +\
                          ' is not recognized.'.format(sect_key)
                sys.exit(err_msg)
        return sect_dict, sect_key

    def read_par_file(self):
        """
        Parses a parameter file, returning the contents in a dictionary of
        dictionaries.  The "outer" dictionary contains each section.  The "inner"
        dictionaries contain the parameter/value pairs.
        """
        sect_key = None
        sect_dict = {}
        with open(self.filename, 'rt') as par_file:
            for line in par_file.readlines():
                line = line.strip()
                if line != '' and not is_whole_line_comment(line):
                    if is_section_header(line):
                        sect_dict, sect_key = self._start_new_section(line)
                    else:
                        if sect_key != None:
                            if line.find('='):
                                key, val = line.split('=', 2)
                                if key == 'par':
                                    if 'par' in sect_dict:
                                        sect_dict['par'].append(val.strip())
                                    else:
                                        sect_dict['par'] = [val.strip()]
                                else:
                                    if key not in sect_dict:
                                        sect_dict[key] = val.strip()
                                    else:
                                        err_msg = 'Duplicate entry found ' + \
                                                  'for {0} in {1}'.\
                                                  format(key, self.filename)
                                        sys.exit(err_msg)
                            elif line.strip in self.acceptable_single_keys:
                                sect_dict[key] = 'True'
                            else:
                                err_msg = 'Found entry {0} with no value ' + \
                                          'in {1}'.format(key, self.filename)
                                sys.exit(err_msg)
                        else:
                            err_msg = 'Error in {0}, no section header found!'.\
                                      format(self.filename)
                            sys.exit(err_msg)
            if sect_key != '':
                self.par_results[sect_key] = sect_dict
        return self.par_results
