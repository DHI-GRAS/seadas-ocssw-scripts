#!/usr/bin/env python

"""
Program to perform multilevel processing (previously known as the
seadas_processor and sometimes referred to as the 'uber' processor).
"""

try:
    import configparser
except ImportError:
    import ConfigParser as configparser
    
import datetime
import logging
import optparse
import os
import re
import subprocess
import sys
import tarfile
import time
import traceback

import get_obpg_file_type
import modules.mlp_utils as mlp_utils
import modules.benchmark_timer as benchmark_timer
import modules.MetaUtils as MetaUtils
import modules.name_finder_utils as name_finder_utils
import modules.obpg_data_file as obpg_data_file
import modules.ProcUtils as ProcUtils
import modules.processor as processor
import modules.processing_rules as processing_rules
import modules.uber_par_file_reader as uber_par_file_reader
#import product

__version__ = '1.0.6'

__author__ = 'melliott'

class ProcessorConfig(object):
    """
    Configuration data for the program which needs to be widely available.
    """
    SECS_PER_DAY = 86400
    def __init__(self, hidden_dir, ori_dir, verbose, overwrite, use_existing,
                 tar_name=None, timing=False, out_dir=None):
        self.prog_name = os.path.basename(sys.argv[0])

        if not os.path.exists(hidden_dir):
            try:
                os.mkdir(hidden_dir)
            except OSError:
                if sys.exc_info()[1].find('Permission denied:') != -1:
                    log_and_exit('Error!  Unable to create directory {0}'.\
                                 format(hidden_dir))
        self.hidden_dir = hidden_dir
        self.original_dir = ori_dir
        self.verbose = verbose
#        self.keepfiles = keepfiles
        self.keepfiles = False
        self.overwrite = overwrite
        self.use_existing = use_existing
        self.get_anc = True
        self.tar_filename = tar_name
        self.timing = timing
        if out_dir:
            self.output_dir = out_dir
            self.output_dir_is_settable = False
        else:
            self.output_dir = '.'   # default to current dir, change later if
                                    # specified in par file or command line
            self.output_dir_is_settable = True
        cfg_file_path = os.path.join(self.hidden_dir, 'seadas_ocssw.cfg')
        if os.path.exists(cfg_file_path):
            self._read_saved_options(cfg_file_path)
        else:
            self.max_file_age = 2592000          # number of seconds in 30 days
            self._write_default_cfg_file(cfg_file_path)
        ProcessorConfig._instance = self

    def _read_saved_options(self, cfg_path):
        """
        Gets options stored in the program's configuration file.
        """
        try:
            cfg_parser = configparser.SafeConfigParser()
            cfg_parser.read(cfg_path)
            try:
                self.max_file_age = ProcessorConfig.SECS_PER_DAY * \
                                    int(cfg_parser.get('main',
                                                       'par_file_age').\
                                    split(' ', 2)[0])
            except configparser.NoSectionError as nse:
                print ('nse: ' + str(nse))
                print ('sys.exc_info(): ')
                for msg in sys.exc_info():
                    print ('  ' +  str(msg))
                log_and_exit('Error!  Configuration file has no "main" ' +
                             'section.')
            except configparser.NoOptionError:
                log_and_exit('Error! The "main" section of the configuration ' +
                             'file does not specify a "par_file_age".')
        except configparser.MissingSectionHeaderError:
            log_and_exit('Error! Bad configuration file, no section headers ' +
                         'found.')

    def _set_temp_dir(self):
        """
        Sets the value of the temporary directory.
        """
        if os.path.exists('/tmp') and os.path.isdir('/tmp') and \
           os.access('/tmp', os.W_OK):
            return '/tmp'
        else:
            cwd = os.getcwd()
            if os.path.exists(cwd) and os.path.isdir(cwd) and \
               os.access(cwd, os.W_OK):
                return cwd
            else:
                log_and_exit('Error! Unable to establish a temporary ' +
                             'directory.')

    def _write_default_cfg_file(self, cfg_path):
        """
        Writes out a configuration file using default values.
        """
        with open(cfg_path, 'wt') as cfg_file:
            cfg_file.write('[main]\n')
            cfg_file.write('par_file_age=30  # units are days\n')

def get_obpg_data_file_object(file_specification):
    """
    Returns an obpg_data_file object for the file named in file_specification.
    """
    ftyper = get_obpg_file_type.ObpgFileTyper(file_specification)
    (ftype, sensor) = ftyper.get_file_type()
    (stime, etime) = ftyper.get_file_times()
    obpg_data_file_obj = obpg_data_file.ObpgDataFile(file_specification, ftype,
                                                     sensor, stime, etime,
                                                     ftyper.attributes)
    return obpg_data_file_obj

def build_executable_path(prog_name):
    """
    Returns the directory in which the program named in prog_name is found.
    None is returned if the program is not found.
    """
    exe_path = None
    candidate_subdirs = ['bin', 'run', 'scripts', 'run/scripts']
    for subdir in candidate_subdirs:
        cand_path = os.path.join(OCSSWROOT_DIR, subdir, prog_name)
        if os.path.exists(cand_path):
            exe_path = cand_path
            break
    return exe_path

def build_file_list_file(filename, file_list):
    """
    Create a file listing the names of the files to be processed.
    """
    with open(filename, 'wt') as file_list_file:
        for fname in file_list:
            file_list_file.write(fname + '\n')

def build_general_rules():
    """
    Builds and returns the general rules set.

    Rule format:
    target type (string),  source types (list of strings), batch processing
    flag (Boolean), action to take (function name)
    """
    rules_dict = {
        'level 1a': processing_rules.build_rule('level 1a', ['level 0'],
                                                run_bottom_error, False),
        'l1brsgen': processing_rules.build_rule('l1brsgen', ['l1'],
                                                run_l1brsgen, False),
        'l2brsgen': processing_rules.build_rule('l2brsgen', ['l2gen'],
                                                run_l2brsgen, False),
        'l1mapgen': processing_rules.build_rule('l1mapgen', ['l1'],
                                                run_l1mapgen, False),
        'l2mapgen': processing_rules.build_rule('l2mapgen', ['l2gen'],
                                                run_l2mapgen, False),
        #'level 1b': processing_rules.build_rule('level 1b', ['level 1a','geo'],
        #                                    run_l1b, False),
        'level 1b': processing_rules.build_rule('level 1b', ['level 1a'],
                                                run_l1b, False),
        # 'l2gen': processing_rules.build_rule('l2gen', ['level 1b'], run_l2gen,
        #                                      False),
        'l2gen': processing_rules.build_rule('l2gen', ['level 1a'], run_l2gen,
                                             False),
        'l2extract': processing_rules.build_rule('l2extract', ['l2gen'],
                                                 run_l2extract, False),
        'l2bin': processing_rules.build_rule('l2bin', ['l2gen'], run_l2bin,
                                             True),
        'l3bin': processing_rules.build_rule('l3bin', ['l2bin'], run_l3bin,
                                             True),
        'l3mapgen': processing_rules.build_rule('l3mapgen', ['l3bin'],
                                                run_l3mapgen, False),
        'smigen': processing_rules.build_rule('smigen', ['l3bin'], run_smigen,
                                              False)
    }
    rules_order = ['level 1a', 'l1brsgen', 'l1mapgen', 'level 1b', 'l2gen',
                   'l2extract', 'l2brsgen', 'l2mapgen', 'l2bin', 'l3bin',
                   'l3mapgen', 'smigen']
    rules = processing_rules.RuleSet('General rules', rules_dict, rules_order)
    return rules

def build_goci_rules():
    """
    Builds and returns the rules set for GOCI.

    Rule format:
    target type (string),  source types (list of strings), batch processing
    flag (Boolean), action to take (function name)
    """
    rules_dict = {
        'level 1a': processing_rules.build_rule('level 1a', ['level 0'],
                                                run_bottom_error, False),
        'l1brsgen': processing_rules.build_rule('l1brsgen', ['l1'],
                                                run_l1brsgen, False),
        'l2brsgen': processing_rules.build_rule('l2brsgen', ['l2gen'],
                                                run_l2brsgen, False),
        'l1mapgen': processing_rules.build_rule('l1mapgen', ['l1'],
                                                run_l1mapgen, False),
        'l2mapgen': processing_rules.build_rule('l2mapgen', ['l2gen'],
                                                run_l2mapgen, False),
        #'level 1b': processing_rules.build_rule('level 1b', ['level 1a','geo'],
        #                                    run_l1b, False),
        'level 1b': processing_rules.build_rule('level 1b', ['level 1a'],
                                                run_l1b, False),
        # 'l2gen': processing_rules.build_rule('l2gen', ['level 1b'], run_l2gen,
        #                                      False),
        'l2gen': processing_rules.build_rule('l2gen', ['level 1b'], run_l2gen,
                                             False),
        'l2extract': processing_rules.build_rule('l2extract', ['l2gen'],
                                                 run_l2extract, False),
        'l2bin': processing_rules.build_rule('l2bin', ['l2gen'], run_l2bin,
                                             True),
        'l3bin': processing_rules.build_rule('l3bin', ['l2bin'], run_l3bin,
                                             True),
        'l3mapgen': processing_rules.build_rule('l3mapgen', ['l3bin'],
                                                run_l3mapgen, False),
        'smigen': processing_rules.build_rule('smigen', ['l3bin'], run_smigen,
                                              False)
    }
    rules_order = ['level 1a', 'l1brsgen', 'l1mapgen', 'level 1b', 'l2gen',
                   'l2extract', 'l2brsgen', 'l2mapgen', 'l2bin', 'l3bin',
                   'l3mapgen', 'smigen']
    rules = processing_rules.RuleSet('GOCI rules', rules_dict, rules_order)
    return rules

def build_l2gen_par_file(par_contents, input_file, geo_file, output_file):
    """
    Build the parameter file for L2 processing.
    """
    dt_stamp = datetime.datetime.today()
    par_name = ''.join(['L2_', dt_stamp.strftime('%Y%m%d%H%M%S'), '.par'])
    par_path = os.path.join(cfg_data.hidden_dir, par_name)
    with open(par_path, 'wt') as par_file:
        par_file.write('# Automatically generated par file for l2gen\n')
        par_file.write('ifile=' + input_file + '\n')
        if not geo_file is None:
            par_file.write('geofile=' + geo_file + '\n')
        par_file.write('ofile=' + output_file + '\n')
        for l2_opt in par_contents:
            if l2_opt != 'ifile' and l2_opt != 'geofile' \
                    and not l2_opt in FILE_USE_OPTS:
                par_file.write(l2_opt + '=' + par_contents[l2_opt] + '\n')
    return par_path

