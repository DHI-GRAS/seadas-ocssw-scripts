#!/usr/bin/env python

"""
SeaDAS processing script (also known as the 'uber' processor).
"""

__author__ = 'melliott'

#import modis_processor

import ConfigParser
import datetime
import get_obpg_file_type
import logging
import optparse
import os
import uber_par_file_reader
import MetaUtils
import ProcUtils
import processor
import processing_rules
#import product
import re
import subprocess
import sys
import tarfile
import time
import traceback
import types

class ProcessorConfig:
    """
    Configuration data for the program which needs to be widely available.
    """
    SECS_PER_DAY = 86400
    def __init__(self, hidden_dir, ori_dir, verbose, overwrite, use_existing,
                 tar_name=None):
        if not(os.path.exists(hidden_dir)):
            try:
                os.mkdir(hidden_dir)
            except OSError:
                if sys.exc_info()[1].find('Permission denied:') != -1:
                    log_and_exit("Error!  Unable to create directory {0}".\
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
            cfg_parser = ConfigParser.SafeConfigParser()
            cfg_parser.read(cfg_path)
            try:
                self.max_file_age = ProcessorConfig.SECS_PER_DAY * \
                                    int(cfg_parser.get('main', 'par_file_age').\
                                    split(' ', 2)[0])
            except ConfigParser.NoSectionError, nse:
                print 'nse: ' + str(nse)
                print 'sys.exc_info(): '
                for msg in sys.exc_info():
                    print '  ' +  str(msg)
                log_and_exit('Error!  Configuration file has no "main" ' +
                             'section.')
            except ConfigParser.NoOptionError:
                log_and_exit('Error! The "main" section of the configuration ' +
                             'file does not specify a "par_file_age".')
        except ConfigParser.MissingSectionHeaderError:
            log_and_exit('Error! Bad configuration file, no section headers ' +
                         'found.')

    def _set_temp_dir(self):
        """
        Sets the value of the temporary directory.
        """
        if os.path.exists('/tmp') and os.path.isdir('/tmp') and \
           os.access('/tmp', os.W_OK):
            self.temp_dir = '/tmp'
        else:
            cwd = os.getcwd()
            if os.path.exists(cwd) and os.path.isdir(cwd) and \
               os.access(cwd, os.W_OK):
                self.temp_dir = cwd
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

def build_file_list_file(filename, file_list):
    """
    Create a file listing the names of the files to be processed.
    """
    with open(filename, 'wt') as file_list_file:
        for fname in file_list:
            file_list_file.write(fname + '\n')

def build_l2gen_par_file(par_contents, input_file, geo_file, output_file):
    """
    Build the parameter file for L2 processing.
    """
    dt_stamp = datetime.datetime.today()
    par_name = ''.join(['L2_', dt_stamp.strftime('%Y%m%d%H%M%S'), '.par'])
    par_path = os.path.join(cfg_data.hidden_dir, par_name)
    with open(par_path, 'wt') as par_file:
        par_file.write('# Automatically generated par file\n')
        par_file.write('ifile=' + input_file + '\n')
        if not geo_file is None:
            par_file.write('geofile=' + geo_file + '\n')
        par_file.write('ofile=' + output_file + '\n')
        for key in par_contents:
            if key != 'ifile' and key != 'geofile':
                par_file.write(key + '=' + par_contents[key] + '\n')
    return par_path

def build_general_rules():
    """
    Builds the general rules set.

    Rule format:
    target type (string),  sources (list of strings), batch processing flag (Boolean),
    action to take (function name)
    """
    rules_dict = {
        'level 1a': processing_rules.Rule('level 1a', ['level 0'], False,
                                          run_bottom_error),
        'l1brsgen': processing_rules.Rule('l1brsgen', ['l1'], False,
                                          run_l1brsgen),
        'l2brsgen': processing_rules.Rule('l2brsgen', ['l2gen'], False,
                                          run_l2brsgen),
        'l1mapgen': processing_rules.Rule('l1mapgen', ['l1'], False,
                                          run_l1mapgen),
        'l2mapgen': processing_rules.Rule('l2mapgen', ['l2gen'], False,
                                          run_l2mapgen),
        'level 1b': processing_rules.Rule('level 1b', ['level 1a', 'geo'],
                                          False, run_l1b),
        'l2gen': processing_rules.Rule('l2gen', ['level 1b'], False, run_l2gen),
        'l2extract': processing_rules.Rule('l2extract', ['l2gen'], False,
                                           run_l2extract),
        'l2bin': processing_rules.Rule('l2bin', ['l2gen'], True, run_l2bin),
        'l3bin': processing_rules.Rule('l3bin', ['l3bin'], True, run_l3bin),
#        'smigen': processing_rules.Rule('smigen', ['l3bin'], False, run_smigen)
        'smigen': processing_rules.Rule('smigen', ['l2bin'], False, run_smigen)
    }
    rules_order = ['level 1a', 'l1brsgen', 'l1mapgen', 'level 1b', 'l2gen',
                   'l2extract', 'l2brsgen', 'l2mapgen', 'l2bin', 'l3bin',
                   'smigen']
    rules = processing_rules.RuleSet('General rules', rules_dict, rules_order)
    return rules

def build_modis_rules():
    """
    Builds the MODIS rules set.
    """
    rules_dict =  {
        'level 0': processing_rules.Rule('level 0', ['nothing lower'], False,
                                          run_bottom_error),
        'level 1a': processing_rules.Rule('level 1a', ['level 0'], False,
                                          run_modis_l1a),
        'l1brsgen': processing_rules.Rule('l1brsgen', ['l1'], False,
                                          run_l1brsgen),
        'l1mapgen': processing_rules.Rule('l1mapgen', ['l1'], False,
                                          run_l1mapgen),
        'geo': processing_rules.Rule('geo', ['level 1a'], False, run_modis_geo),
        'l1aextract_modis': processing_rules.Rule('l1aextract_modis',
                                                  ['level 1a', 'geo'], False,
                                                  run_l1aextract_modis),
        'level 1b': processing_rules.Rule('level 1b', ['level 1a', 'geo'],
                                          False, run_modis_l1b),
        'l2gen': processing_rules.Rule('l2gen', ['level 1b','geo'], False,
                                       run_l2gen),
        'l2extract': processing_rules.Rule('l2extract', ['l2gen'], False,
                                           run_l2extract),
        'l2brsgen': processing_rules.Rule('l2brsgen', ['l2gen'], False,
                                          run_l2brsgen),
        'l2mapgen': processing_rules.Rule('l2mapgen', ['l2gen'], False,
                                          run_l2mapgen),
        'l2bin': processing_rules.Rule('l2bin', ['l2gen'], True, run_l2bin),
        'l3bin': processing_rules.Rule('l3bin', ['l3bin'], True, run_l3bin),
#        'smigen': processing_rules.Rule('smigen', ['l3bin'], False, run_smigen)
        'smigen': processing_rules.Rule('smigen', ['l2bin'], False, run_smigen)
    }
    rules_order = ['level 0', 'level 1a', 'l1brsgen', 'l1mapgen', 'geo',
                   'l1aextract_modis', 'level 1b', 'l2gen', 'l2extract',
                   'l2bin', 'l2brsgen', 'l2mapgen', 'l3bin', 'smigen']
    rules = processing_rules.RuleSet("MODIS Rules", rules_dict, rules_order)
    return rules

def build_seawifs_rules():
    """
    Builds the general rules set.
    """
    rules_dict =  {
        'level 1a': processing_rules.Rule('level 1a', ['level 0'], False,
                                          run_bottom_error),
        'l1aextract_seawifs': processing_rules.Rule('l1aextract_seawifs',
                                                    ['level 1a'], False,
                                                    run_l1aextract_seawifs),
        'l1brsgen': processing_rules.Rule('l1brsgen', ['l1'], False,
                                          run_l1brsgen),
        'l1mapgen': processing_rules.Rule('l1mapgen', ['l1'], False,
                                          run_l1mapgen),
        'level 1b': processing_rules.Rule('level 1b', ['level 1a'], False,
                                          run_l1b),
        'l2gen': processing_rules.Rule('l2gen', ['level 1b'], False, run_l2gen),
        'l2extract': processing_rules.Rule('l2extract', ['l2gen'], False,
                                           run_l2extract),
        'l2brsgen': processing_rules.Rule('l2brsgen', ['l2gen'], False,
                                          run_l2brsgen),
        'l2mapgen': processing_rules.Rule('l2mapgen', ['l2gen'], False,
                                          run_l2mapgen),
        'l2bin': processing_rules.Rule('l2bin', ['l2gen'], True, run_l2bin),
        'l3bin': processing_rules.Rule('l3bin', ['l3bin'], True, run_l3bin),
#        'smigen': processing_rules.Rule('smigen', ['l3bin'], False, run_smigen)
        'smigen': processing_rules.Rule('smigen', ['l2bin'], False, run_smigen)
    }
    rules_order = ['level 1a', 'l1brsgen', 'l1mapgen', 'level 1b', 'l2gen',
                   'l2extract', 'l2brsgen', 'l2mapgen', 'l2bin', 'l3bin',
                   'smigen']
    rules = processing_rules.RuleSet("SeaWiFS Rules", rules_dict, rules_order)
    return rules

def build_rules():
    """
    Build the processing rules.
    """
    rules = dict(general=build_general_rules,
                 modis=build_modis_rules,
                 seawifs=build_seawifs_rules)
    return rules

def clean_files(delete_list):
    """
    Delete unwanted files created during processing.
    """
    if cfg_data.verbose:
        print "Cleaning up files"
    files_deleted = 0
    # Delete any files in the delete list.  This contain "interemediate" files
    # which were needed to complete processing, but which weren't explicitly
    # requested as output targets.
    for filepath in delete_list:
        if cfg_data.verbose:
            print "Deleting {0}".format(filepath)
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
                print "Deleting {0}".format(par_path)
            os.remove(par_path)
            files_deleted += 1
    if cfg_data.verbose:
        if not files_deleted:
            print "No files were found for deletion."
        elif files_deleted == 1:
            print "One file was deleted."
        else:
            print "A total of {0} files were deleted.".format(files_deleted)

def do_processing(rules_sets, par_file):
    """
    Perform the processing for each step (element of processor_list) needed.
    """
    global input_file_data
    #todo:  Break this up into smaller parts!
    files_to_keep = []
    files_to_delete = []
    file_use_opts = ['keepfiles', 'overwrite', 'use_existing']
    (par_contents, input_files_list) = get_par_file_contents(par_file,
                                                             file_use_opts)
    if par_contents['main']:
        # Avoid overwriting file options that are already turned on in cfg_data
        # (from command line input).
        keepfiles, use_existing, overwrite = get_file_handling_opts(par_contents)
        if keepfiles:
            cfg_data.keepfiles = True
        if use_existing:
            cfg_data.use_existing = True
        if overwrite:
            cfg_data.overwrite = True
        if 'use_nrt_anc' in par_contents['main'] and \
           int(par_contents['main']['use_nrt_anc']) == 0:
            cfg_data.get_anc = False
    logging.debug('cfg_data.overwrite: ' + str(cfg_data.overwrite))
    logging.debug('cfg_data.use_existing: ' + str(cfg_data.use_existing))
    logging.debug('cfg_data.keepfiles: ' + str(cfg_data.keepfiles))
    if cfg_data.overwrite and cfg_data.use_existing:
        err_msg = 'Error!  Incompatible options overwrite and use_existing ' +\
                  'were found in {0}.'.format(par_file)
        log_and_exit(err_msg)
    if len(input_files_list) == 1:
        if MetaUtils.is_ascii_file(input_files_list[0]):
            input_files_list = read_file_list_file(input_files_list[0])
    input_file_data = get_input_files_type_data(input_files_list)
    logging.debug("input_file_data: " + str(input_file_data))
    first_file_key = input_file_data.keys()[0]
    logging.debug("first_file_key: " + first_file_key)
    instrument = input_file_data[first_file_key][1].split()[0]
    logging.debug("instrument: " + instrument)
    if instrument in rules_sets:
        rules = rules_sets[instrument]()
    else:
        rules = rules_sets['general']()

    source_files = get_source_files(input_file_data)
    lowest_source_level = get_lowest_source_level(source_files)
    logging.debug("lowest_source_level: " + str(lowest_source_level))
    processors = get_processors(cfg_data, instrument, par_contents, rules,
                                lowest_source_level)
    logging.debug("processors: " + str(processors))
    if cfg_data.tar_filename:
        tar_file = tarfile.open(cfg_data.tar_filename, 'w')
    try:
        #todo: can probably make the loop work with 'for proc in processors:'
        for ndx, proc in enumerate(processors):
            proc_src_types = processors[ndx].rule_set.rules[processors[ndx].target_type].src_file_types
            if proc_src_types[0] in source_files:
                src_key = proc_src_types[0]
            else:
                src_key = None
                for cand_proc in reversed(processors[:ndx]):
                    if suffixes[cand_proc.target_type] == \
                       processors[ndx].rule_set.rules[processors[ndx].target_type].src_file_types[0]:
                        if cand_proc.target_type in source_files:
                            src_key = cand_proc.target_type
                            break
                if src_key is None:
                    err_msg = 'Error! Unable to find source files for {0}.'.\
                              format(processors[ndx].target_type)
                    log_and_exit(err_msg)
            logging.debug('proc_src_types:')
            logging.debug('\n  '.join([pst for pst in proc_src_types]))
            if proc.requires_batch_processing():
                logging.debug('Performing batch processing for ' + str(proc))
                output_file = run_batch_processor(ndx, processors,
                                                  source_files[src_key])
                if processors[ndx].target_type in source_files:
                    if not output_file in source_files[processors[ndx].target_type]:
                        source_files[processors[ndx].target_type].\
                            append(output_file)
                else:
                    source_files[processors[ndx].target_type] = [output_file]
            else:
                logging.debug('Performing nonbatch processing for ' + str(proc))
                if len(proc_src_types) == 1:
                    try:
                        src_file_sets = source_files[src_key]
                    except Exception:
                        print "Exception encountered: "
                        e_info = sys.exc_info()
                        err_msg = ''
                        for info in e_info:
                            err_msg += "  " + str(info)
                        log_and_exit(99)
                elif len(proc_src_types) == 2:
                    src_file_sets = zip(source_files[proc_src_types[0]],
                                        source_files[proc_src_types[1]])
                else:
                    err_msg = 'Error!  Encountered too many source file types.'
                    log_and_exit(err_msg)
                for file_set in src_file_sets:
                    output_file = run_nonbatch_processor(ndx, processors,
                                                         input_file_data,
                                                         file_set)
                    if processors[ndx].target_type in source_files:
                        if not output_file in source_files[processors[ndx].target_type]:
                            source_files[processors[ndx].target_type].\
                                append(output_file)
                    else:
                        source_files[processors[ndx].target_type] = [output_file]
            if cfg_data.keepfiles or processors[ndx].keepfiles:
                files_to_keep.append(output_file)
                if cfg_data.tar_filename:
                    tar_file.add(output_file)
                logging.debug('Added ' + output_file + ' to tar file list')
            #todo: add "target" files to files_to_keep and other files to files_to_delete, as appropriate
    except Exception:
        exc_parts = [str(l) for l in sys.exc_info()]
        err_type_parts = str(exc_parts[0]).strip().split('.')
        err_type = err_type_parts[-1].strip("'>")
        tb_line = traceback.format_exc().splitlines()[-3]
        line_num = tb_line.split(',')[1]
        err_msg = 'Error!  The {0} program encountered an unrecoverable ' + \
                  '{1}, {2}, at {3}!'.format(os.path.basename(sys.argv[0]), \
                                       err_type, exc_parts[1], line_num.strip())
        log_and_exit(err_msg)
    finally:
        if cfg_data.tar_filename:
            tar_file.close()
            logging.debug('closed tar file')
        # Since the clean_files function will delete hidden files as well as the
        # files in files_to_delete, it should be called regardless of whether
        # files_to_delete contains anything.
        clean_files(files_to_delete)
    if cfg_data.verbose:
        print "Processing complete."
    logging.debug("Processing complete.")
    return

def execute_command(command):
    """
    Execute what is contained in command and then output the results to log
    files and the console, as appropriate.
    """
    if DEBUG:
        print "Entering execute_command, cfg_data.verbose =", cfg_data.verbose

    subproc = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    std_out, err_out = subproc.communicate()
    status = subproc.returncode
    logging.info(std_out)
    logging.info(err_out)
    if cfg_data.verbose:
        print std_out
    return status

def extract_par_section(par_contents, section):
    """
    Returns a single section (e.g. L1a, GEO, L1B, L2, etc.) from the "par" file.
    """
    sect_dict = {}
    for key in par_contents[section].keys():
        sect_dict[key] = par_contents[section][key]
    return sect_dict

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
        opt_found = is_option_value_true(opt_str)
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
    logging.debug('Executing lonlat2pixline command: {0}'.format(lonlat_cmd))
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
    Get a Python Date from a recognized file name's year and day of year.
    """
    base_filename = os.path.basename(filename)
    if re.match("[ACMOQSTV]\d\d\d\d\d\d\d.*", base_filename):
        year = int(base_filename[1:5])
        doy = int(base_filename[5:8])
    elif re.match("\d\d\d\d\d\d\d.*", base_filename):
        # Some Aquarius
        year = int(base_filename[0:4])
        doy = int(base_filename[4:7])
    elif re.match('\w*_npp_d\d\d\d\d\d\d\d_.*', base_filename):
        # NPP
        prefix_removed_name = re.sub('\w*_npp_d', '', base_filename)
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
    Get input files found in the uber par file's ifile line, an file list file,
    or both.  Ensure that the list contains no duplicates.
    """
    from_ifiles = []
    from_infilelist = []
    if 'ifile' in par_data['main']:
        inp_file_str = par_data['main']['ifile'].split('#', 2)[0]
        cleaned_str = re.sub('[\t,:\[\]()"\']', ' ', inp_file_str)
        from_ifiles = cleaned_str.split()
    if 'infilelist' in par_data['main']:
        infilelist_name = par_data['main']['infilelist']
        if os.path.exists(infilelist_name):
            if os.path.isfile(infilelist_name) and \
              os.access(infilelist_name, os.R_OK):
                with open(infilelist_name, 'rt') as in_file_list_file:
                    inp_lines = in_file_list_file.readlines()
                from_infilelist = [fn.rstrip() for fn in inp_lines
                                   if not re.match('^\s*#', fn)]
    inp_file_list = uniqify_list(from_ifiles + from_infilelist)
    return inp_file_list

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
        'level 2': 'l2gen',
        'level 3 binned': 'l3bin',
        'level 3 smi': 'smigen'
    }
    input_file_type_data = {}
    for inp_file in input_files_list:
        if os.path.dirname((inp_file)) == '':
            inp_path = os.path.join(os.getcwd(), inp_file)
        else:
            inp_path = inp_file
        file_typer = get_obpg_file_type.ObpgFileTyper(inp_file)
        file_type, file_instr = file_typer.get_file_type()
        file_type = converter[file_type.lower()]
        input_file_type_data[inp_file] = (file_type, file_instr.lower())
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
            new_proc = processor.Processor('', rules, prod,
                                           {}, cfg_data.hidden_dir )
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
        if not isinstance(candidate_progs, types.NoneType):
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
        return source_files.keys()[0]
    else:
        lowest = source_files.keys()[0]
        for key in source_files.keys()[1:]:
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
        elif not key == 'keepfiles':
            options += ' ' + key + '=' + par_data[key]
    return options

