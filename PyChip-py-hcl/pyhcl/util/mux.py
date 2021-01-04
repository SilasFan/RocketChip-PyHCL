from pyhcl import *
from typing import List, Tuple, Union, Any


def _Mux1H(_in: List[Tuple[Bool, Any]]):
    return oneHotMux(_in)


def Mux1H(sel: Union[List[Bool], U], _in: Union[List[Any], U]):
    pass

