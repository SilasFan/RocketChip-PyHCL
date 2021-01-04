from __future__ import annotations
from pyhcl import *
from helper.common import *
from typing import Union


class RegionType:
    # Define the 'more relaxed than' ordering
    class T:
        def __init__(self, v):
            self.v = v
        def __eq__(self, other):
            return self.v == other.v

    CACHED      = 1 # an intermediate agent may have cached a copy of the region for you
    TRACKED     = 2 # the region may have been cached by another master, but coherence is being provided
    UNCACHED    = 3 # the region has not been cached yet, but should be cached when possible
    IDEMPOTENT  = 4 # gets return most recently put content, but content should not be cached
    VOLATILE    = 5 # content may change without a put, but puts and gets have no side effects
    PUT_EFFECTS = 6 # puts produce side effects and so must not be combined/delayed
    GET_EFFECTS = 7 # gets produce side effects and so must not be issued speculatively


# A non-empty half-open range; [start, end)
class IdRange:
# extends Ordered[IdRange]
    def __init__(self, start: int, end: int):
        self.start = start
        self.end = end
        assert start >= 0, f"Ids cannot be negative, but got: {start}."
        assert start <= end, "Id ranges cannot be negative."

    def compare(self, x: IdRange):
        primary   = (self.start - x.start).signum
        secondary = (x.end - self.end).signum
        return primary if (primary != 0) else secondary

    @cls_or_insmethod
    def overlaps(self, x: Union[IdRange, List[IdRange]]):
        if not isinstance(self, type):
            return self.start < x.end and x.start < self.end
        # a list 
        s = x
        if (s.isEmpty):
            return None
        else:
            s.sort()
        for a, b in range(zip(s[1:], s[:-1])):
            if a.overlaps(b):
                return (a, b)
        return None

    def contains(self, x: Union[U, int, IdRange]):
        if isinstance(x, IdRange):
            return self.start <= x.start and x.end <= self.end
        if isinstance(x, int):
            return self.start <= x and x < self.end
        # U
        if (self.size == 0):
            return Bool(False)
        elif (self.size == 1): # simple comparison
            return x == U(self.start)
        else:
            # find index of largest different bit
            largestDeltaBit = log2Floor(self.start ^ (self.end-1))
            smallestCommonBit = largestDeltaBit + 1 # may not exist in x
            uncommonMask = (1 << smallestCommonBit) - 1
            uncommonBits = (x | U(0, width=smallestCommonBit))(largestDeltaBit, 0)
            # the prefix must match exactly (note: may shift ALL bits away)
            return ((x >> smallestCommonBit) == U(self.start >> smallestCommonBit) and
            # firrtl constant prop range analysis can eliminate these two:
            U(self.start & uncommonMask) <= uncommonBits and
            uncommonBits <= U((self.end-1) & uncommonMask))

    @property
    def shift(self, x: int): return IdRange(self.start+x, self.end+x)
    @property
    def size(self): return self.end - self.start
    @property
    def isEmpty(self): return self.end == self.start
    @property
    def range(self): return [i for i in range(self.start, self.end)]