def get_output_name(input_name, suffix):
    """
    Determine the output name for a program to be run.
    """
    # todo:  Delete, once this isn't needed (i.e. all the calls to it are eliminated because the output file is pulled from the processor)
    (dirname, basename) = os.path.split(input_name)
    basename_parts = basename.rsplit('.', 2)
    output_name = os.path.join(dirname, basename_parts[0] + '.' + suffix)
    return output_name

def get_output_name2(input_name, input_files, suffix):
    """
    Determine the output name for a program to be run.
    """
    # Todo: refactor to be get_output_name and delete the other get_output_name
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
                if re.match('MOD00.P\d\d\d\d\d\d\d\.\d\d\d\d', input_name):
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
        'geo' : 'geo', 'modis_GEO.py': 'geo',
        'level 1b' : 'level 1b', 'l1b' : 'level 1b', 'l1bgen' : 'level 1b',
        'modis_L1B.py': 'level 1b',
        'l2gen' : 'l2gen',
        'l2bin' : 'l2bin',
        'l2brsgen' : 'l2brsgen',
        'l2extract' : 'l2extract',
        'l2mapgen' : 'l2mapgen',
        'l3bin' : 'l3bin',
        'smigen' : 'smigen',
        'main' : 'main'
        #        'level 3' : 'level 3', 'l3' : 'level 3'
    }
    if cfg_data.verbose:
        print "Processing %s" % par_file
    par_reader = uber_par_file_reader.ParReader(par_file,
                                                acceptable_single_keys,
                                                acceptable_par_keys)
    par_contents = par_reader.read_par_file()
    ori_keys = par_contents.keys()
    for key in ori_keys:
        if key in acceptable_par_keys:
            if key != acceptable_par_keys[key]:
                par_contents[acceptable_par_keys[key]] = par_contents[key]
                del par_contents[key]
        else:
            acc_key_str = ', '.join(acceptable_par_keys.keys())
            err_msg = """Error!  Parameter file {0} contains a section titled "{1}", which is not a recognized program.
The recognized programs are: {2}""".format(par_file, key, acc_key_str)

            log_and_exit(err_msg)
    if 'main' in par_contents:
