#! /usr/bin/env python

from __future__ import print_function
import re
import sys
import os

def ask_user(prompt):
    """
    Ask user a yes/no question
    """
    is_installed = raw_input(prompt)
    if re.search('(n|y)', is_installed.lower()[0]):
        return is_installed.lower()[0]
    else:
        return None


def chk_user_ver():
    """
    make sure the python executable file exists where the user reports it to be
    """
    ver = raw_input("What is the full path to your python (v2.6 or greater)?: ")
    if os.path.exists(ver) and os.path.isfile(ver):
        return ver
    else:
        print ("%s does not exist." % ver)
        return None

if __name__ == "__main__":
    req_version = (2, 6)
    cur_version = sys.version_info
    installed = None
    do_install = None
    pyver = None

    if cur_version >= req_version and cur_version[0] >= 2:
        print ("Python version acceptable")
    else:
        print ("Your default python interpreter is too old.")
        while installed is None:
            installed = ask_user("Do you have another python installation >= v2.6? (Y or N): ")
        if installed == 'y':
            while pyver is None:
                pyver = chk_user_ver()

            pylons = os.listdir(os.path.join(os.getenv("OCSSWROOT"), 'run', 'scripts'))
            print ("The following scripts have been modified to use %s as the interpreter:" % pyver)

            for f in pylons:
                if re.search('\.py$', f) and f != "pyverchk.py":
                    p = re.compile("^#.*python.*")
                    file = os.path.join(os.getenv("OCSSWROOT"), 'run', 'scripts', f)
                    text = open(file, "r").read()
                    pyf = open(file, "w")
                    newver = "#! " + pyver
                    pyf.write(p.sub(newver, text))
                    pyf.close()
                    print ("\t", file)

        else:
            print ('''
You may continue to install SeaDAS, however, the scripts required for data
processing will not work until you install a version of python >= v2.6
            ''')

            while do_install is None:
                do_install = ask_user("Would you like to continue with the installation? (Y or N): ")

            if do_install == "y":
                sys.exit(0)
            else:
                sys.exit(99)