def build_meris_rules():
    """
    Builds and returns the rules set for MERIS.

    Rule format:
    target type (string),  source types (list of strings), batch processing
    flag (Boolean), action to take (function name)
    """
    rules_dict = {
        'level 1a': processing_rules.build_rule('level 1a', ['level 0'],
                                                run_bottom_error, False),
        'l1brsgen': processing_rules.build_rule('l1brsgen', ['l1'],
                                                run_l1brsgen, False),
        'l2brsgen': processing_rules.build_rule('l2brsgen', ['l2gen'],
                                                run_l2brsgen, False),
        'l1mapgen': processing_rules.build_rule('l1mapgen', ['l1'],
                                                run_l1mapgen, False),
        'l2mapgen': processing_rules.build_rule('l2mapgen', ['l2gen'],
                                                run_l2mapgen, False),
        #'level 1b': processing_rules.build_rule('level 1b', ['level 1a','geo'],
        #                                    run_l1b, False),
        'level 1b': processing_rules.build_rule('level 1b', ['level 1a'],
                                                run_l1b, False),
        # 'l2gen': processing_rules.build_rule('l2gen', ['level 1b'], run_l2gen,
        #                                      False),
        'l2gen': processing_rules.build_rule('l2gen', ['level 1b'], run_l2gen,
                                             False),
        'l2extract': processing_rules.build_rule('l2extract', ['l2gen'],
                                                 run_l2extract, False),
        'l2bin': processing_rules.build_rule('l2bin', ['l2gen'], run_l2bin,
                                             True),
        'l3bin': processing_rules.build_rule('l3bin', ['l2bin'], run_l3bin,
                                             True),
        'l3mapgen': processing_rules.build_rule('l3mapgen', ['l3bin'],
                                                run_l3mapgen, False),
        'smigen': processing_rules.build_rule('smigen', ['l3bin'], run_smigen,
                                              False)
    }
    rules_order = ['level 1a', 'l1brsgen', 'l1mapgen', 'level 1b', 'l2gen',
                   'l2extract', 'l2brsgen', 'l2mapgen', 'l2bin', 'l3bin',
                   'l3mapgen', 'smigen']
    rules = processing_rules.RuleSet('MERIS rules', rules_dict, rules_order)
    return rules

def build_modis_rules():
    """
    Builds and returns the MODIS rules.

    Rule format:
    target type (string),  source types (list of strings), action to take
    (function name), batch processing flag (Boolean)
    """
    rules_dict = {
        'level 0': processing_rules.build_rule('level 0', ['nothing lower'],
                                               run_bottom_error, False),
        'level 1a': processing_rules.build_rule('level 1a', ['level 0'],
                                                run_modis_l1a, False),
        'l1brsgen': processing_rules.build_rule('l1brsgen', ['l1'],
                                                run_l1brsgen, False),
        'l1mapgen': processing_rules.build_rule('l1mapgen', ['l1'],
                                                run_l1mapgen, False),
        'geo': processing_rules.build_rule('geo', ['level 1a'], run_modis_geo,
                                           False),
        'l1aextract_modis': processing_rules.build_rule('l1aextract_modis',
                                                        ['level 1a', 'geo'],
                                                        run_l1aextract_modis,
                                                        False),
        'level 1b': processing_rules.build_rule('level 1b',
                                                ['level 1a', 'geo'],
                                                run_modis_l1b, False),
        'l2gen': processing_rules.build_rule('l2gen', ['level 1b', 'geo'],
                                             run_l2gen, False),
        'l2extract': processing_rules.build_rule('l2extract', ['l2gen'],
                                                 run_l2extract, False),
        'l2brsgen': processing_rules.build_rule('l2brsgen', ['l2gen'],
                                                run_l2brsgen, False),
        'l2mapgen': processing_rules.build_rule('l2mapgen', ['l2gen'],
                                                run_l2mapgen, False),
        'l2bin': processing_rules.build_rule('l2bin', ['l2gen'], run_l2bin,
                                             True),
        'l3bin': processing_rules.build_rule('l3bin', ['l2bin'], run_l3bin,
                                             True),
        'l3mapgen': processing_rules.build_rule('l3mapgen', ['l3bin'],
                                                run_l3mapgen, False, False),
        'smigen': processing_rules.build_rule('smigen', ['l3bin'], run_smigen,
                                              False)
    }
    rules_order = ['level 0', 'level 1a', 'l1brsgen', 'l1mapgen', 'geo',
                   'l1aextract_modis', 'level 1b', 'l2gen', 'l2extract',
                   'l2bin', 'l2brsgen', 'l2mapgen', 'l3bin', 'l3mapgen',
                   'smigen']
    rules = processing_rules.RuleSet("MODIS Rules", rules_dict, rules_order)
    return rules

def build_seawifs_rules():
    """
    Builds and returns the SeaWiFS rules set.
    """
    rules_dict = {
        'level 1a': processing_rules.build_rule('level 1a', ['level 0'],
                                                run_bottom_error, False),
        'l1aextract_seawifs': processing_rules.build_rule('l1aextract_seawifs',
                                                          ['level 1a'],
                                                          run_l1aextract_seawifs,
                                                          False),
        'l1brsgen': processing_rules.build_rule('l1brsgen', ['l1'],
                                                run_l1brsgen, False),
        'l1mapgen': processing_rules.build_rule('l1mapgen', ['l1'],
                                                run_l1mapgen, False),
        'level 1b': processing_rules.build_rule('level 1b', ['level 1a'],
                                                run_l1b, False),
        # 'l2gen': processing_rules.build_rule('l2gen', ['level 1b'], run_l2gen,
        #                                       False),
        'l2gen': processing_rules.build_rule('l2gen', ['level 1a'], run_l2gen,
                                             False),
        'l2extract': processing_rules.build_rule('l2extract', ['l2gen'],
                                                 run_l2extract, False),
        'l2brsgen': processing_rules.build_rule('l2brsgen', ['l2gen'],
                                                run_l2brsgen, False),
        'l2mapgen': processing_rules.build_rule('l2mapgen', ['l2gen'],
                                                run_l2mapgen, False),
        'l2bin': processing_rules.build_rule('l2bin', ['l2gen'], run_l2bin,
                                             True),
        'l3bin': processing_rules.build_rule('l3bin', ['l2bin'], run_l3bin,
                                             True, False),
        'l3mapgen': processing_rules.build_rule('l3mapgen', ['l3bin'],
                                                run_l3mapgen, False, False),
        'smigen': processing_rules.build_rule('smigen', ['l3bin'], run_smigen,
                                              False)
    }
    rules_order = ['level 1a', 'l1aextract_seawifs', 'l1brsgen',
                   'l1mapgen', 'geo', 'level 1b', 'l2gen', 'l2extract',
                   'l2brsgen', 'l2mapgen', 'l2bin', 'l3bin',
                   'l3mapgen', 'smigen']
    rules = processing_rules.RuleSet("SeaWiFS Rules", rules_dict, rules_order)
    return rules

def build_viirs_rules():
    """
    Builds and returns the VIIRS rules set. (incomplete)
    """
    # todo: finish this
    rules_dict = {
        'level 1a': processing_rules.build_rule('level 1a',
                                                ['nothing lower'],
                                                run_bottom_error, False),
        'geo': processing_rules.build_rule('geo', ['level 1a'],
                                           run_geolocate_viirs, False),
        'level 1b': processing_rules.build_rule('level 1b', ['level 1a', 'geo'],
                                                run_viirs_l1b, False),
#        'l2gen': processing_rules.build_rule('l2gen', ['level 1a', 'geo'],
#                                             run_l2gen_viirs, True),
        'l2gen': processing_rules.build_rule('l2gen', ['level 1a', 'geo'],
                                             run_l2gen, False),
        'l2extract': processing_rules.build_rule('l2extract', ['l2gen'],
                                                 run_l2extract, False),
        'l2brsgen': processing_rules.build_rule('l2brsgen', ['l2gen'],
                                                run_l2brsgen, False),
        'l2mapgen': processing_rules.build_rule('l2mapgen', ['l2gen'],
                                                run_l2mapgen, False),
        'l2bin': processing_rules.build_rule('l2bin', ['l2gen'], run_l2bin,
                                             True),
        'l3bin': processing_rules.build_rule('l3bin', ['l2bin'], run_l3bin,
                                             True),
        'l3mapgen': processing_rules.build_rule('l3mapgen', ['l3bin'],
                                                run_l3mapgen, False, False),
        'smigen': processing_rules.build_rule('smigen', ['l3bin'], run_smigen,
                                              False)
    }
    rules_order = ['level 1a', 'geo', 'level 1b', 'l2gen', 'l2extract',
                   'l2brsgen', 'l2mapgen', 'l2bin', 'l3bin',
                   'l3mapgen', 'smigen']
    rules = processing_rules.RuleSet('VIIRS Rules', rules_dict, rules_order)
    return rules

def build_rules():
    """
    Build the processing rules.
    """
    rules = dict(general=build_general_rules(),
                 goci=build_goci_rules(),
                 meris=build_meris_rules(),
                 modis=build_modis_rules(),
                 seawifs=build_seawifs_rules(),
                 viirs=build_viirs_rules())
    return rules

def check_options(options):
    """
    Check command line options
    """
    if options.tar_file:
        if os.path.exists(options.tar_file):
            err_msg = 'Error! The tar file, {0}, already exists.'. \
                format(options.tar_file)
            log_and_exit(err_msg)
    if options.ifile:
        if not os.path.exists(options.ifile):
            err_msg = 'Error! The specified input file, {0}, does not exist.'. \
                format(options.ifile)
            log_and_exit(err_msg)

