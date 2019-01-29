#! /usr/bin/python
from __future__ import print_function

import re

def __matches(regex, textlist):
    """Returns subset of input textlist which matches regex."""
    return [item for item in textlist if re.match(regex, item)]


def promote_value(mydict, keyregex):
    """
    Assign value of a single-item inner dictionary to its outer key.
    (cut out the middleman)

    mydict = {'OUTER': {'INNER': val}}
    promote_value(mydict, 'IN.*')
    mydict => {'OUTER': val}
    """
    for k, v in list(mydict.items()):
        if isinstance(v, dict):
            promote_value(v, keyregex)
            if len(list(v.keys())) == 1 and re.match(keyregex, list(v.keys())[0]):
                mydict[k] = v[list(v.keys())[0]]


def promote_dict(mydict, keyregex):
    """
    A single-item inner dictionary takes the place of its outer key.
    (level up)

    mydict = {'OUTER': {'INNER': val}}
    promote_dict(mydict, 'IN.*')
    mydict => {'INNER': val}
    """
    for k, v in list(mydict.items()):
        if isinstance(v, dict):
            promote_dict(v, keyregex)
            if len(list(v.keys())) == 1 and re.match(keyregex, list(v.keys())[0]):
                key = list(v.keys())[0]
                if key not in mydict:
                    mydict[key] = v[key]
                    del mydict[k]


def flatten_dict(mydict):
    """
    All keys are promoted, as long as a key of the same name does not exist at the upper level.

    mydict = {'OUTER': {'INNER1': {'INNER2': {'INNER3': val}}}}
    flatten_dict(mydict)
    mydict => {'INNER3': val}
    """
    for k, v in list(mydict.items()):
        if isinstance(v, dict):
            flatten_dict(v)
            for key in list(v.keys()):
                if key not in mydict:
                    mydict[key] = v[key]
                    del v[key]
            if not len(list(v.keys())):
                del mydict[k]


def delete_key(mydict, keyregex):
    """
    Remove all keys with name matching keyregex from nested dictionary.

    mydict = {'OUTER': {'INNER1': {'INNER2': {'INNER3': val}}}}
    delete_key(mydict, '*.2')
    mydict => {'OUTER': {'INNER1': {}}}
    """
    for v in list(mydict.values()):
        if isinstance(v, dict):
            delete_key(v, keyregex)
    for k in __matches(keyregex, list(mydict.keys())):
        del mydict[k]


def delete_empty(mydict):
    """
    Remove empty dictionaries from nested dictionary.

    mydict = {'OUTER': {'INNER': val}, 'EMPTY': {'EMPTY': {}}}
    delete_empty(mydict)
    mydict => {'OUTER': {'INNER': val} }
    """
    for k, v in list(mydict.items()):
        if isinstance(v, dict):
            delete_empty(v)
            if not len(list(v.keys())):
                del mydict[k]


def reassign_keys_in_dict(mydict, namekey, valuekey):
    """
    Combine two key/value pairs.

    mydict = {'OUTER': {'namekey': 'key', 'valuekey': val}}
    reassign_keys_in_dict(mydict, 'namekey', 'valuekey')
    mydict => {'OUTER': {'key': val}}
    """
    for v in list(mydict.values()):
        if isinstance(v, dict):
            reassign_keys_in_dict(v, namekey, valuekey)
            try:
                v[v[namekey]] = v[valuekey]
                del v[namekey]
                del v[valuekey]
            except (KeyError, TypeError):  pass


def _allkeys(mydict, myset):
    myset.update(mydict)
    for d in mydict.values():
        if isinstance(d, dict):
            _allkeys(d, myset)


def allkeys(mydict):
    """Return list of all unique keys in dictionary."""
    myset = set()
    _allkeys(mydict, myset)
    return sorted(myset)

#--------------------------------------------------------------------------

if __name__ == "__main__":
    import time

    def __dotest(cmd, dict1, dict2):
        print("\n", cmd)
        print("before: ", dict1)
        start_time = time.time()
        exec(cmd)
        end_time = time.time()
        print("after:  ", dict1)
        print("target: ", dict2)
        print(1000 * (end_time - start_time), "ms")

    val = 99

    cmd = "promote_value(dict1, 'IN.*')"
    dict1 = {'OUTER': {'INNER': val}}
    dict2 = {'OUTER': val}
    __dotest(cmd, dict1, dict2)

    cmd = "promote_dict(dict1, 'IN.*')"
    dict1 = {'OUTER': {'INNER': val}}
    dict2 = {'INNER': val}
    __dotest(cmd, dict1, dict2)

    cmd = "flatten_dict(dict1)"
    dict1 = {'OUTER': {'INNER1': {'INNER2': {'INNER3': val}}}}
    dict2 = {'INNER3': val}
    __dotest(cmd, dict1, dict2)

    cmd = "delete_key(dict1, '.*2')"
    dict1 = {'OUTER': {'INNER1': {'INNER2': {'INNER3': val}}}}
    dict2 = {'OUTER': {'INNER1': {}}}
    __dotest(cmd, dict1, dict2)

    cmd = "delete_empty(dict1)"
    dict1 = {'OUTER': {'INNER': val}, 'EMPTY': {'EMPTY': {}}}
    dict2 = {'OUTER': {'INNER': val}}
    __dotest(cmd, dict1, dict2)

    cmd = "reassign_keys_in_dict(dict1, 'namekey', 'valuekey')"
    dict1 = {'OUTER': {'namekey': 'key', 'valuekey': val}}
    dict2 = {'OUTER': {'key': val}}
    __dotest(cmd, dict1, dict2)
