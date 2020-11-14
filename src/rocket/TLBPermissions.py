from dataclasses import dataclass, field
from typing import List, Dict

from pyhcl import *
from helper.common import *
from diplomacy.Parameters import *
from tilelink.Parameters import *

@dataclass
class TLBPermissions:
    homogeneous: Bool # if false, the below are undefined
    r: Bool # readable
    w: Bool # writeable
    x: Bool # executable
    c: Bool # cacheable
    a: Bool # arithmetic ops
    l: Bool # logical ops


class TLBPageLookup:

    @dataclass
    class TLBFixedPermissions:
        e: Bool # get-/put-effects
        r: Bool # readable
        w: Bool # writeable
        x: Bool # executable
        c: Bool # cacheable
        a: Bool # arithmetic ops
        l: Bool
        useful: Bool = field(init=False)

        def __post_init__(self):
            # logical ops
            self.useful = self.r | self.w | self.x | self.c | self.a | self.l

    @staticmethod
    def groupRegions(managers: List[TLManagerParameters]) -> Dict[TLBFixedPermissions, List[AddressSet]]:
        permissions = map(
            lambda m: (m.address, TLBFixedPermissions(
            e = m.regionType in vec(RegionType.PUT_EFFECTS, RegionType.GET_EFFECTS),
            r = m.supportsGet     or m.supportsAcquireB, # if cached, never uses Get
            w = m.supportsPutFull or m.supportsAcquireT, # if cached, never uses Put
            x = m.executable,
            c = m.supportsAcquireB,
            a = m.supportsArithmetic,
            l = m.supportsLogical)), managers)

        return mapValues(lambda v: AddressSet.unify(flatten(v)), 
                         groupBy(lambda x: x[1], filter(lambda x: x[1].useful, permissions)))

        # AddressSet.unify(seq.flatMap(lambda x: x._1))) # coalesce same-permission regions

    # Unmapped memory is considered to be inhomogeneous
    @staticmethod
    def apply(managers: List[TLManagerParameters], xLen: int, cacheBlockBytes: int, pageSize: int):
        assert isPow2(xLen) and xLen >= 8
        assert isPow2(cacheBlockBytes) and cacheBlockBytes >= xLen/8
        assert isPow2(pageSize) and pageSize >= cacheBlockBytes

        xferSizes = TransferSizes(cacheBlockBytes, cacheBlockBytes)
        allSizes = TransferSizes(1, cacheBlockBytes)
        amoSizes = TransferSizes(4, xLen/8)

        for m in managers:
            assert not m.supportsGet        or m.supportsGet       .contains(allSizes),  f"Memory region '{m.name}' at {m.address} only supports {m.supportsGet} Get, but must support {allSizes}"
            assert not m.supportsPutFull    or m.supportsPutFull   .contains(allSizes),  f"Memory region '{m.name}' at {m.address} only supports {m.supportsPutFull} PutFull, but must support {allSizes}"
            assert not m.supportsPutPartial or m.supportsPutPartial.contains(allSizes),  f"Memory region '{m.name}' at {m.address} only supports {m.supportsPutPartial} PutPartial, but must support {allSizes}"
            assert not m.supportsAcquireB   or m.supportsAcquireB  .contains(xferSizes), f"Memory region '{m.name}' at {m.address} only supports {m.supportsAcquireB} AcquireB, but must support {xferSizes}"
            assert not m.supportsAcquireT   or m.supportsAcquireT  .contains(xferSizes), f"Memory region '{m.name}' at {m.address} only supports {m.supportsAcquireT} AcquireT, but must support {xferSizes}"
            assert not m.supportsLogical    or m.supportsLogical   .contains(amoSizes),  f"Memory region '{m.name}' at {m.address} only supports {m.supportsLogical} Logical, but must support {amoSizes}"
            assert not m.supportsArithmetic or m.supportsArithmetic.contains(amoSizes),  f"Memory region '{m.name}' at {m.address} only supports {m.supportsArithmetic} Arithmetic, but must support {amoSizes}"
            
        grouped = mapValues(
                lambda l: filter(lambda x: x.alignment >= pageSize, l),
                TLBPageLookup.groupRegions(managers)) # discard any region that's not big enough

        def lowCostProperty(prop):
            (yesm, nom) = partition(lambda k, v: prop(k), grouped)
            (yes, no) = (flatten(yesm.values()), flatten(nom.values()))
            # Find the minimal bits needed to distinguish between yes and no
            decisionMask = AddressDecoder(Seq(yes, no))
            simplify = lambda x: AddressSet.unify(distinct(map(lambda x: x.widen(~decisionMask), x)))
            (yesf, nof) = (simplify(yes), simplify(no))
            if (yesf.size < no.size):
                return lambda x: foldLeft(
                        lambda x, y: x + y, 
                        list(map(lambda x: x.contains(x), yesf)),
                        Bool(False))

            else:
                return lambda x: ~foldLeft(
                        lambda x, y: x + y, 
                        list(map(lambda x: x.contains(x), nof)),
                        Bool(False))

        # Derive simplified property circuits (don't care when not homo)
        rfn = lowCostProperty(lambda x: x.r)
        wfn = lowCostProperty(lambda x: x.w)
        xfn = lowCostProperty(lambda x: x.x)
        cfn = lowCostProperty(lambda x: x.c)
        afn = lowCostProperty(lambda x: x.a)
        lfn = lowCostProperty(lambda x: x.l)

        homo = AddressSet.unify(flatten(grouped.values()))
        return lambda x: TLBPermissions(
                homogeneous = foldLeft(
                    lambda x, y: x or y,  
                    map(lambda x: x.contains(x), homo),
                    Bool(False)),
                r = rfn(x),
                w = wfn(x),
                x = xfn(x),
                c = cfn(x),
                a = afn(x),
                l = lfn(x))

    # Are all pageSize intervals of mapped regions homogeneous?
    @staticmethod
    def homogeneous(managers: List[TLManagerParameters], pageSize: int):
        forall(lambda y: forall(lambda x: x.alignment >= pageSize, y), 
               TLBPageLookup.groupRegions(managers).values())


if __name__ == "__main__":
    pass
