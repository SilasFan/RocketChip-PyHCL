from pyhcl import *
from helper.common import *


class DecoupledHelper:
    def __init__(self, *args):
        self.rvs = list(args)

    def fire(self, exclude = None, *includes):
        if exclude == None:
            return reduce(lambda x, y: x & y, self.rvs)
        return reduce(
            lambda x, y: x & y, 
            list(filter(lambda z: z != exclude), self.rvs) + list(includes))
    
