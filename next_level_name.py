#!/usr/bin/env python

"""
Program to return the name of the next level file that would be created from
the input file name.
"""

#import datetime
import get_obpg_file_type
import MetaUtils
import next_level_name_finder
import obpg_data_file
import optparse
import os
import sys
import traceback

__author__ = 'melliott'

#2345678901234567890123456789012345678901234567890123456789012345678901234567890

#########################################

FILE_TYPES_CONVERTER = { 'Level 0': 'Level 0',
                         'Level 1A': 'Level 1A',
                         'l1agen' : 'Level 1A',
                         'Level 1B': 'Level 1B',
                         'Level 2': 'Level 2',
                         'L3bin': 'L3bin',
                         'Level 3 Binned': 'L3bin'
}

#def get_1_file_name(input_name, file_typer, file_type, sensor,
#                    target_program, clopts):
def get_1_file_name(data_file, target_program, clopts):
    """
    Return the next level name for a single file.
    """
    level_finder = get_level_finder([data_file], target_program, clopts)
    next_level_name = level_finder.get_next_level_name()
    return next_level_name

def get_extension(file_type):
    extensions = {'l2bin': '.L3b', 'l3bin': '.L3b', 'smigen': '.SMI'}
    return extensions[file_type]

def get_multifile_next_level_name(data_files_list_info, target_program, clopts):
    """
    Return the next level name for a set of files.
    """
    next_level_name = 'fill-in value for multiple inputs'
    for file_info in data_files_list_info:
        if file_info.file_type == 'unknown':
            print '{0}: unknown type'.format(file_info['name'])
    next_level_name = get_multifile_output_name(data_files_list_info,
                                                target_program, clopts.l2_suite)
    return next_level_name

def get_multifile_output_name(data_files_list_info, target_program, l2_suite):
    """
    Returns the file name derived from a group of files names.
    """
    #    output_name = 'place_holder_name'
    if l2_suite is None:
        l2_suite = '_OC'
    output_type = OUTPUT_TYPES[data_files_list_info[0].file_type]
    for data_file in data_files_list_info[1:]:
        if OUTPUT_TYPES[data_file.file_type] != output_type:
            err_msg = 'Error!  Output types do not match for {0} and {1}'.\
            format(data_files_list_info[0].name, data_file.name)
            sys.exit(err_msg)
    time_ext = next_level_name_finder.get_time_period_extension(
        data_files_list_info[0].start_time,
        data_files_list_info[-1].end_time)
    output_name = data_files_list_info[0].start_time[0:4] +\
                  data_files_list_info[0].start_time[4:7] +\
                  data_files_list_info[-1].start_time[0:4] +\
                  data_files_list_info[-1].start_time[4:7] +\
                  get_extension(target_program) + time_ext + l2_suite
    return output_name

#########################################

def get_command_line_data():
    """
    Returns the options and arguments from a command line call.
    """
    ver_msg = ' '.join(['%prog', __version__])
    use_msg = 'usage: %prog INPUT_FILE TARGET_PROGRAM'
    cl_parser = optparse.OptionParser(usage=use_msg, version=ver_msg)
    cl_parser.add_option('--l2_suite', dest='l2_suite', action='store',
                         type='string', help='data type suite for l2gen')
    (clopts, clargs) = cl_parser.parse_args()
    if len(clargs) == 0:
        print "\nError! No input file or target program specified.\n"
        cl_parser.print_help()
        sys.exit(0)
    elif len(clargs) == 1:
        print "\nError! No target program specified.\n"
        cl_parser.print_help()
        sys.exit(0)
    elif len(clargs) > 2:
        print '\nError!  Too many arguments specified on the command line.'
        cl_parser.print_help()
        sys.exit(0)
    else:
        return clopts, clargs[0], clargs[1]

