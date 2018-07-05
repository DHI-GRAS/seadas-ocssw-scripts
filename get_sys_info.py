#!/usr/bin/env python

"""
Print various items that may be of interest for SeaDAS and OCSSW
troubleshooting or forum posts.
"""

from __future__ import print_function

import argparse
import os
import platform
import re
#import socket
import subprocess
import sys

__version__ = '0.0.2.devel'

__author__ = 'melliott'

def get_cleaned_python_version():
    """
    Return the Python version, cleaned of extra text (especially relevant for
    Anaconda installations. Return "Not found" if the Python version is not
    found (although how that happens is a major mystery!).
    """
    py_ver = 'Not found'
    py_ver = sys.version
    if sys.version.upper().find('ANACONDA') != -1:
        py_ver = ' '.join([sys.version.split(' ')[0], '(part of an Anaconda installation)'])
    else:
        py_ver = sys.version.split(' ')[0]
    return py_ver

def get_l_program_version(l_program):
    """
    Returns the version for various "l programs" (e.g. l2gen, l3bin)
    """
    lprog_ver = ' '.join([l_program, 'not found'])
    try:
        cmd = l_program
        args = 'version'
        cmd_line = ' '.join([cmd, args])
        process = subprocess.Popen(cmd_line, shell=True, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        out_txt, _ = process.communicate()
        ver_lines = out_txt.split('\n')
        ver_lines.remove('')
        lprog_ver = ver_lines[-1].strip()
    except:
        print('Encountered exception')
        lprog_ver = ' '.join([l_program, 'not found'])
    return lprog_ver

def get_java_version():
    """
    Returns the java version, which is obtained by running java -version
    via subprocess.
    """
    java_ver = 'Not installed'
    try:
        cmd = 'java'
        args = '-version'
        cmd_line = ' '.join([cmd, args])
        process = subprocess.Popen(cmd_line, shell=True, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        # Java prints the version info to stderr, rather than stdout
        _, err_txt = process.communicate()
        if err_txt.upper().find('RUNTIME') != -1:
            err_lines = err_txt.split('\n')
            java_ver = re.sub('(^[^"]+|(?<=")[^"]+$)', '', err_lines[0]).strip('"')
    except:
        java_ver = 'Not installed'
    return java_ver

def get_seadas_root():
    """
    Returns the path of the SeaDAS installation as found in the SEADAS_ROOT or SEADAS
    environment variable, or "Not installed" if neither of those variables are defined
    in the environment.
    """
    seadas_root = 'Not installed'
    if 'SEADAS_ROOT' in os.environ:
        seadas_root = os.environ['SEADAS_ROOT']
    elif 'SEADAS' in os.environ:
        seadas_root = os.environ['SEADAS']
    return seadas_root

def get_seadas_version(seadas_root):
    """
    Returns the SeaDAS version as held in the VERSION.txt file in the
    directory pointed to by the SEADAS_ROOT environment variable.
    """
    seadas_ver = 'Not installed'
    ver_path = os.path.join(seadas_root, 'VERSION.txt')
    if os.path.exists(ver_path):
        with open(ver_path, 'rt') as ver_file:
            in_line = ver_file.readline()
            if in_line.find('VERSION') != -1:
                seadas_ver = in_line.split(' ', 1)[1].strip()
    return seadas_ver

def handle_command_line():
    """
    Handle help or version being requested on the command line.
    """
    parser = argparse.ArgumentParser(version=__version__)
    parser.parse_args()
    return

def main():
    """
    The program's main function - gets and prints items of interest.
    """
    handle_command_line()
    seadas_root = get_seadas_root()
    if 'OCSSWROOT' in os.environ:
        ocssw_root = os.environ['OCSSWROOT']
    else:
        ocssw_root = 'Not installed'

    #print('hostname: {0}'.format(socket.gethostname()))
    #print('processor: {0}'.format(platform.processor()))
    print('Platform: {0}'.format(platform.platform()))
    print('Python version: {0}'.format(get_cleaned_python_version()))
    print('Java version: {0}'.format(get_java_version()))
    print('SEADAS_ROOT: {0}'.format(seadas_root))
    print('OCSSWROOT: {0}'.format(ocssw_root))
    print('l2gen version: {0}'.format(get_l_program_version('l2gen').strip()))
    print('l2bin version: {0}'.format(get_l_program_version('l2bin').strip()))
    print('l3bin version: {0}'.format(get_l_program_version('l3bin').strip()))
    print('l3mapgen version: {0}'.format(get_l_program_version('l3mapgen').strip()))

if __name__ == '__main__':
    sys.exit(main())