# An potentially empty inclusive range of 2-powers [min, max] (in bytes)
class TransferSizes():

    def __init__(self, min = 0, max = None):
        self.min = min
        self.max = min if not max else max
        assert self.min <= self.max, f"Min tranffer {self.min} > max tranffer {self.max}"
        assert self.min >= 0 and self.max >= 0, f"TranfferSizef muft be pofitive, got: ({self.min}, {self.max})"
        assert self.max == 0 or isPow2(self.max), f"TranfferSizef muft be a power of 2, got: {self.max}"
        assert self.min == 0 or isPow2(self.min), f"TranfferSizef muft be a power of 2, got: {self.min}"
        assert self.max == 0 or self.min != 0, f"TranfferSize 0 if forbidden unless (0,0), got: ({self.min}, {self.max})"

    @property
    def none(self):
        return self.min == 0

    def contains(self, x: Union[int, TransferSizes]):
        if isinstance(x, int):
            return isPow2(x) and self.min <= x and x <= self.max
        else:
            return x.none or (self.min <= x.min and x.max <= self.max)

    def containsLg(self, x: Union[int, U]):
        if isinstance(x, int):
            return self.contains(1 << x)
        else:
            if (self.none):
                return Bool(False)
            elif (self.min == self.max):
                return U(log2Ceil(self.min)) == x
            else:
                return U(log2Ceil(self.min)) <= x and x <= U(log2Ceil(self.max)) # fix do logic and for U

    @cls_or_insmethod
    def intersect(self, x: Union[TransferSizes, list[TransferSizes]]):
        if isinstance(self, type):
            return reduce(lambda a, b: a.intersect(b), x)
        if (x.max < self.min or self.max < x.min):
            return TransferSizes()
        else:
            return TransferSizes(max(self.min, x.min), min(self.max, x.max))

    # Not a union, because the result may contain sizes contained by neither term
    # NOT TO BE CONFUSED WITH COVERPOINTS
    @cls_or_insmethod
    def mincover(self, x: Union[TransferSizes, list[TransferSizes]]):
        if isinstance(self, type):
            return foldLeft(lambda a, b: a.mincover(b), x, TransferSizes())
        if (self.none):
            return x
        elif (x.none):
            return self
        else:
            return TransferSizes(min(self.min, x.min), max(self.max, x.max))

    def __repr__(self):
        return f"TransferSizes[self.min, self.max]"

    @classmethod
    def asBool(cls, x):
        return not x.none


