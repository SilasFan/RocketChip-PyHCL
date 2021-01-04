from pyhcl import *


def get_pyhcl_type(v):
    from pyhcl.dsl.cio import Input, Output
    from pyhcl.dsl.cdatatype import INT
    from pyhcl.core._repr import And, Or, Not, Neg, Xor, Add, Sub, Orr, Andr, Xorr, Index
    import inspect

    # print(v, isinstance(v, Bundle))
    data_typ = [Vec, VecInit, Bundle]
    hardware_typ = [Wire, Reg, RegInit]
    op_typ = [And, Or, Not, Neg, Xor, Add, Sub, Orr, Andr, Xorr]

    if v.__class__ in data_typ:
        return v
    if isinstance(v, Bundle):
        return v
    if inspect.isclass(v) and issubclass(v, INT):
        return v

    if v.__class__ in hardware_typ:
        typ = v.typ
    elif v.__class__ in op_typ:
        typ = v.typ
    elif isinstance(v, Index):
        typ = v.typ
    elif isinstance(v, Input):
        typ = v.typ
    elif isinstance(v, Output):
        typ = v.typ
    else:
        typ = v.value
    return get_pyhcl_type(typ)


def connect_all(lhs, rhs):

    from pyhcl.dsl.cdatatype import INT
    from pyhcl.ir.low_ir import Flip
    from pyhcl.core._repr import Index

    def _connect(lhs, rhs, lhs_typ, rhs_typ):
        if (isinstance(lhs_typ, Bundle) and
                isinstance(rhs_typ, Bundle)):
            common_attr = set(lhs_typ._kv.keys()) & set(rhs_typ._kv.keys())
            for attr in common_attr:
                _connect(
                    lhs.__getattribute__(attr),
                    rhs.__getattribute__(attr),
                    lhs_typ._kv[attr],
                    rhs_typ._kv[attr],
                )
        elif (isinstance(lhs_typ, Vec) and
                isinstance(rhs_typ, Vec) and
                len(lhs_typ) == len(rhs_typ)):
            for i in range(len(lhs_typ)):
                _connect(
                    lhs[i],
                    rhs[i],
                    lhs_typ.typ,
                    rhs_typ.typ,
                )
        elif (issubclass(lhs_typ, INT) and
                issubclass(rhs_typ, INT)):
            if lhs_typ.field == Flip():
                rhs <<= lhs
            else:
                lhs <<= rhs

    _connect(
        lhs,
        rhs,
        get_pyhcl_type(lhs),
        get_pyhcl_type(rhs),
    )

