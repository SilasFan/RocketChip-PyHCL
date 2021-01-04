from pyhcl import *
from .util import connect_all, get_pyhcl_type


def WireDefault(v):
    typ = get_pyhcl_type(v)
    w = Wire(typ)
    connect_all(w, v)
    return w