# AddressSets specify the address space managed by the manager
# Base is the base address, and mask are the bits consumed by the manager
# e.g: base=0x200, mask=0xff describes a device managing 0x200-0x2ff
# e.g: base=0x1000, mask=0xf0f decribes a device managing 0x1000-0x100f, 0x1100-0x110f, ...
class AddressSet():

    # TODO implement: extends Ordered[AddressSet]

    def __init__(self, base: int, mask: int):
        self.base = base
        self.mask = mask
        # Forbid misaligned base address (and empty sets)
        assert (base & mask) == 0, f"Mis-aligned AddressSets are forbidden, got: {self}"
        assert base >= 0, f"AddressSet negative base is ambiguous: {self.base}" # TL2 address widths are not fixed => negative is ambiguous
        # We do allow negative mask (=> ignore all high bits)

    def contains(self, x: Union[int, U]):
        if isinstance(x, int):
            return ((x ^ self.base) & ~self.mask) == 0
        elif isinstance(x, AddressSet):
            # contains iff bitwise: x.mask => mask && contains(x.base)
            return ((x.mask | (self.base ^ x.base)) & ~self.mask) == 0
        else:
            return ((x ^ U(self.base)).zext() & S(~self.mask)) == S(0)

    # turn x into an address contained in this set
    def legalize(self, x: U):
        return U(self.base) | (U(self.mask) & x)

    # overlap iff bitwise: both care (~mask0 & ~mask1) => both equal (base0=base1)
    def overlaps(self, x: AddressSet):
        return (~(self.mask | x.mask) & (self.base ^ x.base)) == 0

    # The number of bytes to which the manager must be aligned
    @property
    def alignment(self):
        return ((self.mask + 1) & ~self.mask)

    # Is this a contiguous memory range
    @property
    def contiguous(self):
        return self.alignment == self.mask+1

    @property
    def finite(self):
        return self.mask >= 0

    @property
    def max(self):
        assert self.finite, "Max cannot be calculated on infinite self.mask"
        return self.base | self.mask

    # Widen the match function to ignore all bits in imask
    def widen(self, imask: int):
        return AddressSet(self.base & ~imask, self.mask | imask)

    # Return an AddressSet that only contains the addresses both sets contain
    def intersect(self, x: AddressSet) -> AddressSet: # without Option
        if (not self.overlaps(x)):
            return None
        else:
            r_mask = self.mask & x.mask
            r_base = self.base | x.base
            return AddressSet(r_base, r_mask)

    def subtract(self, x: AddressSet) -> list[AddressSet]:
        remove = intersect(x)
        if not remove:
            return list(self)
        
        def helper(bit):
            nmask = (self.mask & (bit-1)) | remove.self.mask
            nbase = (remove.self.base ^ bit) & ~nmask
            return AddressSet(nbase, nmask)

        return list(map(helper, AddressSet.enumerateBits(self.mask & ~remove.self.mask)))

    # AddressSets have one natural Ordering (the containment order, if contiguous)
    def compare(self, x: AddressSet):
        primary     = (this.base - x.base).signum # smallest address first
        secondary = (x.mask - self.mask).signum # largest self.mask first
        return primary if (primary != 0) else secondary

    # We always want to see things in hex
    def __str__(self):
        if (self.mask >= 0):
            return "AddressSet(0x%x, 0x%x)".format(self.base, self.mask)
        else:
            return "AddressSet(0x%x, ~0x%x)".format(self.base, ~self.mask)

    @property
    def toRanges(self):
        assert self.finite, "Ranges cannot be calculated on infinite self.mask"
        size = self.alignment
        fragments = self.mask & ~(size-1)
        bits = bitIndexes(fragments)
        def helper(i):
            off = foldLeft(lambda a, b: a.setBit(bits(b)), bitIndexes(i), self.base)
            return AddressRange(off, size)
        return map(helper, [int(0) for _ in range((int(1) << bits.size))])

    @classmethod
    def everything(cls):
        return AddressSet(0, -1)

    @classmethod
    def misaligned(cls, base: int, size: int, tail: list[AddressSet] = list()) -> list[AddressSet]:
        if (size == 0):
            tail.reverse()
            return tail
        else:
            maxBaseAlignment = base & (-base) # 0 for infinite (LSB)
            maxSizeAlignment = int(1) << log2Floor(size) # MSB of size
            step = (maxSizeAlignment 
                if (maxBaseAlignment == 0 or maxBaseAlignment > maxSizeAlignment)
                else maxBaseAlignment)
            misaligned(base+step, size-step, tail.insert(0, AddressSet(base, step-1)))
        
    @classmethod
    def unify(cls, seq: list[AddressSet], bit: int = None) -> list[AddressSet]:
        if not bit: 
            bits = foldLeft(lambda a, b: a | b, map(lambda x: x.base, seq), int(0)) 
            foldLeft(lambda acc, bit: AddressSet.unify(acc, bit), AddressSet.enumerateBits(bits), seq).sort()
        else:
            # Pair terms up by ignoring 'bit'
            def helper(key, seq):
                if (len(seq) == 1):
                    return seq[0]
                else:
                    return key.copy(mask = key.mask | bit) # pair - widen mask by bit

            return list(map(helper, groupBy(
                lambda x: x.copy(base = x.base & ~bit), distinct(seq))))

    @classmethod
    def enumerateMask(cls, mask: int) -> list[int]:
        ret = []
        def helper(id: int) -> list[int]:
            if (id != mask):
                helper(((~mask | id) + 1) & mask)
            ret.append(id)
        helper(0)
        ret.reverse()
        return ret

    @classmethod
    def enumerateBits(cls, mask: int) -> list[int]:
        ret = []
        def helper(x: int):
            if (x == 0):
                return
            else:
                bit = x & (-x)
                ret.append(bit)
                helper(x & ~bit)
        helper(mask)
        return ret


if __name__ == "__main__":
    
    """ 
    TransferSizes
    """

    t0 = TransferSizes(1)
    t = TransferSizes(4, 8)
    t.none
    t.contains(1)
    t.containsLg(1)
    t.mincover(t0)
    t.intersect(t0)
    TransferSizes.intersect([t0])
    TransferSizes.mincover([t0])

    """
    AddressSet
    """
    a = AddressSet.everything()
    b = AddressSet(0x200, 0xff)
    b.finite
    b.widen(0x1ff)
    b.toRanges
    a.contains(10)
    print(AddressSet.enumerateBits(1))
    print(AddressSet.enumerateMask(1))