#        if 'ocproc_sensor' in par_contents['main']:
#            instrument = par_contents['main']['ocproc_sensor'].lower()
#        else:
#            instrument = None
        input_files_list = get_input_files(par_contents)
        if input_files_list is None:
            err_msg = 'Error!  No input files specified in {0}'.format(par_file)
            log_and_exit(err_msg)
    else:
        err_msg = 'Error! Could not find section "main" in {0}'.format(par_file)
        log_and_exit(err_msg)
#    return par_contents, instrument, input_files_list
    return par_contents, input_files_list

def get_processors(cfg_data, instrument, par_contents, rules,
                   lowest_source_level):
    """
    Determine the processors which are needed.
    """
    processors = []
    for key in par_contents.keys():
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

def get_source_products_types(targt_prod, ruleset):
    """
    Return the list of source product typess needed to produce the final product.
    """
    src_prod_names = [targt_prod]
    targt_pos = ruleset.order.index(targt_prod)
    new_prod_names = []
    for pos in xrange(targt_pos, 1, -1):
        for prod_name in src_prod_names:
            if ruleset.rules[ruleset.order[pos]].target_type == prod_name:
                for src_typ in ruleset.rules[ruleset.order[pos]].src_file_types:
                    new_prod_names.append(src_typ)
    src_prod_names += new_prod_names
    return src_prod_names