def clean_files(delete_list):
    """
    Delete unwanted files created during processing.
    """
    if cfg_data.verbose:
        print ("Cleaning up files")
        sys.stdout.flush()
    files_deleted = 0
    # Delete any files in the delete list.  This contain "interemediate" files
    # which were needed to complete processing, but which weren't explicitly
    # requested as output targets.
    for filepath in delete_list:
        if cfg_data.verbose:
            print ('Deleting {0}'.format(filepath))
            sys.stdout.flush()
        os.remove(filepath)
        files_deleted += 1
    # Delete hidden par files older than the cut off age
    hidden_files = os.listdir(cfg_data.hidden_dir)
    par_files = [f for f in hidden_files if f.endswith('.par')]
    for par_file in par_files:
        par_path = os.path.join(cfg_data.hidden_dir, par_file)
        file_age = round(time.time()) - os.path.getmtime(par_path)
        if file_age > cfg_data.max_file_age:
            if cfg_data.verbose:
                print ('Deleting {0}'.format(par_path))
                sys.stdout.flush()
            os.remove(par_path)
            files_deleted += 1
    if cfg_data.verbose:
        if not files_deleted:
            print ('No files were found for deletion.')
            sys.stdout.flush()
        elif files_deleted == 1:
            print ('One file was deleted.')
            sys.stdout.flush()
        else:
            print ('A total of {0} files were deleted.'.format(files_deleted))
            sys.stdout.flush()

def create_levels_list(rules_sets):
    """
    Returns a list containing all the levels from all the rules sets.
    """
    set_key = list(rules_sets.keys())[0]
    logging.debug('set_key = %s', (set_key))
    lvls_lst = [(lvl, [set_key]) for lvl in rules_sets[set_key].order[1:]]
    for rules_set_name in list(rules_sets.keys())[1:]:
        for lvl_name in rules_sets[rules_set_name].order[1:]:
            names_list = [lst_item[0] for lst_item in lvls_lst]
            if lvl_name in names_list:
                lvls_lst[names_list.index(lvl_name)][1].append(rules_set_name)
            else:
                prev_ndx = rules_sets[rules_set_name].order.index(lvl_name) - 1
                if rules_sets[rules_set_name].order[prev_ndx] in names_list:
                    ins_ndx = names_list.index(rules_sets[rules_set_name].order[prev_ndx]) + 1
                else:
                    ins_ndx = 0
                lvls_lst.insert(ins_ndx, (lvl_name, [rules_set_name]))
    return lvls_lst


def create_help_message(rules_sets):
    """
    Creates the message to be displayed when help is provided.
    """
    level_names = create_levels_list(rules_sets)
    message = """
    %prog [options] parameter_file

    The parameter_file is similar to, but not exactly like, parameter
    files for OCSSW processing programs:
     - It has sections separated by headers which are denoted by "["
        and "]".
    The section named "main" is required.  Its allowed options are:
        ifile - Required entry naming the input file(s) to be processed.
        use_nrt_anc - use near real time ancillary data
        keepfiles - keep all the data files generated
        overwrite - overwrite any data files which already exist
        use_existing  - use any data files which already exist

        Simultaneous use of both the overwrite and use_existing options
        is not permitted.

    The names for other sections are the programs for which that section's
    entries are to be applied.  Intermediate sections which are required for the
    final level of processing do not need to be defined if their default options
    are acceptable.  A section can be empty.  The final level of processing
    must have a section header, even if no entries appear within that section.
     - Entries within a section appear as key=value.  Comma separated lists of
    values can be used when appropriate.
     - Comments are marked by "#"; anything appearing on a line after that
    character is ignored.  A line beginning with a "#" is completely ignored.

    In addition to the main section, the following sections are allowed:
        Section name:           Applicable Instrument(s):
        -------------           -------------------------\n"""

    lvl_name_help = ''
    for lname in level_names:
        lvl_name_help += '        {0:24s}{1}\n'.\
                         format(lname[0] + ':', ', '.join(lname[1]))

    message += lvl_name_help
    message += """
    Example:

    # Sample par file for %prog.
    [main]
    ifile=2010345034027.L1A_LAC
    [l2gen]
    l2prod=chlor_a
    # final processing level
    """
    return message

def do_processing(rules_sets, par_file, cmd_line_ifile=None):
    """
    Perform the processing for each step (element of processor_list) needed.
    """
    global input_file_data
    #todo:  Break this up into smaller parts!
    files_to_keep = []
    files_to_delete = []
    input_files_list = []
    (par_contnts, input_files_list) = get_par_file_contents(par_file,
                                                            FILE_USE_OPTS)
    if cmd_line_ifile:
        skip_par_ifile = True
        if os.path.exists(cmd_line_ifile):
            input_files_list = [cmd_line_ifile]
        else:
            msg = 'Error! Specified ifile {0} does not exist.'.\
                  format(cmd_line_ifile)
            sys.exit(msg)
    else:
        skip_par_ifile = False
    if par_contnts['main']:
        if (not skip_par_ifile) and (not 'ifile' in par_contnts['main']):
            msg = 'Error! No ifile specified in the main section of {0}.'.\
                  format(par_file)
            sys.exit(msg)
        # Avoid overwriting file options that are already turned on in cfg_data
        # (from command line input).
        keepfiles, use_existing, overwrite = get_file_handling_opts(par_contnts)
        if keepfiles:
            cfg_data.keepfiles = True
        if use_existing:
            cfg_data.use_existing = True
        if overwrite:
            cfg_data.overwrite = True
        if 'use_nrt_anc' in par_contnts['main'] and \
           int(par_contnts['main']['use_nrt_anc']) == 0:
            cfg_data.get_anc = False
        if 'odir' in par_contnts['main']:
            dname = par_contnts['main']['odir']
            if os.path.exists(dname):
                if os.path.isdir(dname):
                    if cfg_data.output_dir_is_settable:
                        cfg_data.output_dir = os.path.realpath(dname)
                    else:
                        log_msg = 'Ignoring par file specification for output directory, {0}; using command line value, {1}.'.format(par_contnts['main']['odir'], cfg_data.output_dir)
                        logging.info(log_msg)
                else:
                    msg = 'Error! {0} is not a directory.'.format(dname)
                    sys.exit(msg)
            else:
                msg = 'Error! {0} does not exist.'.format(dname)
                sys.exit(msg)

    logging.debug('cfg_data.overwrite: ' + str(cfg_data.overwrite))
    logging.debug('cfg_data.use_existing: ' + str(cfg_data.use_existing))
    logging.debug('cfg_data.keepfiles: ' + str(cfg_data.keepfiles))
    if cfg_data.overwrite and cfg_data.use_existing:
        err_msg = 'Error! Incompatible options overwrite and use_existing were found in {0}.'.format(par_file)
        log_and_exit(err_msg)
    if len(input_files_list) == 1:
        if MetaUtils.is_ascii_file(input_files_list[0]):
            input_files_list = read_file_list_file(input_files_list[0])
    input_file_data = get_input_files_type_data(input_files_list)
    if not input_file_data:
        log_and_exit('No valid data files were specified for processing.')
    logging.debug("input_file_data: " + str(input_file_data))
    first_file_key = list(input_file_data.keys())[0]
    logging.debug("first_file_key: " + first_file_key)
    instrument = input_file_data[first_file_key][1].split()[0]
    logging.debug("instrument: " + instrument)
    if instrument in rules_sets:
        rules = rules_sets[instrument]
    else:
        rules = rules_sets['general']

    src_files = get_source_files(input_file_data)
    lowest_src_lvl = get_lowest_source_level(src_files)
    logging.debug("lowest_source_level: " + str(lowest_src_lvl))
    processors = get_processors(instrument, par_contnts, rules, lowest_src_lvl)
    logging.debug("processors: " + str(processors))
    if cfg_data.tar_filename:
        tar_file = tarfile.open(cfg_data.tar_filename, 'w')
    proc_name_list = ', '.join([p.target_type for p in processors])
    print ('{0}: {1} processors to run: {2}'.format(cfg_data.prog_name,
                                                    len(processors),
                                                    proc_name_list))
    if 'geofile' in par_contnts['main']:
        for proc in processors:
            proc.geo_file = par_contnts['main']['geofile']
    sys.stdout.flush()
    try:
        for ndx, proc in enumerate(processors):
            print ('Running {0}: processor {1} of {2}.'.format(
                proc.target_type, ndx + 1, len(processors)))
            logging.debug('')
            log_msg = 'Processing for {0}:'.format(proc.target_type)
            logging.debug(log_msg)
            proc.out_directory = cfg_data.output_dir
            if cfg_data.timing:
                proc_timer = benchmark_timer.BenchmarkTimer()
                proc_timer.start()
            proc_src_types = proc.rule_set.rules[proc.target_type].src_file_types
            src_key = None
            if proc_src_types[0] == 'l1':
                if 'level 1a' in src_files:
                    src_key = 'level 1a'
                elif 'level 1b' in src_files:
                    src_key = 'level 1b'
            elif proc_src_types[0] in src_files:
                src_key = proc_src_types[0]
            else:
                for cand_proc in reversed(processors[:ndx]):
                    if SUFFIXES[cand_proc.target_type] == \
                       proc.rule_set.rules[proc.target_type].src_file_types[0]:
                        if cand_proc.target_type in src_files:
                            src_key = cand_proc.target_type
                            break
                if src_key is None:
                    err_msg = 'Error! Cannot find source files for {0}.'.\
                              format(proc.target_type)
                    log_and_exit(err_msg)
            logging.debug('proc_src_types:')
            logging.debug('\n  '.join([pst for pst in proc_src_types]))
            if proc.requires_batch_processing():
                logging.debug('Performing batch processing for ' + str(proc))
                out_file = run_batch_processor(ndx, processors,
                                               src_files[src_key])
                if proc.target_type in src_files:
                    if not out_file in src_files[proc.target_type]:
                        src_files[proc.target_type].append(out_file)
                else:
                    src_files[proc.target_type] = [out_file]
            else:
                if proc.rule_set.rules[proc.target_type].action:
                    logging.debug('Performing nonbatch processing for ' +
                                  str(proc))
                    src_file_sets = get_source_file_sets(proc_src_types,
                                                         src_files, src_key,
                                                         proc.rule_set.rules[proc.target_type].requires_all_sources)
                    success_count = 0
                    for file_set in src_file_sets:
                        out_file = run_nonbatch_processor(ndx, processors, file_set)
                        if out_file:
                            success_count += 1
                            if proc.target_type in src_files:
                                if not out_file in src_files[proc.target_type]:
                                    src_files[proc.target_type].append(out_file)
                            else:
                                src_files[proc.target_type] = [out_file]
                    if success_count == 0:
                        msg = 'The {0} processor produced no output files.'.format(proc.target_type)
                        logging.info(msg)
                else:
                    msg = '-I- There is no way to create {0} files for {1}.'.format(proc.target_type, proc.instrument)
                    logging.info(msg)
            if cfg_data.keepfiles or proc.keepfiles:
                if out_file:
                    files_to_keep.append(out_file)
                    if cfg_data.tar_filename:
                        tar_file.add(out_file)
                    logging.debug('Added ' + out_file + ' to tar file list')
            #todo: add "target" files to files_to_keep and other files to files_to_delete, as appropriate
            if cfg_data.timing:
                proc_timer.end()
                timing_msg = 'Time for {0} process: {1}'.format(
                    proc.target_type, proc_timer.get_total_time_str())
                print (timing_msg)
                logging.info(timing_msg)
