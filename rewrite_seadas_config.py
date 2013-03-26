#!/usr/bin/env python

"""
Rewrite the seadas configuration file (usually 
$SEADAS/config/seadas.config), changing the value
of the seadas.ocssw.root line to a value passed
in via the command line call.
"""

import shutil
import sys

def rewrite_seadas_config(seadas_config, install_dir):
    """
    Reads the input file then writes it to a temporary file,
    changing the appropriate entry.  Then it copies the temporary
    file over the original.
    """
    with open(seadas_config, 'rt') as in_file:
        in_content = in_file.readlines()

    with open('seadas_config.tmp', 'wt') as out_file:
        for line in in_content:
            if line.startswith('seadas.ocssw.root'):
                out_line = 'seadas.ocssw.root = ' + install_dir + '\n'
            else:
                out_line = line
            out_file.write(out_line)
    shutil.copy('seadas_config.tmp', seadas_config)
    return

def main():
    """
    Allows program to be imported without immediately executing.
    """
    rewrite_seadas_config(sys.argv[1], sys.argv[2])
    return 0

if __name__ == '__main__':
    sys.exit(main())