def is_option_value_true(opt_val_str):
    """
    Returns True if opt_val_str is one the various possible values that OBPG
    programs accept as true.  
    """
    TRUE_VALUES = ['1', 'ON', 'on', 'TRUE', 'true', 'YES', 'yes']
    opt_val = False
    if opt_val_str in TRUE_VALUES:
        opt_val = True
    return opt_val

def log_and_exit(error_msg):
    """
    Record error_msg in the debug log, then exit with error_msg going to stderr
    and an exit code of 1; see http://docs.python.org/library/sys.html#log_and_exit.
    """
    logging.debug(error_msg)
    sys.exit(error_msg)

def main():
    """
    main processing function.
    """
    global cfg_data
    global DEBUG
    rules_sets = build_rules()
    ver_msg = ' '.join(['%prog', __version__])
    use_msg = """
    Usage: %prog [options] parameter_file

    The parameter_file is similar to, but not exactly like, parameter files for
    OCSSW processing programs:
     - It has sections separated by headers which are denoted by "[" and "]".
    The section named "main" is required.  Its allowed options are:
        ifile - Required entry naming the input file(s) to be processed.
        use_nrt_anc - use near real time ancillary data
        keepfiles - keep all the data files generated
        overwrite - overwrite any data files which already exist
        use_existing  - use any data files which already exist

        Simultaneous use of both the overwrite and use_existing options is
        not permitted.

    The names for other sections are the programs for which that section's
    entries are to be applied.  Intermediate sections which are required for the
    final level of processing do not need to be defined if their default options
    are acceptable.  A section can be empty.  The final level of processing
    must have a section header, even if no entries appear within that section.
     - Entries within a section appear as key=value.  Comma separated lists of
    values can be used when appropriate.
     - Comments are marked by "#"; anything appearing on a line after that
    character is ignored.  A line beginning with a "#" is completely ignored.

    Example:

    # Sample par file for %prog.
    [main]
    ifile=2010345034027.L1A_LAC
    [l2gen]
    l2prod=chlor_a
    # final processing level
    """
    cl_parser = optparse.OptionParser(usage=use_msg, version=ver_msg)
    (options, args) = process_command_line(cl_parser)

    if len(args) < 1:
        print "\nError! No file specified for processing.\n"
        cl_parser.print_help()
    else:
        if options.debug:
            # Don't just set DEBUG = options.debug, as that would override the
            # in-program setting.
            DEBUG = True
        if options.tar_file:
            if os.path.exists(options.tar_file):
                err_msg = 'Error! The tar file, {0}, already exists.'.\
                          format(options.tar_file)
                log_and_exit(err_msg)
        cfg_data = ProcessorConfig('.seadas_data', os.getcwd(), options.verbose,
                                   options.overwrite, options.use_existing,
                                   options.tar_file)
        if not(os.access(cfg_data.hidden_dir, os.R_OK) ):
            err_msg = "Error!  The working directory is not readable!"
            log_and_exit(err_msg)
        if os.path.exists(args[0]):
            log_timestamp = datetime.datetime.today().strftime('%Y%m%d%H%M%S')
            start_logging(log_timestamp)
            try:
                do_processing(rules_sets, args[0])
            except Exception:
                exc_parts = [str(l) for l in sys.exc_info()]
                err_type_parts = str(exc_parts[0]).strip().split('.')
                err_type = err_type_parts[-1].strip("'>")
                tb_line = traceback.format_exc().splitlines()[-3]
                line_num = tb_line.split(',')[1]
                err_msg = 'Error!  The {0} program encountered an unrecoverable {1}, {2}, at {3}!'.format(os.path.basename(sys.argv[0]), err_type, exc_parts[1], line_num.strip())
                log_and_exit(err_msg)
        logging.shutdown()
    return 0