#             print ('{0}: processor {1} of {2} complete.'.format(
#                 cfg_data.prog_name, ndx + 1, len(processors)))
            sys.stdout.flush()
            logging.debug('Processing complete for "%s".', proc.target_type)
    except Exception:
        if DEBUG:
            err_msg = get_traceback_message()
            log_and_exit(err_msg)
        else:
            err_msg = "Unrecoverable error encountered in processing."
            log_and_exit(err_msg)
    finally:
        if cfg_data.tar_filename:
            tar_file.close()
            logging.debug('closed tar file')
        # Since the clean_files function will delete hidden files as well as
        # the files in files_to_delete, it should be called regardless of
        # whether files_to_delete contains anything.
        clean_files(files_to_delete)
    if cfg_data.verbose:
        print ("Processing complete.")
        sys.stdout.flush()
    logging.debug("Processing complete.")
    return

def execute_command(command):
    """
    Execute what is contained in command and then output the results to log
    files and the console, as appropriate.
    """
    if DEBUG:
        print ("Entering execute_command, cfg_data.verbose =",
               cfg_data.verbose)
        log_msg = 'Executing command:\n  {0}'.format(command)
        logging.debug(log_msg)
    subproc = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    std_out, err_out = subproc.communicate()
    status = subproc.returncode
    logging.info(std_out)
    logging.info(err_out)
    if cfg_data.verbose:
        print (std_out)
    return status

def extract_par_section(par_contents, section):
    """
    Returns a single section (e.g. L1a, GEO, L1B, L2, etc.) from the "par" file.
    """
    sect_dict = {}
    for key in list(par_contents[section].keys()):
        sect_dict[key] = par_contents[section][key]
    return sect_dict

def find_geo_file(inp_file):
    """
    Searches for a GEO file corresponding to inp_file.  If that GEO file exists,
    returns that file name; otherwise, returns None.
    """
    src_dir = os.path.dirname(inp_file)
    src_base = os.path.basename(inp_file)
    geo_base = src_base.rsplit('.', 1)[0]
    geo_file = os.path.join(src_dir, geo_base + '.GEO')
    if not os.path.exists(geo_file):
        geo_file = None
    return geo_file

def find_viirs_geo_file(proc, first_svm_file):
    """
    Searches for a GEO file corresponding to first_svm_file.  If that GEO file
    exists, returns that file name; otherwise, returns None.
    """
    fname = first_svm_file.replace('SVM01', 'GMTCO').rstrip()
    if not os.path.exists(fname):
        fname = None
    return fname

def get_batch_output_name(file_set, suffix):
    """
    Returns the output file for a "batch" run, i.e. a process that can accept
    multiple inputs, such as l2bin or l3bin.
    """
    mission_prefixes = ['A', 'C', 'O', 'S', 'T']
    stem = 'out'
    if not len(file_set):     # == 0:
        err_msg = "Error!  An output file name could not be determined."
        log_and_exit(err_msg)
    elif len(file_set) == 1:
        stem = os.path.splitext(file_set[0])[0]
    else:
        earliest_file = file_set[0]
        latest_file = file_set[0]
        earliest_file_date = get_file_date(earliest_file)
        latest_file_date = get_file_date(latest_file)
        for cur_file in file_set[1:]:
            file_date = get_file_date(cur_file)
            if file_date < earliest_file_date:
                earliest_file = cur_file
                earliest_file_date = file_date
            elif file_date > latest_file_date:
                latest_file = cur_file
                latest_file_date = file_date
        if (earliest_file[0] == latest_file[0]) and \
           (earliest_file[0] in mission_prefixes):
            stem = earliest_file[0]
        else:
            stem = ''
        earliest_file_date_stamp = earliest_file_date.strftime('%Y%j')
        latest_file_date_stamp = latest_file_date.strftime('%Y%j')
        if earliest_file_date_stamp == latest_file_date_stamp:
            stem += earliest_file_date_stamp
        else:
            stem += earliest_file_date_stamp + latest_file_date_stamp
    return ''.join([stem, '.', suffix])

def get_data_file_option(par_contents, opt_text):
    """
    If found in par_contents, the value for the option specified by opt_text
    is returned; otherwise, False is returned.
    """
    opt_found = False
    if opt_text in par_contents['main']:
        opt_str = par_contents['main'][opt_text].upper()
        opt_found = mlp_utils.is_option_value_true(opt_str)
    return opt_found

def get_extract_params(proc):
    """
    Run the lonlat2pixline program and return the parameters found.
    """
    if proc.geo_file:
        # MODIS
        in_file = proc.geo_file
    else:
        # SeaWiFS
        in_file = proc.input_file
    args = ' '.join([in_file, proc.par_data['SWlon'],
                     proc.par_data['SWlat'], proc.par_data['NElon'],
                     proc.par_data['NElat']])
    lonlat_prog = os.path.join(proc.ocssw_bin, 'lonlat2pixline')
    lonlat_cmd = ' '.join([lonlat_prog, args])
    logging.debug('Executing lonlat2pixline command: "%s"', lonlat_cmd)
    process_output = subprocess.Popen(lonlat_cmd, shell=True,
                                      stdout=subprocess.PIPE).communicate()[0]
    lonlat_output = process_output.split(chr(10))
    start_line = None
    end_line = None
    start_pixel = None
    end_pixel = None
    for line in lonlat_output:
        if 'sline' in line:
            start_line = int(line.split('=')[1])
        if 'eline' in line:
            end_line = int(line.split('=')[1])
        if 'spixl' in line:
            start_pixel = int(line.split('=')[1])
        if 'epixl' in line:
            end_pixel = int(line.split('=')[1])
    return start_line, end_line, start_pixel, end_pixel

def get_file_date(filename):
    """
    Get a Python Date object from a recognized file name's year and day of year.
    """
    base_filename = os.path.basename(filename)
    if re.match(r'[ACMOQSTV]\d\d\d\d\d\d\d.*', base_filename):
        year = int(base_filename[1:5])
        doy = int(base_filename[5:8])
    elif re.match(r'\d\d\d\d\d\d\d.*', base_filename):
        # Some Aquarius
        year = int(base_filename[0:4])
        doy = int(base_filename[4:7])
    elif re.match(r'\w*_npp_d\d\d\d\d\d\d\d_.*', base_filename):
        # NPP
        prefix_removed_name = re.sub(r'\w*_npp_d', '', base_filename)
        year = int(prefix_removed_name[0:4])
        doy = int(prefix_removed_name[5:7])
    else:
        err_msg = 'Unable to determine date for {0}'.format(filename)
        log_and_exit(err_msg)
    file_date = datetime.datetime(year, 1, 1) + datetime.timedelta(doy - 1)
    return file_date

def get_file_handling_opts(par_contents):
    """
    Returns the values of the file handling options in par_contents.
    """
    keepfiles = get_data_file_option(par_contents, 'keepfiles')
    use_existing = get_data_file_option(par_contents, 'use_existing')
    overwrite = get_data_file_option(par_contents, 'overwrite')
    return keepfiles, use_existing, overwrite

def get_input_files(par_data):
    """
    Get input files found in the uber par file's ifile line, a file list file,
    or both.  Ensure that the list contains no duplicates.
    """
    #inp_file_list = None
    from_ifiles = []
    from_infilelist = []
    if 'ifile' in par_data['main']:
        inp_file_str = par_data['main']['ifile'].split('#', 2)[0]
        cleaned_str = re.sub(r'[\t,:\[\]()"\']', ' ', inp_file_str)
        from_ifiles = cleaned_str.split()
    if 'infilelist' in par_data['main']:
        infilelist_name = par_data['main']['infilelist']
        if os.path.exists(infilelist_name):
            if os.path.isfile(infilelist_name) and \
              os.access(infilelist_name, os.R_OK):
                with open(infilelist_name, 'rt') as in_file_list_file:
                    inp_lines = in_file_list_file.readlines()
                from_infilelist = [fn.rstrip() for fn in inp_lines
                                   if not re.match(r'^\s*#', fn)]
    if len(from_ifiles) == 0 and len(from_infilelist) == 0:
        return None
    # Make sure there are no duplicates.  Tests with timeit showed that
    # list(set()) is much faster than a "uniqify" function.
    return list(set(from_ifiles + from_infilelist))

def get_input_files_type_data(input_files_list):
    """
    Returns a dictionary with the the file_type (L0, L1A, L2, etc) and
    instrument for each file in the input list.
    """
    converter = {
        'geo': 'geo',
        'level 0': 'level 0',
        'level 1 browse data': 'l1brsgen',
        'level 1a': 'level 1a',
        'level 1b': 'level 1b',
        'sdr': 'level 1b',
        'level 2': 'l2gen',
        'level 3 binned': 'l3bin',
        'level 3 smi': 'smigen'
    }
    input_file_type_data = {}
    for inp_file in input_files_list:
        # if os.path.dirname((inp_file)) == '':
        #     inp_path = os.path.join(os.getcwd(), inp_file)
        # else:
        #     inp_path = inp_file
        file_typer = get_obpg_file_type.ObpgFileTyper(inp_file)
        file_type, file_instr = file_typer.get_file_type()
        #if file_type in converter:
        #    file_type = converter[file_type.lower()]
        #else:
        #    err_msg =
        # 'Error! Cannot process file type {0} of {1}'.format(file_type,
        #  inp_file)
        if file_type.lower() in converter:
            file_type = converter[file_type.lower()]
            input_file_type_data[inp_file] = (file_type, file_instr.lower())
        else:

        #     input_file_type_data[inp_file] = ('unknown', 'unknown')
            warn_msg = "Warning: Unable to determine a type for file {0}.  It will not be processed.".format(inp_file)
            print (warn_msg)
            logging.info(warn_msg)
    return input_file_type_data

