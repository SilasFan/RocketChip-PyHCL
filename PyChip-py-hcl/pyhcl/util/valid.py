from pyhcl import *


class Valid(Bundle):
    def __init__(self, gen):
        Bundle.__init__(self, valid=Bool, bits=gen)
    def fire(self):
        return self.valid