def process_command_line(cl_parser):
    """
    Get arguments and options from the calling command line.
    To be consistent with other OBPG programs, an underscore ('_') is used for
    multiword options, instead of a dash ('-').
    """
    cl_parser.add_option('-v', '--verbose',
                      action='store_true', dest='verbose', default=False,
                      help='print status messages to stdout')
    cl_parser.add_option('-k', '--keepfiles', action='store_true',
                         dest='keepfiles', default=False,
                         help='keep files created during processing')
    cl_parser.add_option('--overwrite', action='store_true', dest='overwrite',
                         default=False,
                         help='overwrite files which already exist (default = stop processing if file already exists)')
    cl_parser.add_option('--use_existing', action='store_true',
                         dest='use_existing', default=False,
                         help='use files which already exist (default = stop processing if file already exists)')
    cl_parser.add_option('--debug', action='store_true', dest='debug',
                         default=False, help=optparse.SUPPRESS_HELP)
    cl_parser.add_option('-t', '--tar', type=str, dest='tar_file',
                         help=optparse.SUPPRESS_HELP)

    (options, args) = cl_parser.parse_args()
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
        err_msg = 'Error!  File {0} specified the following input files ' + \
                  'which could not be located:\n   {1}'.\
                  format(flf_name, ', '.join([bl for bl in bad_lines]))
        log_and_exit(err_msg)
    return files_list