def get_intermediate_processors(existing_procs, rules, lowest_source_level):
    """
    Create processor objects for products which are needed, but not explicitly
    specified in the par file.
    """
    existing_products = [proc.target_type for proc in existing_procs]
    intermediate_products = get_intermediate_products(existing_products, rules,
                                                      lowest_source_level)
    intermediate_processors = []
    for prod in intermediate_products:
        # Create a processor for the product and add it to the intermediate
        # processors list
        if not prod in existing_products:
            new_proc = processor.Processor('', rules, prod, {},
                                           cfg_data.hidden_dir)
            intermediate_processors.append(new_proc)
    return intermediate_processors

def get_intermediate_products(existing_prod_names, ruleset,
                              lowest_source_level):
    """
    Find products which are needed, but not explicitly specified by the
    par file.
    """
    required_progs = []
    for prog in existing_prod_names:
        candidate_progs = get_required_programs(prog, ruleset,
                                                lowest_source_level)
        if not isinstance(candidate_progs, type(None)):
            for candidate_prog in candidate_progs:
                required_progs.append(candidate_prog)
    required_progs = uniqify_list(required_progs)
    required_progs.sort()
    return required_progs

def get_l2_extension():
    """
    Returns the extension for an L2 file.  For the time being, this is
    just '.L2'; however, different extensions may be wanted in the future, thus
    this function is in place.
    """
    return '.L2'

def get_l3bin_extension():
    """
    Returns the extension for an L3 Binned file.  For the time being, this is
    just '.L3bin'; however, different extensions may be wanted in the future,
    thus this function is in place.
    """
    return '.L3b'

def get_lowest_source_level(source_files):
    """
    Find the level of the lowest level source file to be processed.
    """
    if len(source_files) == 1:
        return list(source_files.keys())[0]
    else:
        lowest = list(source_files.keys())[0]
        for key in list(source_files.keys())[1:]:
            if key < lowest:
                lowest = key
        return lowest

def get_options(par_data):
    """
    Extract the options for a program to be run from the corresponding data in
    the uber par file.
    """
    options = ''
    for key in par_data:
        if key == 'ofile':
            log_and_exit('Error!  The "ofile" option is not permitted.')
        else:
            if not key.lower() in FILE_USE_OPTS:
                if par_data[key]:
                    options += ' ' + key + '=' + par_data[key]
                else:
                    options += ' ' + key
    return options

def get_output_name(inp_files, targ_prog, suite=None, oformt=None, res=None):
    """
    Determine what the output name would be if targ_prog is run on input_files.
    """
    cl_opts = optparse.Values()
    cl_opts.suite = suite
    cl_opts.oformat = oformt
    cl_opts.resolution = res
    if not isinstance(inp_files, list):
        data_file = get_obpg_data_file_object(inp_files)
        nm_findr = name_finder_utils.get_level_finder([data_file], targ_prog,
                                                      cl_opts)
    else:
        nm_findr = name_finder_utils.get_level_finder(inp_files, targ_prog,
                                                      cl_opts)
    return nm_findr.get_next_level_name()

def get_output_name2(input_name, input_files, suffix):
    """
    Determine the output name for a program to be run.
    """
    # Todo: rename to get_output_name and delete other get_output_name
    output_name = None
    if input_name in input_files:
        if input_files[input_name][0] == 'level 0' and \
           input_files[input_name][1].find('modis') != -1:
            if input_files[input_name][1].find('aqua') != -1:
                first_char = 'A'
            else:
                first_char = 'T'
            time_stamp = ''
            if os.path.exists(input_name + '.const'):
                with open(input_name + '.const') as constructor_file:
                    constructor_data = constructor_file.readlines()
                for line in constructor_data:
                    if line.find('starttime=') != -1:
                        start_time = line[line.find('=') + 1].strip()
                        break
                time_stamp = ProcUtils.date_convert(start_time, 't', 'j')
            else:
                if re.match(r'MOD00.P\d\d\d\d\d\d\d\.\d\d\d\d', input_name):
                    time_stamp = input_name[7:14] + input_name[15:19] + '00'
                else:
                    err_msg = "Cannot determine time stamp for input file {0}".\
                              format(input_name)
                    log_and_exit(err_msg)
            output_name = first_char + time_stamp + '.L1A'
        else:
#            if input_files[input_name] == ''
            (dirname, basename) = os.path.split(input_name)
            basename_parts = basename.rsplit('.', 2)
            output_name = os.path.join(dirname, basename_parts[0] + '.' +
                                       suffix)
    else:
        (dirname, basename) = os.path.split(input_name)
        basename_parts = basename.rsplit('.', 2)
        output_name = os.path.join(dirname, basename_parts[0] + '.' + suffix)
    return output_name

def get_par_file_contents(par_file, acceptable_single_keys):
    """
    Return the contents of the input "par" file.
    """
    acceptable_par_keys = {
        'level 0' : 'level 0', 'l0' : 'level 0',
        'level 1a' : 'level 1a', 'l1a' : 'level 1a', 'l1agen': 'level 1a',
        'modis_L1A.py': 'level 1a',

        'l1aextract_modis' : 'l1aextract_modis',
        'l1aextract_seawifs' : 'l1aextract_seawifs',
        'l1brsgen' : 'l1brsgen',
        'geo' : 'geo', 'modis_GEO.py': 'geo',
        'level 1b' : 'level 1b', 'l1b' : 'level 1b', 'l1bgen' : 'level 1b',
        'modis_L1B.py': 'level 1b',
        'level 2' : 'l2gen',
        'l2gen' : 'l2gen',
        'l2bin' : 'l2bin',
        'l2brsgen' : 'l2brsgen',
        'l2extract' : 'l2extract',
        'l2mapgen' : 'l2mapgen',
        'l3bin' : 'l3bin',
        'l3mapgen' : 'l3mapgen',
        'smigen' : 'smigen',
        'main' : 'main'
    }
    if cfg_data.verbose:
        print ("Processing %s" % par_file)
    par_reader = uber_par_file_reader.ParReader(par_file,
                                                acceptable_single_keys,
                                                acceptable_par_keys)
    par_contents = par_reader.read_par_file()
    ori_keys = list(par_contents.keys())
    for key in ori_keys:
        if key in acceptable_par_keys:
            if key != acceptable_par_keys[key]:
                par_contents[acceptable_par_keys[key]] = par_contents[key]
                del par_contents[key]
        else:
            acc_key_str = ', '.join(list(acceptable_par_keys.keys()))
            err_msg = """Error!  Parameter file {0} contains a section titled "{1}", which is not a recognized program.
The recognized programs are: {2}""".format(par_file, key, acc_key_str)

            log_and_exit(err_msg)
    if 'main' in par_contents:
        input_files_list = get_input_files(par_contents)
    else:
        err_msg = 'Error! Could not find section "main" in {0}'.format(par_file)
        log_and_exit(err_msg)
    return par_contents, input_files_list

def get_processors(instrument, par_contents, rules, lowest_source_level):
    """
    Determine the processors which are needed.
    """
    processors = []
    for key in list(par_contents.keys()):
        if key != 'main':
            section_contents = extract_par_section(par_contents, key)
            proc = processor.Processor(instrument, rules, key, section_contents,
                                       cfg_data.hidden_dir)
            processors.append(proc)
    if processors:
        processors.sort()    # needs sorted for get_intermediate_processors
        processors += get_intermediate_processors(processors, rules,
                                                  lowest_source_level)
        processors.sort()
    return processors

def get_required_programs(target_program, ruleset, lowest_source_level):
    """
    Returns the programs required too produce the desired final output.
    """
    programs_to_run = []
    cur_rule = ruleset.rules[target_program]
    src_types = cur_rule.src_file_types
    if src_types[0] == cur_rule.target_type:
        programs_to_run = [target_program]
    else:
        for src_type in src_types:
            if src_type in ruleset.rules:
                if ruleset.order.index(src_type) > \
                   ruleset.order.index(lowest_source_level):
                    programs_to_run.insert(0, src_type)
                    if len(src_types) > 1:
                        programs_to_run.insert(0, src_types[1])
                    programs_to_add = get_required_programs(src_type, ruleset,
                                                            lowest_source_level)
                    for prog in programs_to_add:
                        programs_to_run.insert(0, prog)
    return programs_to_run

def get_source_geo_files(source_files, proc_src_types, proc_src_ndx):
    """
    :param source_files: list of source files
    :param proc_src_types: list of source types for the processor
    :param proc_src_ndx: index into the proc_src_types list pointing to the
                         source type to use to get the input files
    :return: list of GEO files that correspond to the files in source_files
    """
    inp_files = source_files[proc_src_types[proc_src_ndx]]
    geo_files = []
    for inp_file in inp_files:
        geo_file = find_geo_file(inp_file)
        if geo_file:
            geo_files.append(geo_file)
        else:
            err_msg = 'Error! Cannot find GEO ' \
                      'file {0}.'.format(geo_file)
            log_and_exit(err_msg)
    return geo_files

def get_source_file_sets(proc_src_types, source_files, src_key, requires_all_sources):
    """
    Returns the set of source files needed.
    """
    if len(proc_src_types) == 1:
        try:
            src_file_sets = source_files[src_key]
        except Exception:
            # print "Exception encountered: "
            # e_info = sys.exc_info()
            # err_msg = ''
            # for info in e_info:
            #     err_msg += "  " + str(info)
            if DEBUG:
                err_msg = get_traceback_message()
                log_and_exit(err_msg)
            else:
                err_msg = 'Error! Unable to determine what source files are required for the specified output files.'
                log_and_exit(err_msg)
    else:
        if requires_all_sources:
            if len(proc_src_types) == 2:
                if proc_src_types[0] in source_files \
                        and proc_src_types[1] in source_files:
                    src_file_sets = list(zip(source_files[proc_src_types[0]],
                                        source_files[proc_src_types[1]]))
                else:
                    if proc_src_types[0] in source_files:
                        if proc_src_types[1] == 'geo':
                            geo_files = get_source_geo_files(source_files, proc_src_types, 0)
                            src_file_sets = list(zip(source_files[proc_src_types[0]],
                                                geo_files))
                        else:
                            err_msg = 'Error! Cannot find all {0} and' \
                                      ' {1} source files.'.format(proc_src_types[0],
                                                                  proc_src_types[1])
                            log_and_exit(err_msg)
                    elif proc_src_types[1] in source_files:
                        if proc_src_types[0] == 'geo':
                            geo_files = get_source_geo_files(source_files, proc_src_types, 1)
                            src_file_sets = list(zip(source_files[proc_src_types[1]],
                                                geo_files))
                        else:
                            err_msg = 'Error! Cannot find all {0} and' \
                                      ' {1} source files.'.format(proc_src_types[0],
                                                                  proc_src_types[1])
                            log_and_exit(err_msg)
                    else:
                        err_msg = 'Error! Cannot find all source files.'
                        log_and_exit(err_msg)
            else:
                err_msg = 'Error! Encountered too many source file types.'
                log_and_exit(err_msg)
        else:
            for proc_src_type in proc_src_types:
                if proc_src_type in source_files:
                    src_file_sets = source_files[proc_src_type]
    return src_file_sets

