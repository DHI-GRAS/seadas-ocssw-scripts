#! /usr/bin/env python

import subprocess
import os

# set the rpath in the executables
os.chdir(os.path.join(os.environ['OCSSWROOT'], "bin"))
for fileName in os.listdir('.'):
    if os.path.isfile(fileName):
        line = subprocess.check_output(['file', fileName])
        if "Mach-O 64-bit executable" in line:
            #print ('------' + fileName)
            p = subprocess.Popen(["otool", "-L", fileName], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, err = p.communicate()
            #print("out=",out)
            lines = out.split('\n')
            for line in lines:
                if '/opt/local/lib' in line:
                    #print('  ' + line)
                    libPath = line.split()[0]
                    parts = libPath.split('/')
                    libName = parts[len(parts)-1]
                    newName = '@rpath/' + libName
                    #print('  ' + libPath + ' -> ' + newName)
                    subprocess.call(["install_name_tool", "-change", libPath, newName, fileName])