#def run_batch_processor(ndx, processors, input_file_type_data, file_set):
def run_batch_processor(ndx, processors, file_set):
    """
    Run a processor, e.g. l2bin, which processes batches of files.
    """
    logging.debug('in run_batch_processor, ndx = {0}'.format(ndx))
    timestamp = time.strftime('%Y%m%d_%H%M%S', time.gmtime(time.time()))
    file_list_name = cfg_data.hidden_dir + os.sep + 'files_' + \
                     processors[ndx].target_type + '_' + timestamp + '.lis'
    with open(file_list_name, 'wt') as file_list:
        for fname in file_set:
            file_list.write(fname + '\n')
    suffix_key = processors[ndx].rule_set.rules[processors[ndx].target_type].target_type
    output_file = get_batch_output_name(file_set, suffixes[suffix_key])
    processors[ndx].input_file = file_list_name
    processors[ndx].output_file = output_file
    processors[ndx].execute()
    return output_file

def run_bottom_error(proc):
    """
    Exits with an error message when there is an attempt to process a source
    file at the lowest level of a rule chain.
    """
    err_msg = 'Error!  Attempting to create a product for which no creation ' +\
              'program is known.'
    log_and_exit(err_msg)

def run_executable(proc):
    """
    Sets up and runs an executable program.
    """
    #todo: replace l1bgen with the appropriate proc.whatever
    prog = os.path.join(proc.ocssw_bin, 'l1bgen')
    args = 'ifile=' + proc.input_file + ' '
    args += 'ofile=' + proc.output_file + ' '
    if not proc.geo_file is None:
        args += proc.geo_file + ' '
    args += get_options(proc.par_data)
    cmd = ' '.join([prog, args])
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
            err_msg = "Error! Cannot compute coordinates for l1aextract_modis."
            log_and_exit(err_msg)
        l1aextract_prog = os.path.join(proc.ocssw_bin, 'l1aextract_modis')
        l1aextract_cmd = ' '.join([l1aextract_prog, proc.input_file,
                                   str(start_pixel), str(end_pixel),
                                   str(start_line), str(end_line),
                                   proc.output_file])
        logging.debug('Executing l1aextract_modis command: {0}'.\
                      format(l1aextract_cmd))
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
        logging.debug('Executing l1aextract_seawifs command: {0}'.\
                      format(l1aextract_cmd))
        status = execute_command(l1aextract_cmd)
        return status

def run_l1b(proc):
    """
    Runs the l1bgen executable.
    """
    return run_executable(proc)

