from pyhcl import *


class Decoupled(Bundle):

    def __init__(self, gen):
        Bundle.__init__(self,
            ready=U.w(1).flip(),
            valid=U.w(1),
            bits=gen
        )

    def fire(self):
        return self.valid & self.ready

