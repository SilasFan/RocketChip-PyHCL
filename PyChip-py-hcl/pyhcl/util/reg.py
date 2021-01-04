from pyhcl import *
from .util import get_pyhcl_type


def RegNext(v):
    typ = get_pyhcl_type(v)
    reg = Reg(typ)
    reg <<= v
    return reg


def RegEnable(_next, enalbe):
    typ = get_pyhcl_type(_next)
    reg = Reg(typ)
    with when(enalbe):
        reg <<= _next
    return reg