def get_source_files(input_files):
    """
    Returns a dictionary containing the programs to be run (as keys) and the
    a list of files on which that program should be run.
    """
    source_files = {}
    for file_path in input_files:
        ftype = input_files[file_path][0]
        if ftype in source_files:
            source_files[ftype].append(file_path)
        else:
            source_files[ftype] = [file_path]
    return source_files

def get_source_products_types(targt_prod, ruleset):
    """
    Return the list of source product types needed to produce the final product.
    """
    src_prod_names = [targt_prod]
    targt_pos = ruleset.order.index(targt_prod)
    new_prod_names = []
    for pos in range(targt_pos, 1, -1):
        for prod_name in src_prod_names:
            if ruleset.rules[ruleset.order[pos]].target_type == prod_name:
                for src_typ in ruleset.rules[ruleset.order[pos]].src_file_types:
                    new_prod_names.append(src_typ)
    src_prod_names += new_prod_names
    return src_prod_names

def get_traceback_message():
    """
    Returns an error message built from traceback data.
    """
    exc_parts = [str(l) for l in sys.exc_info()]
    err_type_parts = str(exc_parts[0]).strip().split('.')
    err_type = err_type_parts[-1].strip("'>")
    tb_data = traceback.format_exc()
    tb_line = tb_data.splitlines()[-3]
    line_num = tb_line.split(',')[1]
    st_data = traceback.extract_stack()
    err_file = os.path.basename(st_data[-1][0])
    msg = 'Error!  The {0} program encountered an unrecoverable {1}, {2}, at {3} of {4}!'.\
        format(cfg_data.prog_name,
               err_type, exc_parts[1], line_num.strip(), err_file)
    return msg



def log_and_exit(error_msg):
    """
    Record error_msg in the debug log, then exit with error_msg going to stderr
    and an exit code of 1; see:
        http://docs.python.org/library/sys.html#exit.
    """
    logging.info(error_msg)
    sys.exit(error_msg)

def main():
    """
    main processing function.
    """
    global cfg_data
    global DEBUG
    rules_sets = build_rules()
    cl_parser = optparse.OptionParser(usage=create_help_message(rules_sets),
                                      version=' '.join(['%prog', __version__]))
    (options, args) = process_command_line(cl_parser)

    if len(args) < 1:
        print ("\nError! No file specified for processing.\n")
        cl_parser.print_help()
    else:
        if options.debug:
            # Don't just set DEBUG = options.debug, as that would override the
            # in-program setting.
            DEBUG = True
        check_options(options)
        cfg_data = ProcessorConfig('.seadas_data', os.getcwd(),
                                   options.verbose, options.overwrite,
                                   options.use_existing, options.tar_file,
                                   options.timing, options.odir)
        if not os.access(cfg_data.hidden_dir, os.R_OK):
            log_and_exit("Error!  The working directory is not readable!")
        if os.path.exists(args[0]):
            log_timestamp = datetime.datetime.today().strftime('%Y%m%d%H%M%S')
            start_logging(log_timestamp)
            try:
                if cfg_data.timing:
                    main_timer = benchmark_timer.BenchmarkTimer()
                    main_timer.start()
                    do_processing(rules_sets, args[0])
                    main_timer.end()
                    timing_msg = 'Total processing time: {0}'.format(
                        str(main_timer.get_total_time_str()))
                    print (timing_msg)
                    logging.info(timing_msg)
                else:
                    if options.ifile:
                        do_processing(rules_sets, args[0], options.ifile)
                    else:
                        do_processing(rules_sets, args[0])
            except Exception:
                if DEBUG:
                    err_msg = get_traceback_message()
                    log_and_exit(err_msg)
                else:
                    # todo: make a friendlier error message
                    err_msg = 'Unanticipated error encountered during processing!'
                    log_and_exit(err_msg)
        else:
            err_msg = 'Error! Parameter file {0} does not exist.'.\
                      format(args[0])
            sys.exit(err_msg)
        logging.shutdown()
    return 0

def process_command_line(cl_parser):
    """
    Get arguments and options from the calling command line.
    To be consistent with other OBPG programs, an underscore ('_') is used for
    multiword options, instead of a dash ('-').
    """
    cl_parser.add_option('--debug', action='store_true', dest='debug',
                         default=False, help=optparse.SUPPRESS_HELP)
    cl_parser.add_option('-k', '--keepfiles', action='store_true',
                         dest='keepfiles', default=False,
                         help='keep files created during processing')
    cl_parser.add_option('--ifile', action='store', type='string',
                         dest='ifile', help="input file")
    cl_parser.add_option('--output_dir', '--odir',
                         action='store', type='string', dest='odir',
                         help="user specified directory for output")
    cl_parser.add_option('--overwrite', action='store_true',
                         dest='overwrite', default=False,
                         help='overwrite files which already exist (default = stop processing if file already exists)')
    cl_parser.add_option('-t', '--tar', type=str, dest='tar_file',
                         help=optparse.SUPPRESS_HELP)
    cl_parser.add_option('--timing', dest='timing', action='store_true',
                         default=False,
                         help='report time required to run each program and total')
    cl_parser.add_option('--use_existing', action='store_true',
                         dest='use_existing', default=False,
                         help='use files which already exist (default = stop processing if file already exists)')
    cl_parser.add_option('-v', '--verbose',
                         action='store_true', dest='verbose', default=False,
                         help='print status messages to stdout')

    (options, args) = cl_parser.parse_args()
    for ndx, cl_arg in enumerate(args):
        if cl_arg.startswith('par='):
            args[ndx] = cl_arg.lstrip('par=')
    if options.overwrite and options.use_existing:
        log_and_exit('Error!  Options overwrite and use_existing cannot be ' + \
                     'used simultaneously.')
    return options, args

def read_file_list_file(flf_name):
    """
    Reads flf_name and returns the list of files to be processed.
    """
    files_list = []
    bad_lines = []
    with open(flf_name, 'rt') as flf:
        inp_lines = flf.readlines()
    for line in inp_lines:
        fname = line.split('#')[0].strip()
        if fname != '':
            if os.path.exists(fname):
                files_list.append(fname)
            else:
                bad_lines.append(fname)
    if len(bad_lines) > 0:
        err_msg = 'Error!  File {0} specified the following input files which could not be located:\n   {1}'.\
                  format(flf_name, ', '.join([bl for bl in bad_lines]))
        log_and_exit(err_msg)
    return files_list

def run_batch_processor(ndx, processors, file_set):
    """
    Run a processor, e.g. l2bin, which processes batches of files.
    """
    logging.debug('in run_batch_processor, ndx = %d', ndx)
    if os.path.exists((file_set[0])) and tarfile.is_tarfile(file_set[0]):
        processors[ndx].input_file = file_set[0]
    else:
        timestamp = time.strftime('%Y%m%d_%H%M%S', time.gmtime(time.time()))
        file_list_name = cfg_data.hidden_dir + os.sep + 'files_' + \
                         processors[ndx].target_type + '_' + timestamp + '.lis'
        with open(file_list_name, 'wt') as file_list:
            for fname in file_set:
                file_list.write(fname + '\n')
        processors[ndx].input_file = file_list_name
    data_file_list = []
    finder_opts = {}
    for fspec in file_set:
        dfile = get_obpg_data_file_object(fspec)
        data_file_list.append(dfile)
    if 'suite' in processors[ndx].par_data:
        finder_opts['suite'] = processors[ndx].par_data['suite']
    elif 'prod' in processors[ndx].par_data:
        finder_opts['suite'] = processors[ndx].par_data['prod']
    if 'resolution' in processors[ndx].par_data:
        finder_opts['resolution'] = processors[ndx].par_data['resolution']
    if 'oformat' in processors[ndx].par_data:
        finder_opts['oformat'] = processors[ndx].par_data['oformat']
    name_finder = name_finder_utils.get_level_finder(data_file_list,
                                                     processors[ndx].target_type,
                                                     finder_opts)
    processors[ndx].output_file = os.path.join(processors[ndx].out_directory,
                                               name_finder.get_next_level_name())
    if DEBUG:
        log_msg = "Running {0} with input file {1} to generate {2} ".\
                  format(processors[ndx].target_type,
                         processors[ndx].input_file,
                         processors[ndx].output_file)
        logging.debug(log_msg)
    processors[ndx].execute()
    return processors[ndx].output_file

def run_bottom_error(proc):
    """
    Exits with an error message when there is an attempt to process a source
    file at the lowest level of a rule chain.
    """
    err_msg = 'Error!  Attempting to create {0} product, but no creation program is known.'.format(proc.target_type)
    log_and_exit(err_msg)

def run_geolocate_viirs(proc):
    """
    Set up and run the geolocate_viirs program, returning the exit status of the run.
    """
    logging.debug('In run_geolocate_viirs')
    prog = build_executable_path('geolocate_viirs')
    #### Temporary, until the local environment is set up
#     prog='/accounts/melliott/seadas/ocssw/bin/geolocate_viirs'
    # os.path.join(proc.ocssw_root, 'run', 'scripts', 'modis_GEO.py')
    if not prog:
        err_msg = 'Error! Cannot find program geolocate_viirs.'
        logging.info(err_msg)
        sys.exit(err_msg)
    args = ''.join(['-ifile=', proc.input_file, ' -geofile_mod=', proc.output_file])
    args += get_options(proc.par_data)
    cmd = ' '.join([prog, args])
    logging.debug("\nRunning: " + cmd)
    return execute_command(cmd)

def run_l1aextract_modis(proc):
    """
    Set up and run l1aextract_modis.
    """
    if 'SWlon' in proc.par_data and 'SWlat' in proc.par_data and\
       'NElon' in proc.par_data and 'NElat' in proc.par_data:
        start_line, end_line, start_pixel, end_pixel = get_extract_params(proc)
        if (start_line is None) or (end_line is None) or (start_pixel is None)\
        or (end_pixel is None):
            err_msg = 'Error! Cannot find l1aextract_modis coordinates.'
            log_and_exit(err_msg)
        l1aextract_prog = os.path.join(proc.ocssw_bin, 'l1aextract_modis')
        l1aextract_cmd = ' '.join([l1aextract_prog, proc.input_file,
                                   str(start_pixel), str(end_pixel),
                                   str(start_line), str(end_line),
                                   proc.output_file])
        logging.debug('Executing l1aextract_modis command: "%s"',
                      l1aextract_cmd)
        status = execute_command(l1aextract_cmd)
        return status

