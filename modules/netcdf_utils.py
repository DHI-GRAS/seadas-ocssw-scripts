#! /usr/bin/env python3
"""
Module containing utilities to manipulate netCDF4 files.
"""
__author__ = 'gfireman'

import sys
import time
import numpy as np
import netCDF4
from os.path import basename

def nccopy_var(srcvar, dstgrp, indices=None, verbose=False):
    """Copy a netCDF4 variable, optionally subsetting some dimensions.

    Function to copy a single netCDF4 variable and associated attributes.
    Optionally subset specified dimensions.

    Parameters
    ----------
    srcvar : netCDF4.Variable
        Open variable to be copied
    dstgrp : netCDF4.Group
        Open Group or Dataset destination object to copy stuff to
    indices : dict, optional
        Dict of dimname:[indexarr] to subset a dimension
    verbose : boolean, optional
        Print extra info

    Side Effects
    ------------
    Strings are written as H5T_CSET_ASCII, not H5T_CSET_UTF8
    Empty attributes are written as scalar "" instead of NULL
    """

    # create variable with same name, dimnames, storage format
    zlib =      srcvar.filters().get('zlib', False)
    shuffle =   srcvar.filters().get('shuffle', False)
    complevel = srcvar.filters().get('complevel', 0)
    dstvar = dstgrp.createVariable(srcvar.name,
                                srcvar.dtype,
                                srcvar.dimensions,
                                zlib=zlib,
                                shuffle=shuffle,
                                complevel=complevel)
    # TODO: get and set chunksizes.

    # set variable attributes
    dstvar.setncatts(srcvar.__dict__)

    # if no dimension changes, copy all
    if not indices or not any(k in indices for k in srcvar.dimensions):
        if verbose:
            print("\tcopying",srcvar.name)
        dstvar[:] = srcvar[:]

    # otherwise, copy only the subset
    else:
        if verbose:
            print("\tsubsetting",srcvar.name)
        tmpvar = srcvar[:]
        for dimname in indices:
            try:
                axis = srcvar.dimensions.index(dimname)
            except ValueError:
                continue
            tmpvar = np.take(tmpvar, indices[dimname], axis=axis)
        dstvar[:] = tmpvar

    # make sure it's written out
    dstgrp.sync()


def nccopy_grp(srcgrp, dstgrp, indices=None, verbose=False):
    """Recursively copy a netCDF4 group, optionally subsetting some dimensions.

    Function to recursively copy a netCDF4 group,
    with associated attributes, dimensions and variables.
    Optionally subset specified dimensions.

    Parameters
    ----------
    srcgrp : netCDF4.Group
        Open Group or Dataset source object containing stuff to be copied
    dstgrp : netCDF4.Group
        Open Group or Dataset destination object to copy stuff to
    indices : dict, optional
        Dict of dimname:[indexarr] to subset a dimension
    verbose : boolean, optional
        Print extra info
    """

    if verbose:
        print('grp: ', srcgrp.path)

    # copy all group attributes
    dstgrp.setncatts(srcgrp.__dict__)

    # define each dimension
    for dimname, dim in srcgrp.dimensions.items():
        if dim.isunlimited():
            dimsize = None
        elif indices and dimname in indices:
            dimsize = len(indices[dimname])
        else:
            dimsize = len(dim)
        dstgrp.createDimension(dimname, dimsize)

    # define each variable
    for varname, srcvar in srcgrp.variables.items():
        if verbose:
            print('var: ', '/'.join([srcgrp.path, srcvar.name]))
        nccopy_var(srcvar, dstgrp, indices=indices, verbose=verbose)

    # define each subgroup
    for grpname, srcsubgrp in srcgrp.groups.items():
        dstsubgrp = dstgrp.createGroup(grpname)
        nccopy_grp(srcsubgrp, dstsubgrp, indices=indices, verbose=verbose)


def nccopy(srcfile, dstfile, verbose=False):
    """Copy a netCDF4 file.

    Function to copy a netCDF4 file to a new file.
    Intended mostly as a demonstration.

    Parameters
    ----------
    srcfile : str
        Path to source file; must be netCDF4 format.
    dstfile : str
        Path to destination file; directory must exist.
    verbose : boolean, optional
        Print extra info
    """

    with netCDF4.Dataset(srcfile, 'r') as src, \
         netCDF4.Dataset(dstfile, 'w') as dst:
        if verbose:
            print('\nfile:', src.filepath())
        nccopy_grp(src, dst, verbose=verbose)


def ncsubset_vars(srcfile, dstfile, subset, verbose=False, **kwargs):
    """Copy a netCDF4 file, with some dimensions subsetted.

    Function to copy netCDF4 file to a new file,

    Function to copy a single netCDF4 variable and associated attributes.
    Optionally subset specified dimensions.

    Parameters
    ----------
    srcfile : str
        Path to source file; must be netCDF4 format.
    dstfile : str
        Path to destination file; directory must exist.
    subset : dict, optional
        Dict of dimname:[startindex,endindex] to subset a dimension
    verbose : boolean, optional
        Print extra info

    Side Effects
    ------------
    Strings are written as H5T_CSET_ASCII, not H5T_CSET_UTF8
    Empty attributes are written as scalar "" instead of NULL
    """

    # works only for dimensions defined in root group
    # TODO: allow dimensions specified in subgroups

    if verbose:
        print('opening', srcfile)
    with netCDF4.Dataset(srcfile, 'r') as src:

        # validate input
        for dimname in subset:
            if dimname not in src.dimensions:
                print('Warning: dimension "' +
                      dimname + '" does not exist in input file root group.')
            if (subset[dimname][0] > subset[dimname][1]):
                print('Invalid indices for dimension "' +
                      dimname + '"; exiting.')
                return
        for dimname, dim in src.dimensions.items():
            if ((dimname in subset) and
                any((0 > d or d > len(dim) - 1) for d in subset[dimname])):
                oldsubset = subset.copy()
                subset[dimname] = np.clip(subset[dimname], a_min=0,
                                          a_max=len(dim) - 1).tolist()
                print('Clipping "' + dimname +
                      '" dimension indices to match input file:',
                      oldsubset[dimname], '->', subset[dimname])

        # construct index arrays
        indices = {k : np.arange(subset[k][0],
                                 subset[k][1] + 1) for k in subset}

        # copy source file
        if verbose:
            print('opening', dstfile)
        with netCDF4.Dataset(dstfile, 'w') as dst:
            nccopy_grp(src, dst, indices=indices, verbose=verbose)
            update_history(dst, **kwargs)

            # dstfile closes automatically
        # srcfile closes automatically


def update_history(dataset, timestamp=None, cmdline=None):
    """Update 'date_created' and 'history' attributes

    Function to add or update 'date_created' and 'history'
    attributes for specified dataset (usually root).

    Parameters
    ----------
    dataset : netCDF4.Group
        Open Group or Dataset destination object to update
    timestamp : time.struct_time, optional
        Timestamp to add to history attribute
        Defaults to current time
    cmdline : string, optional
        Description to add to history attribute
    """

    if not timestamp:
        timestamp = time.gmtime()
    fmt = '%Y-%m-%dT%H:%M:%SZ'   # ISO 8601 extended date format
    date_created = time.strftime(fmt, timestamp)

    if not cmdline:
        cmdline = ' '.join([basename(sys.argv[0])]+sys.argv[1:])
    cmdline = ''.join([date_created, ': ', cmdline])
    if 'history' in dataset.ncattrs():
        history = ''.join([dataset.history.strip(), '; ', cmdline])
    else:
        history = cmdline

    dataset.setncattr('date_created', date_created)
    dataset.setncattr('history', history)
