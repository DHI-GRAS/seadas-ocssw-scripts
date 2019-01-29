"""
Defines the Processor class, which defines how to create targets from their
sources.
"""

import os
#import processing_rules
#import subprocess
import sys

__author__ = 'melliott'

class Processor(object):
    """
    Processor contains the data and methods needed to create a single target.
    """
    __name__ = "Processor"
    #def __init__(self, instr, src, ruleset, target_type, targt=''):
    def __init__(self, instr, ruleset, program, par_data, out_dir):

        self.input_file = None
        self.geo_file = None
        self.par_data = par_data
        self.instrument = instr
        self.target_type = program
        self.ocssw_root = os.environ['OCSSWROOT']
        self.ocssw_bin = os.environ['OCSSW_BIN']
        self.rule_set = ruleset
        self.applicable_rules = self._get_applicable_rules(ruleset)
        self.out_directory = out_dir
        self.keepfiles = False

        self.required_types = self._find_required_types()

    def __cmp__(self, other):
        """
        Custom comparator to determine which Processor should come before another.
        This is based on the order in which they should be processed.
        """
        self_ndx = self.rule_set.order.index(self.target_type)
        if self_ndx < 0:
            print('Error!  Could not locate {0} target type in {1} rule set.'.format(self.target_type, str(self)))
            sys.exit(99)
#        other_ndx = other.rule_set.find_target_type(other.target_type)
        other_ndx = other.rule_set.order.index(other.target_type)
        if other_ndx < 0:
            print('Error!  Could not locate {0} target type in {1} rule set.'.format(other.target_type, str(other)))
            sys.exit(98)
        if self_ndx < other_ndx:
            return -1
        elif self_ndx > other_ndx:
            return 1
        else:
            return 0

    def __eq__(self, other):
        return self.__cmp__(other) == 0
    
    def __lt__(self, other):
        return self.__cmp__(other) < 0
        
    def __le__(self, other):
        return self.__cmp__(other) <= 0
    
    def __ne__(self, other):
        return self.__cmp__(other) != 0
    
    def __gt__(self, other):
        return self.__cmp__(other) > 0
    
    def __ge__(self, other):
        return self.__cmp__(other) >= 0
    
    def _find_required_types(self):
        req_types = []

        return req_types

    def _get_applicable_rules(self, ruleset):
        applicable_rules = []
        ndx = 0
        end_fnd = False
#        while (ndx < len(ruleset.rules)) and (not end_fnd):
        for targ in ruleset.order:
            if (self.target_type == targ):
                break
            else:
                applicable_rules.append(ruleset.rules[targ])
                ndx += 1
#        print "applicable_rules for %s: %s" % (str(self), str([str(r) for r in applicable_rules]))
        return applicable_rules

    def inputs_exist(self):
        """
        Return True if the inputs needed for the target output exist,
        otherwise return False.
        """
        input_file = ''
        if 'ifile' in self.par_data:
            input_file = self.par_data['ifile']
        return os.path.exists(input_file)

    def __repr__(self):
        return "Processor for target_type = {0}".format(self.target_type)

    def __str__(self):
        return "{0} processor".format(self.target_type)

    def execute(self):
        """
        Call the function to run the command for this Processor.
        """
        status = self.rule_set.rules[self.target_type].action(self)
        return status

    def requires_batch_processing(self):
        return self.rule_set.rules[self.target_type].requires_batch