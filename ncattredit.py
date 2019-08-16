#!/usr/bin/env python
#
import sys
import os
import time
import datetime
import netCDF4 as nc
import numpy as np

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

# update the history
processtime = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%dT%H:%M:%S')
history = nc.Dataset.getncattr(rootgrp,'history').rstrip() + '\n'+'['+processtime+'] '+os.path.basename(sys.argv[0])+ ' ' + sys.argv[1] + ' ' + sys.argv[2]
nc.Dataset.setncattr(rootgrp,'history', history)


attrs = open(attrFile,'r')

for attr in attrs:
    attrName,attrValue = attr.split('=')
    attrValue = attrValue.rstrip()
    
    # Check to see if the attribute exists,
    # if it does, delete it
    try:
        attrValueExisting = nc.Dataset.getncattr(rootgrp,attrName)
        nc.Dataset.delncattr(rootgrp,attrName)
    except:
        pass

    # if starts with a quote it is a string
    if len(attrValue):
        if attrValue.startswith('"'):
            attrValue = attrValue.strip('"').encode('ascii')
            nc.Dataset.setncattr(rootgrp,attrName,attrValue)
        else:
            # if has a comma it is an array
            if "," in attrValue:
                if attrValue.startswith('['):
                    attrValue = attrValue.lstrip('[').rstrip(']')
                partsStr = attrValue.split(',')
                if '.' in attrValue:
                    parts = np.array(partsStr).astype(np.dtype('f4'))
                else:
                    parts = np.array(partsStr).astype(np.dtype('i4'))
                nc.Dataset.setncattr(rootgrp,attrName,parts)
    
            else:
                if '.' in attrValue:
                    nc.Dataset.setncattr(rootgrp,attrName,np.array(attrValue).astype(np.dtype('f4')))
                else:
                    nc.Dataset.setncattr(rootgrp,attrName,np.array(attrValue).astype(np.dtype('i4')))
        
        
rootgrp.close()
