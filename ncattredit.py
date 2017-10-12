#!/usr/bin/env python
#
import sys
import os
import time
import datetime
import netCDF4 as nc

if len(sys.argv) != 3:
    print('Usage:')
    callseq = sys.argv[0] + ' file ' + 'attr-file'
    print(callseq)
    print('\nThis script modifies global attributes in a netCDF file')
    print('\tfile:\t\tsource file to modify')
    print('\tattr-file:\tfile containig attribue=value pairs to modify\n')
    print('\tto delete an attribute, set the value to a blank string\n')
    print('\tattributes listed in the attr-file but not existing in\n\tthe source file will be added\n')
    print('exit status:')
    print('\t0:\tAll is well')
    print('\t100:\tNo modifications made')
    sys.exit(1)

inFile = sys.argv[1]
attrFile = sys.argv[2]
rootgrp = nc.Dataset(inFile, 'a')

attrs = open(attrFile,'r')

isModified=False

for attr in attrs:
    attrName,attrValue = attr.split('=')
    attrValue = attrValue.rstrip()
# Check to see if the attribute exists,
# if it does, modify accordingly
    try:
        attrValueExisting = nc.Dataset.getncattr(rootgrp,attrName)
        if (not attrValue == attrValueExisting):
            if (not len(attrValue)):
                nc.Dataset.delncattr(rootgrp,attrName)
            else:
                nc.Dataset.setncattr(rootgrp,attrName,list(attrValue))

            isModified=True 

# If it doesn't, add it
    except:
        if (len(attrValue)):
            nc.Dataset.setncattr(rootgrp,attrName,list(attrValue))
            isModified=True

# If we modified something, update the history
if (isModified):
    processtime = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%dT%H:%M:%S')

    history = nc.Dataset.getncattr(rootgrp,'history').rstrip() + '\n'+'['+processtime+'] '+os.path.basename(sys.argv[0])+ ' ' + sys.argv[1] + ' ' + sys.argv[2]
    nc.Dataset.setncattr(rootgrp,'history', history)
    rootgrp.close()
    sys.exit(0)
else:
    rootgrp.close()
    print("Attributes to modify do not differ from values desired...File not modified")
    sys.exit(100)