def get_data_files_info(file_list_file):
    """
    Returns a list of of data files.
    """
    file_info = []
    with open(file_list_file, 'rt') as file_list_file:
        inp_lines = file_list_file.readlines()
    for line in inp_lines:
        filename = line.strip()
        if os.path.exists(filename):
            file_typer = get_obpg_file_type.ObpgFileTyper(filename)
            file_type, sensor = file_typer.get_file_type()
            stime, etime = file_typer.get_file_times()
            data_file = obpg_data_file.ObpgDataFile(filename, file_type,
                                                    sensor, stime, etime)
            file_info.append(data_file)
    file_info.sort()
    return file_info

def get_level_finder(data_file_list, target_program, clopts):
    """
    Returns an appropriate level finder object for the data file passed in.
    """
    if (data_file_list[0].sensor.find('MODIS') != -1):
        if clopts.l2_suite:
            level_finder = next_level_name_finder.ModisNextLevelNameFinder(
                            data_file_list, target_program, clopts.l2_suite)
        else:
            level_finder = next_level_name_finder.ModisNextLevelNameFinder(
                            data_file_list, target_program)
    else:
        if clopts.l2_suite:
            level_finder = next_level_name_finder.NextLevelNameFinder(
                            data_file_list, target_program, clopts.l2_suite)
        else:
            level_finder = next_level_name_finder.NextLevelNameFinder(
                            data_file_list, target_program)
    return level_finder

def handle_unexpected_exception(exc_info):
    """
    Builds and prints an error message from the exception information,
    then exits.
    """
    exc_parts = exc_info
    err_type = str(exc_parts[0]).split('.')[1][0:-2]
    err_msg = 'Error!  Encountered {0}:'.format(str(err_type))
    print err_msg
    if DEBUG:
        traceback.print_exc()
    sys.exit(1)

def main():
    """
    Main function for when this module is called as a program.
    """
    ret_status = 0
    clopts, inp_name, targ_prog = get_command_line_data()

    processable_progs = set(next_level_name_finder.NextLevelNameFinder.PROCESSING_LEVELS.keys() +\
                            next_level_name_finder.ModisNextLevelNameFinder.PROCESSING_LEVELS.keys())
    if not targ_prog in processable_progs:
        err_msg = 'Error!  The target program, "{0}", is not known.'.\
                  format(targ_prog)
        sys.exit(err_msg)
    if os.path.exists(inp_name):
        try:
            file_typer = get_obpg_file_type.ObpgFileTyper(inp_name)
            ftype, sensor = file_typer.get_file_type()
            if ftype == 'unknown':
                if MetaUtils.is_ascii_file(inp_name):
                    # Try treating the input file as a file list file.
                    data_files_info = get_data_files_info(inp_name)
                    if len(data_files_info) > 0:
                        next_level_name = get_multifile_next_level_name(
                                            data_files_info, targ_prog, clopts)
                else:
                    # The input file wasn't a file list file.
                    err_msg = "File {0} is not an OBPG file.".format(inp_name)
                    sys.exit(err_msg)
            else:
                # The file is an OBPG file
                stime, etime = file_typer.get_file_times()
                data_file = obpg_data_file.ObpgDataFile(inp_name, ftype, sensor,
                                                        stime, etime)
                data_files_info = [data_file]
                next_level_name = get_1_file_name(data_file, targ_prog, clopts)
            print 'Output Name: ' + next_level_name
        except SystemExit, e:
            # The intention here is to catch exit exceptions we throw in other
            # parts of the program and continue with the exit, outputting
            # whatever error message was created for the exit.
            sys.exit(e)
        except:
            handle_unexpected_exception(sys.exc_info())
    else:
        err_msg = "Error!  File {0} was not found.".format(inp_name)
        sys.exit(err_msg)
    return ret_status

##########################################

OUTPUT_TYPES = {'Level 2': 'l3bin'}
#global DEBUG
DEBUG = False
DEBUG = True  # Comment out for production use

__version__ = '0.5.dev'
if __name__ == '__main__':
    sys.exit(main())