def run_l1aextract_seawifs(proc):
    """
    Set up and run l1aextract_seawifs.
    """
    if 'SWlon' in proc.par_data and 'SWlat' in proc.par_data and\
       'NElon' in proc.par_data and 'NElat' in proc.par_data:
        start_line, end_line, start_pixel, end_pixel = get_extract_params(proc)
        if (start_line is None) or (end_line is None) or (start_pixel is None)\
           or (end_pixel is None):
            err_msg = 'Error! Cannot compute l1aextract_seawifs coordinates.'
            log_and_exit(err_msg)
        l1aextract_prog = os.path.join(proc.ocssw_bin, 'l1aextract_seawifs')
        l1aextract_cmd = ' '.join([l1aextract_prog, proc.input_file,
                                   str(start_pixel), str(end_pixel),
                                   str(start_line), str(end_line), '1', '1',
                                   proc.output_file])
        logging.debug('Executing l1aextract_seawifs command: "%s"',
                      l1aextract_cmd)
        status = execute_command(l1aextract_cmd)
        return status

def run_l1b(proc):
    """
    Sets up and runs an executable program.
    """
    #todo: replace l1bgen with the appropriate proc.whatever
    prog = os.path.join(proc.ocssw_bin, 'l1bgen_generic')
    args = 'ifile=' + proc.input_file + ' '
    args += 'ofile=' + proc.output_file + ' '
    if not proc.geo_file is None:
        args += proc.geo_file + ' '
    args += get_options(proc.par_data)
    cmd = ' '.join([prog, args])
    return execute_command(cmd)

def run_l1brsgen(proc):
    """
    Runs the l1brsgen executable.
    """
    l1brs_suffixes = {'0':'L1_BRS', '1':'L1_BRS', '2':'ppm',
                      '3':'flt', '4':'png',
                      'hdf4': 'hdf', 'bin': 'bin', 'png': 'png',
                      'ppm': 'ppm'}
    prog = os.path.join(proc.ocssw_bin, 'l1brsgen')
    opts = get_options(proc.par_data)
    #output_name = get_output_name(proc.par_data['ifile'], suffix)
    output_name = get_output_name(proc.input_file, 'l1brsgen')
    if 'outmode' in proc.par_data and proc.par_data['outmode']:
        suffix = l1brs_suffixes[proc.par_data['outmode']]
        cmd = ' '.join([prog, opts, ' ifile=' + proc.input_file,
                        'ofile=' + output_name, 'outmode=' + suffix])
    elif 'oformat' in proc.par_data and proc.par_data['oformat']:
        suffix = l1brs_suffixes['oformat']
        cmd = ' '.join([prog, opts, ' ifile=' + proc.input_file,
                        'ofile=' + output_name, 'oformat=' + suffix])
    else:
        # suffix = l1brs_suffixes['0']
        cmd = ' '.join([prog, opts, ' ifile=' + proc.input_file,
                        'ofile=' + output_name])
    logging.debug('Executing: "%s"', cmd)
    status = execute_command(cmd)
    return status

def run_l1mapgen(proc):
    """
    Runs the l1mapgen executable, handling the range of successful return
    values.
    """
    # Instead of a 0 for a successful exit code, the l1mapgen program returns
    # the percentage of pixels mapped, so a range of possible successful values
    # must be accepted.
    # It should be noted that an exit code of 1 is still an error.
    l1map_suffixes = {'0': 'ppm', '1': 'png', '2': 'geotiff'}
    acceptable_min = 2
    acceptable_max = 100
    prog = os.path.join(proc.ocssw_bin, 'l1mapgen')
    opts = get_options(proc.par_data)
    if 'outmode' in proc.par_data:
        suffix = l1map_suffixes[proc.par_data['outmode']]
    else:
        suffix = l1map_suffixes['0']
    output_name = get_output_name(proc.par_data['ifile'], suffix)
    cmd = ' '.join([prog, opts, ' ofile=' + output_name])
    logging.debug('Executing: "%s"', cmd)
    lvl_nm = execute_command(cmd)
    logging.debug('l1mapgen run complete!  Return value: "%s"', lvl_nm)
    if (lvl_nm >= acceptable_min) and (lvl_nm <= acceptable_max):
        return 0
    else:
        return lvl_nm

def run_l2bin(proc):
    """
    Set up for and perform L2 binning.
    """
    prog = os.path.join(proc.ocssw_bin, 'l2bin')
    if not os.path.exists(prog):
        print ("Error!  Cannot find executable needed for {0}".\
              format(proc.rule_set.rules[proc.target_type].action))
    args = 'infile=' + proc.input_file
    args += ' ofile=' + proc.output_file
    args += ' ' + get_options(proc.par_data)
    cmd = ' '.join([prog, args])
    logging.debug('Running l2bin cmd: ' + cmd)
    if cfg_data.verbose:
        print ('l2bin cmd: ' + cmd)
    ret_val = execute_command(cmd)
    if ret_val != 0:
        if os.path.exists(proc.output_file):
            msg = '-I- The l2bin program returned a status value of {0}. Proceeding with processing, using the output l2 bin file {1}'.format(ret_val, proc.output_file)
            logging.info(msg)
            ret_val = 0
        else:
            msg = '-I- The l2bin program produced a bin file with no data. No further processing will be done.'
            sys.exit(msg)
    return ret_val

def run_l2brsgen(proc):
    """
    Runs the l2brsgen executable.
    """
    logging.debug("In run_l2brsgen")
    prog = os.path.join(proc.ocssw_bin, 'l2brsgen')
    opts = get_options(proc.par_data)
    cmd = ' '.join([prog, opts, 'ifile='+proc.input_file,
                    'ofile=' + proc.output_file])
    logging.debug('Executing: "%s"', cmd)
    status = execute_command(cmd)
    return status

def run_l2extract(proc):
    """
    Set up and run l2extract.
    """
    if 'SWlon' in proc.par_data and 'SWlat' in proc.par_data and \
       'NElon' in proc.par_data and 'NElat' in proc.par_data:
        start_line, end_line, start_pixel, end_pixel = get_extract_params(proc)
        if (start_line is None) or (end_line is None) or (start_pixel is None) \
           or (end_pixel is None):
            err_msg = 'Error! Could not compute coordinates for l2extract.'
            log_and_exit(err_msg)
        l2extract_prog = os.path.join(proc.ocssw_bin, 'l2extract')
        l2extract_cmd = ' '.join([l2extract_prog, proc.input_file,
                                  str(start_pixel), str(end_pixel),
                                  str(start_line), str(end_line), '1', '1',
                                  proc.output_file])
        logging.debug('Executing l2extract command: "%s"', l2extract_cmd)
        status = execute_command(l2extract_cmd)
        return status
    else:
        err_msg = 'Error! Geographical coordinates not specified for l2extract.'
        log_and_exit(err_msg)

def run_l2gen(proc):
    """
    Set up for and perform L2 processing.
    """
    if cfg_data.get_anc:
        getanc_prog = build_executable_path('getanc.py')
        getanc_cmd = ' '.join([getanc_prog, proc.input_file])
        logging.debug('running getanc command: ' + getanc_cmd)
        execute_command(getanc_cmd)
    l2gen_prog = os.path.join(proc.ocssw_bin, 'l2gen')
    if not os.path.exists(l2gen_prog):
        print ("Error!  Cannot find executable needed for {0}".\
              format(proc.rule_set.rules[proc.target_type].action))
    par_name = build_l2gen_par_file(proc.par_data, proc.input_file,
                                    proc.geo_file, proc.output_file)
    logging.debug('L2GEN_FILE=' + proc.output_file)

    args = 'par=' + par_name
    l2gen_cmd = ' '.join([l2gen_prog, args])
    if cfg_data.verbose or DEBUG:
        logging.debug('l2gen cmd: %s', l2gen_cmd)
    return execute_command(l2gen_cmd)

def run_l2gen_viirs(proc):
    """
    Set up VIIRS' l2gen processing.
    """
    file_names = []
    if tarfile.is_tarfile(proc.input_file):
        tar_obj = tarfile.TarFile(proc.input_file)
        file_names = tar_obj.getnames()
        tar_obj.extractall()
    elif MetaUtils.is_ascii_file(proc.input_file):
        with open(proc.input_file, 'rt') as in_file:
            file_names = in_file.readlines()
    elif re.match(r'^SVM\d\d_npp_d\d\d\d\d\d\d\d\_.*\.h5', proc.input_file):
        file_names = [proc.input_file]
    if len(file_names) > 0:
        for fname in file_names:
            if not re.match(r'^GMTCO_npp_d.*\.h5', fname) and \
                not re.match(r'^SVM\d\d_npp_d\d\d\d\d\d\d\d.*\.h5', fname):
                file_names.remove(fname)
        file_names.sort()
        if re.match(r'^GMTCO_npp_d.*\.h5', file_names[0]):
            geo_file = file_names[0]
            first_svm_file = file_names[1]
        elif proc.geo_file:
            first_svm_file = file_names[0]
            geo_file = proc.geo_file
        else:
            first_svm_file = file_names[0]
            geo_file = find_viirs_geo_file(proc, first_svm_file)
            if not geo_file:
                err_msg = 'Error! Unable to find geofile for {0}.'.\
                          format(first_svm_file)
                sys.exit(err_msg)
        new_proc = proc
        new_proc.input_file = first_svm_file
        new_proc.geo_file = geo_file
        run_l2gen(new_proc)

def run_l2mapgen(proc):
    """
    Runs the l2mapgen executable.
    """
    prog = os.path.join(proc.ocssw_bin, 'l2mapgen')
    args = 'ifile=' + proc.input_file
    for opt_name in proc.par_data:
        if not opt_name.lower() in FILE_USE_OPTS:
            args += ' ' + opt_name + '=' + proc.par_data[opt_name]
    args += ' ofile=' + proc.output_file
    cmd = ' '.join([prog, args])
    logging.debug('Executing: "%s"', cmd)
    status = execute_command(cmd)
    logging.debug("l2mapgen run complete with status " + str(status))
    if status == 110:
        # A return status of 110 indicates that there was insufficient data
        # to plot.  That status should be handled as a normal condition here.
        return 0
    return status