def run_l1brsgen(proc):
    """
    Runs the l1brsgen executable.
    """
    l1brs_suffixes = {'0':'L1_BRS', '1':'L1_BRS', '2':'ppm',
                      '3':'flt', '4':'png'}
    prog = os.path.join(proc.ocssw_bin, 'l1brsgen')
    opts = get_options(proc.par_data)
    if proc.par_data['outmode']:
        suffix = l1brs_suffixes[proc.par_data['outmode']]
    else:
        suffix = l1brs_suffixes['0']
    output_name = get_output_name(proc.par_data['ifile'], suffix)
    cmd = ' '.join([prog, opts, ' ofile=' + output_name])
    logging.debug('Executing: %s' % cmd)
    status = execute_command(cmd)
    return status

def run_l1mapgen(proc):
    """
    Runs the l1mapgen executable, handling the range of successful return
    values.
    """
    # Instead of a 0 for a successful exit code, the l1mapgen program returns
    # the percentage of pixels mapped , so the range of possible successful
    # values must be accepted.
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
    logging.debug('Executing: {0}'.format(cmd))
    status = execute_command(cmd)
    logging.debug("l1mapgen run compleat!  returned value: %d" % status)
    if (status >= acceptable_min) and (status <= acceptable_max):
        return 0
    else:
        return status

def run_l2bin(proc):
    """
    Set up for and perform L2 binning.
    """
    prog = os.path.join(proc.ocssw_bin, 'l2bin')
    if not os.path.exists(prog):
        print "Error!  Cannot find executable needed for {0}".\
              format(proc.rule_set.rules[proc.target_type].action)
    args = 'infile=' + proc.input_file
    args += ' ofile=' + proc.output_file
    cmd = ' '.join([prog, args])
    logging.debug('Running l2bin cmd: ' + cmd)
    if cfg_data.verbose:
        print 'l2bin cmd: ' + cmd
    return execute_command(cmd)

def run_l2brsgen(proc):
    """
    Runs the l1brsgen executable.
    """
    l2brs_suffixes = {'0': 'L2_BRS', '1': 'ppm', '2': 'png'}
    logging.debug("In run_l2brsgen")
    prog = os.path.join(proc.ocssw_bin, 'l2brsgen')
    opts = get_options(proc.par_data)
    if proc.par_data['outmode']:
        suffix = l2brs_suffixes[proc.par_data['outmode']]
    else:
        suffix = l2brs_suffixes['0']
    output_name = get_output_name(proc.input_file, suffix)
    cmd = ' '.join([prog, opts, 'ifile='+proc.input_file,
                   'ofile=' + output_name])
    logging.debug('Executing: {0}'.format(cmd))
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
            err_msg = "Error! Could not compute coordinates for l2extract."
            log_and_exit(err_msg)
        l2extract_prog = os.path.join(proc.ocssw_bin, 'l2extract')
        l2extract_cmd = ' '.join([l2extract_prog, proc.input_file,
                                  str(start_pixel), str(end_pixel),
                                  str(start_line), str(end_line), '1', '1',
                                  proc.output_file])
        logging.debug('Executing l2extract command: {0}'.format(l2extract_cmd))
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
        getanc_prog = os.path.join(proc.ocssw_root, 'run/scripts',
                                    'getanc.py')
        getanc_cmd = ' '.join([getanc_prog, proc.input_file])
        logging.debug('running getanc command: ' + getanc_cmd)
        execute_command(getanc_cmd)
    l2gen_prog = os.path.join(proc.ocssw_bin, 'l2gen')
    if not os.path.exists(l2gen_prog):
        print "Error!  Cannot find executable needed for {0}".\
              format(proc.rule_set.rules[proc.target_type].action)
    par_name = build_l2gen_par_file(proc.par_data, proc.input_file,
                                    proc.geo_file, proc.output_file)
    args = 'par=' + par_name
    l2gen_cmd = ' '.join([l2gen_prog, args])
    if cfg_data.verbose or DEBUG:
        logging.debug('l2gen cmd: ' + l2gen_cmd)
    return execute_command(l2gen_cmd)

def run_l2mapgen(proc):
    """
    Runs the l2mapgen executable.
    """
    prog = os.path.join(proc.ocssw_bin, 'l2mapgen')
    args = 'ifile='+proc.input_file
    for key in proc.par_data:
        args += ' ' + key + '=' + proc.par_data[key]
    if 'outmode' in proc.par_data:
        if proc.par_data['outmode'].upper() in ['PPM', 'PGM', 'PNG', 'TIFF']:
            ext = proc.par_data['outmode']
        else:
            err_msg = 'Error!  Unknown l2mapgen outmode {0}.'.\
                      format(proc.par_data['outmode'])
            log_and_exit(err_msg)
    else:
        ext = 'PGM'
    redirect_part = '> ' + os.path.splitext(proc.output_file)[0] + '.' + ext
    cmd = ' '.join([prog, args, redirect_part])
    logging.debug('Executing: {0}'.format(cmd))
    status = execute_command(cmd)
    logging.debug("l2mapgen run complete with status " + str(status))
    if status == 110:
        # A return status of 110 indicates that there was insufficient data to
        # plot.  We want ot handle this as a normal condition here.
        return 0
    else:
        return status

def run_l3bin(proc):
    """
    Set up and run the l3Bin program
    """
    prog = os.path.join(proc.ocssw_bin, 'l3bin')
    if not os.path.exists(prog):
        print "Error!  Cannot find executable needed for {0}".\
              format(proc.rule_set.rules[proc.target_type].action)
    args = 'in=' + proc.input_file
    args += ' ' + "out=" + proc.output_file
    for key in proc.par_data:
        args += ' ' + key + '=' + proc.par_data[key]
    cmd = ' '.join([prog, args])
    logging.debug('Executing l3bin command: "{0}"'.format(cmd))
    return execute_command(cmd)

