
"""
Utility functions for the multilevel_processor.
"""

__author__ = 'melliott'

TRUTH_VALUES = ['1', 'ON', 'on', 'TRUE', 'true', 'YES', 'yes']

def is_option_value_true(opt_val_str):
    """
    Returns True if opt_val_str is one the various possible values that OBPG
    programs accept as true.
    """
    opt_val = False
    if opt_val_str in TRUTH_VALUES:
        opt_val = True
    return opt_val


