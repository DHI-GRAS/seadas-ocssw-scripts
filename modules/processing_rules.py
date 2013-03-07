
"""
This module defines the classes needed for defining rules and rules sets for
the "uber" processor.
"""

__author__ = 'melliott'

class Rule():
    """
    Rule contains the data needed to create one target from its sources.
    """
    def __init__(self, targt, src_types, req_batch, actn):
        self.target_type = targt
        self.src_file_types = src_types
        self.requires_batch = req_batch
        self.action = actn

#    def __repr__(self):
#        return "Rule to convert: {0} to {1} using {2}".format(str(self.src_file_types), self.target_type, self.action)

    def __str__(self):
        return "{0} <- {1}".format(self.target_type, str(self.src_file_types))

class RuleSet():
    """
    Ruleset contains all the rules for a given instrument.
    """
    def __init__(self, nm, ruls, ordr):
        self.name = nm
        self.rules = ruls
        self.order = ordr

    #def _list_members_in(l1, l2):
    #    members_in = []
    #    for el in l1:
    #        if el in l2:
    #            members_in.append(el)
    #    return members_in

    def find_target_type(self, target_type):
        """
        Find the index of the target type specified by target_type.
        """
        ndx = 0
        found = False
        while (ndx < len(self.order)):
            if target_type == self.order[ndx]:
                found = True
                break
            else:
                ndx += 1
        if not found:
            ndx = -1
        if target_type in self.order:
            ndx = self.order.index(target_type)
        else:
            ndx = -1
        return ndx

    def can_process(self, target_type, source_types):
        """
        Determine if a target type can be created from the given source types.
        """
        return True
        print 'Entering can_process for: %s, %s' % (target_type, source_types)
        if target_type in self.rules:
            srcs_fnd = 0
            for src_type in source_types:
                if src_type in self.rules:
                    srcs_fnd += 1
                # Todo: add (recursive) code to search "further back" in the
                #       sources of sources, etc. to see if we can process this.
            if srcs_fnd == len(self.rules):
                return True
#            else:
#                print 'calling can_process for ' + str(self.rules[target].rules[source]) + ', ' + str(source)
#                return self.can_process(self.rules[target], source)
        else:
            return False