def run_modis_geo(proc):
    """
    Sets up and runs the MODIS GEO script.
    """
    prog = os.path.join(proc.ocssw_root, 'run', 'scripts', 'modis_GEO.py')
    args = proc.input_file +  ' --output=' + proc.output_file
    args += get_options(proc.par_data)
    cmd = ' '.join([prog, args])
    logging.debug("\nRunning: " + cmd)
    return execute_command(cmd)

def run_modis_l1a(proc):
    """
    Sets up and runs the MODIS L1A script.
    """
    prog = os.path.join(proc.ocssw_root, 'run', 'scripts', 'modis_L1A.py')
    args = proc.input_file
    args +=  ' --output=' + proc.output_file
    args += get_options(proc.par_data)
    cmd = ' '.join([prog, args])
    logging.debug("\nRunning: " + cmd)
    return execute_command(cmd)

def run_modis_l1b(proc):
    """
    Runs the L1B script.
    """
    prog = os.path.join(proc.ocssw_root, 'run', 'scripts', 'modis_L1B.py')
    args = ' -o ' + proc.output_file
    args += get_options(proc.par_data)
    # No following is longer needed, but kept for reference.
#    args += ' --lutdir $OCSSWROOT/run/var/modisa/cal/EVAL --lutver=6.1.15.1z'
    args += ' ' + proc.input_file
    if not proc.geo_file is None:
        args += ' ' + proc.geo_file
    cmd = ' '.join([prog, args])
    logging.debug("\nRunning: " + cmd)
    return execute_command(cmd)

def run_nonbatch_processor(ndx, processors, input_file_type_data, file_set):
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
    suf_key = processors[ndx].rule_set.rules[processors[ndx].target_type].target_type
    output_file = get_output_name2(input_file, input_file_type_data,
                                   suffixes[suf_key])
    processors[ndx].input_file = input_file
    processors[ndx].output_file = output_file
    processors[ndx].geo_file = geo_file
    if 'keepfiles' in processors[ndx].par_data:
        if processors[ndx].par_data['keepfiles']:     # != 0:
            processors[ndx].keepfiles = True
    if (not os.path.exists(output_file)) or cfg_data.overwrite:
        if cfg_data.verbose:
            print
            print '\nRunning ' + str(processors[ndx])
        proc_status = processors[ndx].execute()
        if proc_status:
            msg = "Error! Status {0} was returned during {1} {2} processing.".\
                  format(proc_status, processors[ndx].instrument,
                         processors[ndx].target_type)
            log_and_exit(msg)
    elif not cfg_data.use_existing:
        log_and_exit('Error! Target file {0} already exists.'.\
                     format(output_file))
    return output_file

def run_script(proc, script_name):
    """
    Build the command to run the processing script which is passed in.
    """
    prog = os.path.join(proc.ocssw_root, 'run', 'scripts', script_name)
    args = ' ifile=' + proc.input_file
    args += ' ofile=' + proc.output_file
    args += get_options(proc.par_data)
    cmd = ' '.join([prog, args])
    logging.debug("\nRunning: " + cmd)
    return execute_command(cmd)

def run_smigen(proc):
    """
    Set up for and perform L3 SMI (Standard Mapped Image) generation.
    """
    prog = os.path.join(proc.ocssw_bin, 'smigen')
    if not os.path.exists(prog):
        print "Error!  Cannot find executable needed for {0}".\
              format(proc.rule_set.rules[proc.target_type].action)
    if 'prod' in proc.par_data:
        args = 'ifile=' + proc.input_file + ' ofile=' + proc.output_file + \
               ' prod=' + proc.par_data['prod']
        cmd = ' '.join([prog, args])
        for key in proc.par_data:
            if key != 'prod':
                args += ' ' + key + '=' + proc.par_data[key]
        logging.debug('\nRunning smigen command: ' + cmd)
        status = execute_command(cmd)
    else:
        err_msg = 'Error! No product specified for smigen.'
        log_and_exit(err_msg)
    return status

def start_logging(time_stamp):
    """
    Opens log file(s) for debugging.
    """
    info_log_name = ''.join(['Processor_', time_stamp, '.log'])
    debug_log_name = ''.join(['seadas_processor_debug_', time_stamp, '.log'])
    seadas_logger = logging.getLogger()
    seadas_logger.setLevel(logging.DEBUG)

    info_hndl = logging.FileHandler(info_log_name)
    info_hndl.setLevel(logging.INFO)
    seadas_logger.addHandler(info_hndl)

    if DEBUG:
        debug_hndl = logging.FileHandler(debug_log_name)
        debug_hndl.setLevel(logging.DEBUG)
        seadas_logger.addHandler(debug_hndl)
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
suffixes = {
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
    'level 1a': 'L1A',
    'level 1b': 'L1B_LAC',
    'smigen': 'SMI'
}
input_file_data = {}
#verbose = False
__version__ = '0.7-beta'

if __name__ == "__main__":
    sys.exit(main())