def run_l3bin(proc):
    """
    Set up and run the l3Bin program
    """
    prog = os.path.join(proc.ocssw_bin, 'l3bin')
    if not os.path.exists(prog):
        print ("Error!  Cannot find executable needed for {0}".\
              format(proc.rule_set.rules[proc.target_type].action))
    args = 'ifile=' + proc.input_file
    for key in proc.par_data:
        if not key.lower() in FILE_USE_OPTS:
            args += ' ' + key + '=' + proc.par_data[key]
    args = 'in=' + proc.input_file
    args += ' ' + "out=" + proc.output_file
    # for key in proc.par_data:
    #     args += ' ' + key + '=' + proc.par_data[key]
    cmd = ' '.join([prog, args])
    logging.debug('Executing l3bin command: "%s"', cmd)
    ret_val = execute_command(cmd)
    if ret_val != 0:
        if os.path.exists(proc.output_file):
            msg = '-I- The l3bin program returned a status value of {0}. Proceeding with processing, using the output l2 bin file {1}'.format(
                ret_val, proc.output_file)
            logging.info(msg)
            ret_val = 0
    else:
        msg = "-I- The l3bin program produced a bin file with no data. No further processing will be done."
        sys.exit(msg)
    return ret_val

def run_l3mapgen(proc):
    """
    Set up and run the l3mapgen program.
    """
    prog = os.path.join(proc.ocssw_bin, 'l3mapgen')
    if not os.path.exists(prog):
        print ("Error!  Cannot find executable needed for {0}".\
              format(proc.rule_set.rules[proc.target_type].action))
    args = 'ifile=' + proc.input_file
    for key in proc.par_data:
        if not key.lower() in FILE_USE_OPTS:
            args += ' ' + key + '=' + proc.par_data[key]
    args += ' ofile=' + proc.output_file
    cmd = ' '.join([prog, args])
    logging.debug('Executing l3mapgen command: "%s"', cmd)
    return execute_command(cmd)

def run_modis_geo(proc):
    """
    Sets up and runs the MODIS GEO script.
    """
    prog = build_executable_path('modis_GEO.py')
    # os.path.join(proc.ocssw_root, 'run', 'scripts', 'modis_GEO.py')
    args = proc.input_file +  ' --output=' + proc.output_file
    args += get_options(proc.par_data)
    cmd = ' '.join([prog, args])
    logging.debug("\nRunning: " + cmd)
    return execute_command(cmd)

def run_modis_l1a(proc):
    """
    Sets up and runs the MODIS L1A script.
    """
    prog = build_executable_path('modis_L1A.py')
    args = proc.input_file
    args += ' --output=' + proc.output_file
    args += get_options(proc.par_data)
    cmd = ' '.join([prog, args])
    logging.debug("\nRunning: " + cmd)
    return execute_command(cmd)

def run_modis_l1b(proc):
    """
    Runs the L1B script.
    """
    prog = build_executable_path('modis_L1B.py')
    args = ' -o ' + proc.output_file
    args += get_options(proc.par_data)
    # The following is no longer needed, but kept for reference.
#    args += ' --lutdir $OCSSWROOT/run/var/modisa/cal/EVAL --lutver=6.1.15.1z'
    args += ' ' + proc.input_file
    if not proc.geo_file is None:
        args += ' ' + proc.geo_file
    cmd = ' '.join([prog, args])
    logging.debug("\nRunning: " + cmd)
    return execute_command(cmd)

def run_nonbatch_processor(ndx, processors, file_set):
    """
    Run a processor which deals with single input files (or pairs of files in
    the case of MODIS L1B processing in which GEO files are also needed).
    """
    if isinstance(file_set, tuple):
        input_file = file_set[0]
        geo_file = file_set[1]
    else:
        input_file = file_set
        geo_file = None
    dfile = get_obpg_data_file_object(input_file)

    cl_opts = optparse.Values()
    if 'suite' in processors[ndx].par_data:
        cl_opts.suite = processors[ndx].par_data['suite']
    elif 'prod' in processors[ndx].par_data:
        cl_opts.suite = processors[ndx].par_data['prod']
    else:
        cl_opts.suite = None
    if 'resolution' in processors[ndx].par_data:
        cl_opts.resolution = processors[ndx].par_data['resolution']
    else:
        cl_opts.resolution = None
    if 'oformat' in processors[ndx].par_data:
        cl_opts.oformat = processors[ndx].par_data['oformat']
    else:
        cl_opts.oformat = None
    name_finder = name_finder_utils.get_level_finder([dfile],
                                                     processors[ndx].target_type,
                                                     cl_opts)
    output_file = os.path.join(processors[ndx].out_directory,
                               name_finder.get_next_level_name())
    if DEBUG:
        print ('in run_nonbatch_processor, output_file = ' + output_file)
    processors[ndx].input_file = input_file
    processors[ndx].output_file = output_file
    processors[ndx].geo_file = geo_file
    if 'keepfiles' in processors[ndx].par_data:
        if processors[ndx].par_data['keepfiles']:     # != 0:
            processors[ndx].keepfiles = True
    if (not os.path.exists(output_file)) or cfg_data.overwrite:
        if cfg_data.verbose:
            print ()
            print ('\nRunning ' + str(processors[ndx]))
            sys.stdout.flush()
        proc_status = processors[ndx].execute()

        if proc_status:
            output_file = None
            msg = "Error! Status {0} was returned during {1} {2} processing.".\
                  format(proc_status, processors[ndx].instrument,
                         processors[ndx].target_type)
            # log_and_exit(msg)
            logging.info(msg)
            # Todo: remove the failed file from future processing
    elif not cfg_data.use_existing:
        log_and_exit('Error! Target file {0} already exists.'.\
                     format(output_file))
    return output_file

def run_script(proc, script_name):
    """
    Build the command to run the processing script which is passed in.
    """
    prog = build_executable_path(script_name)
    args = ' ifile=' + proc.input_file
    args += ' ofile=' + proc.output_file
    args += get_options(proc.par_data)
    cmd = ' '.join([prog, args])
    logging.debug("\nRunning: " + cmd)
    return execute_command(cmd)

def run_smigen(proc):
    """
    Set up for and perform SMI (Standard Mapped Image) generation.
    """
    status = None
    prog = os.path.join(proc.ocssw_bin, 'smigen')
    if not os.path.exists(prog):
        print ("Error!  Cannot find executable needed for {0}".\
              format(proc.rule_set.rules[proc.target_type].action))
    if 'prod' in proc.par_data:
        args = 'ifile=' + proc.input_file + ' ofile=' + proc.output_file + \
               ' prod=' + proc.par_data['prod']
        cmd = ' '.join([prog, args])
        for key in proc.par_data:
            if (key != 'prod') and not (key.lower() in FILE_USE_OPTS):
                args += ' ' + key + '=' + proc.par_data[key]
        logging.debug('\nRunning smigen command: ' + cmd)
        status = execute_command(cmd)
    else:
        err_msg = 'Error! No product specified for smigen.'
        log_and_exit(err_msg)
    return status

def run_viirs_l1b(proc):
    logging.debug('In run_viirs_l1b')
    prog = build_executable_path('calibrate_viirs')
#     prog='/accounts/melliott/seadas/ocssw/bin/calibrate_viirs'

    args = ''.join(['ifile=', proc.input_file, ' l1bfile_mod=', proc.output_file])
    args += get_options(proc.par_data)
    # The following is no longer needed, but kept for reference.
#    args += ' --lutdir $OCSSWROOT/run/var/modisa/cal/EVAL --lutver=6.1.15.1z'
#     args += ' ' + proc.input_file
    if proc.geo_file:
        pass
#         args += ' geofile=' + proc.geo_file
    cmd = ' '.join([prog, args])
    logging.debug("\nRunning: " + cmd)
    return execute_command(cmd)

    return

def start_logging(time_stamp):
    """
    Opens log file(s) for debugging.
    """
    info_log_name = ''.join(['Processor_', time_stamp, '.log'])
    debug_log_name = ''.join(['multilevel_processor_debug_', time_stamp,
                              '.log'])
    info_log_path = os.path.join(cfg_data.output_dir, info_log_name)
    debug_log_path = os.path.join(cfg_data.output_dir, debug_log_name)
    mlp_logger = logging.getLogger()
    #mlp_logger.setLevel(logging.DEBUG)

    info_hndl = logging.FileHandler(info_log_path)
    info_hndl.setLevel(logging.INFO)
    mlp_logger.addHandler(info_hndl)

    if DEBUG:
        debug_hndl = logging.FileHandler(debug_log_path)
        debug_hndl.setLevel(logging.DEBUG)
        mlp_logger.addHandler(debug_hndl)
    logging.debug('Starting ' + os.path.basename(sys.argv[0]) + ' at ' +
                  datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

def uniqify_list(orig_list):
    """
    Returns a list with no duplicates.  Somewhat borrowed from:
      http://www.peterbe.com/plog/uniqifiers-benchmark (example f5)
    """
    uniqified_list = []
    seen_items = {}
    for item in orig_list:
        if item not in seen_items:
            seen_items[item] = 1
            uniqified_list.append(item)
    return uniqified_list

                  #########################################

DEBUG = False
#DEBUG = True

cfg_data = None
FILE_USE_OPTS = ['keepfiles', 'overwrite', 'use_existing']
SUFFIXES = {
    'geo': 'GEO',
    'l1brsgen': 'L1B_BRS',
    'l1aextract_seawifs': 'L1A.sub',
    'l1aextract_modis': 'L1A.sub',
    'l1mapgen': 'L1B_MAP',
    'l2bin': 'L3b',
    'l2brsgen': 'L2_BRS',
    'l2extract': 'L2.sub',
    'l2gen': 'L2',
    'l2mapgen': 'L2B_MAP',
    'l3bin': 'L3b',
    'l3mapgen': 'L3m',
    'level 1a': 'L1A',
    'level 1b': 'L1B_LAC',
    'smigen': 'SMI'
}
input_file_data = {}
#verbose = False

if os.environ['OCSSWROOT']:
    OCSSWROOT_DIR = os.environ['OCSSWROOT']
    logging.debug('OCSSWROOT -> %s', OCSSWROOT_DIR)
else:
    sys.exit('Error! Cannot find OCSSWROOT environment variable.')

if __name__ == "__main__":
    sys.exit(main())
