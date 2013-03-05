
class Product(object):
    __name__ = 'Product'
    def __init__(self, out_type, src_type_list):
#        pass
        self.source_types = src_type_list
        self.output_type = out_type

    def __str__(self):
        return 'Output type: {0}, source types: {1}'.format(self.output_type,
                                                            str(self.source_types))

