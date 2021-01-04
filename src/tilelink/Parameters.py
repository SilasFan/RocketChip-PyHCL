from diplomacy.Parameters import *
from dataclasses import dataclass
from typing import List, Optional, Any, Callable, Tuple, Set


class TLChannelBeatBytes:
    pass


class TLCommonTransferSizes:
    pass


class BundleKeyBase:
    pass


class BundleFieldBase:
    pass


class SimpleProduct:
    pass


@dataclass
class TLMasterToSlaveTransferSizes(TLCommonTransferSizes):

    acquireT:   TransferSizes = TransferSizes()
    acquireB:   TransferSizes = TransferSizes()
    arithmetic: TransferSizes = TransferSizes()
    logical:    TransferSizes = TransferSizes()
    get:        TransferSizes = TransferSizes()
    putFull:    TransferSizes = TransferSizes()
    putPartial: TransferSizes = TransferSizes()
    hint:       TransferSizes = TransferSizes()

    @classmethod
    def unknownEmits(cls):
        return TLSlaveToMasterTransferSizes(
            acquireT   = TransferSizes(1, 4096),
            acquireB   = TransferSizes(1, 4096),
            arithmetic = TransferSizes(1, 4096),
            logical    = TransferSizes(1, 4096),
            get        = TransferSizes(1, 4096),
            putFull    = TransferSizes(1, 4096),
            putPartial = TransferSizes(1, 4096),
            hint       = TransferSizes(1, 4096))

    @classmethod
    def unknownSupports(cls):
        return TLSlaveToMasterTransferSizes()


class BaseNode:
    pass


class Resource:
    pass


@dataclass
class TLSlaveToMasterTransferSizes(TLCommonTransferSizes):
    probe:      TransferSizes = TransferSizes()
    arithmetic: TransferSizes = TransferSizes()
    logical:    TransferSizes = TransferSizes()
    get:        TransferSizes = TransferSizes()
    putFull:    TransferSizes = TransferSizes()
    putPartial: TransferSizes = TransferSizes()
    hint:       TransferSizes = TransferSizes()

    @classmethod
    def unknownEmits(cls):
        return TLSlaveToMasterTransferSizes(
            arithmetic = TransferSizes(1, 4096),
            logical    = TransferSizes(1, 4096),
            get        = TransferSizes(1, 4096),
            putFull    = TransferSizes(1, 4096),
            putPartial = TransferSizes(1, 4096),
            hint       = TransferSizes(1, 4096),
            probe      = TransferSizes(1, 4096))

    @classmethod
    def unknownSupports(cls):
        return TLSlaveToMasterTransferSizes()


class TLCommonTransferSizes:
    pass


@dataclass
class TLSlaveParameters(SimpleProduct):
    nodePath:           List[BaseNode]
    resources:          List[Resource]
    setName:            Optional[str]
    address:            List[AddressSet]
    regionType:         RegionType.T
    executable:         bool
    fifoId:             Optional[int]
    supports:           TLMasterToSlaveTransferSizes
    emits:              TLSlaveToMasterTransferSizes
    # By default, slaves are forbidden from issuing 'denied' responses (it prevents Fragmentation)
    alwaysGrantsT:      bool # typically only True for CacheCork'd read-write devices; dual: neverReleaseData
    # If fifoId=Some, all accesses sent to the same fifoId are executed and ACK'd in FIFO order
    # Note: you can only rely on this FIFO behaviour if your TLMasterParameters include requestFifo
    mayDenyGet:         bool # applies to: AccessAckData, GrantData
    mayDenyPut:         bool # applies to: AccessAck,     Grant,    HintAck
                                     # ReleaseAck may NEVER be denied

    @classmethod
    def v1(cls,
        address:            List[AddressSet],
        resources:          List[Resource] = list(),
        regionType:         RegionType.T  = RegionType.GET_EFFECTS,
        executable:         bool       = False,
        nodePath:           List[BaseNode] = list(),
        supportsAcquireT:   TransferSizes = TransferSizes(),
        supportsAcquireB:   TransferSizes = TransferSizes(),
        supportsArithmetic: TransferSizes = TransferSizes(),
        supportsLogical:    TransferSizes = TransferSizes(),
        supportsGet:        TransferSizes = TransferSizes(),
        supportsPutFull:    TransferSizes = TransferSizes(),
        supportsPutPartial: TransferSizes = TransferSizes(),
        supportsHint:       TransferSizes = TransferSizes(),
        mayDenyGet:         bool = False,
        mayDenyPut:         bool = False,
        alwaysGrantsT:      bool = False,
        fifoId:             int = None
    ):
        return TLSlaveParameters(
            setName       = None,
            address       = address,
            resources     = resources,
            regionType    = regionType,
            executable    = executable,
            nodePath      = nodePath,
            supports      = TLMasterToSlaveTransferSizes(
                acquireT      = supportsAcquireT,
                acquireB      = supportsAcquireB,
                arithmetic    = supportsArithmetic,
                logical       = supportsLogical,
                get           = supportsGet,
                putFull       = supportsPutFull,
                putPartial    = supportsPutPartial,
                hint          = supportsHint),
            emits         = TLSlaveToMasterTransferSizes.unknownEmits(),
            mayDenyGet    = mayDenyGet,
            mayDenyPut    = mayDenyPut,
            alwaysGrantsT = alwaysGrantsT,
            fifoId        = fifoId)

    @classmethod
    def v2(cls,
        address:       List[AddressSet],
        nodePath:      List[BaseNode]            = list(),
        resources:     List[Resource]            = list(),
        name:          Optional[str]             = None,
        regionType:    RegionType.T              = RegionType.GET_EFFECTS,
        executable:    bool                      = False,
        fifoId:        Optional[int]             = None,
        supports:      TLMasterToSlaveTransferSizes = TLMasterToSlaveTransferSizes.unknownSupports(),
        emits:         TLSlaveToMasterTransferSizes = TLSlaveToMasterTransferSizes.unknownEmits(),
        alwaysGrantsT: bool                      = False,
        mayDenyGet:    bool                      = False,
        mayDenyPut:    bool                      = False
    ):
        return TLSlaveParameters(
            nodePath      = nodePath,
            resources     = resources,
            setName       = name,
            address       = address,
            regionType    = regionType,
            executable    = executable,
            fifoId        = fifoId,
            supports      = supports,
            emits         = emits,
            alwaysGrantsT = alwaysGrantsT,
            mayDenyGet    = mayDenyGet,
            mayDenyPut    = mayDenyPut)


class TLManagerParameters:
    # @deprecated("Use TLSlaveParameters.v1 instead of TLManagerParameters","")
    def __new__(cls,
        address:            List[AddressSet],
        resources:          List[Resource] = list(),
        regionType:         RegionType.T   = RegionType.GET_EFFECTS,
        executable:         bool           = False,
        nodePath:           List[BaseNode] = list(),
        supportsAcquireT:   TransferSizes = TransferSizes(),
        supportsAcquireB:   TransferSizes = TransferSizes(),
        supportsArithmetic: TransferSizes = TransferSizes(),
        supportsLogical:    TransferSizes = TransferSizes(),
        supportsGet:        TransferSizes = TransferSizes(),
        supportsPutFull:    TransferSizes = TransferSizes(),
        supportsPutPartial: TransferSizes = TransferSizes(),
        supportsHint:       TransferSizes = TransferSizes(),
        mayDenyGet:         bool = False,
        mayDenyPut:         bool = False,
        alwaysGrantsT:      bool = False,
        fifoId:             Optional[int] = None
    ):
        return TLSlaveParameters.v1(
            address,
            resources,
            regionType,
            executable,
            nodePath,
            supportsAcquireT,
            supportsAcquireB,
            supportsArithmetic,
            supportsLogical,
            supportsGet,
            supportsPutFull,
            supportsPutPartial,
            supportsHint,
            mayDenyGet,
            mayDenyPut,
            alwaysGrantsT,
            fifoId,
      )


@dataclass(init=False)
class TLChannelBeatBytes:

    a: Optional[int] 
    b: Optional[int] 
    c: Optional[int] 
    d: Optional[int]

    def __init__(self, beatBytes = None):
        if beatBytes:
            self.a = beatBytes
            self.b = beatBytes
            self.c = beatBytes
            self.d = beatBytes

    def __post_init__(self):
        self.members = [self.a, self.b, self.c, self.d]
        for beatBytes in self.members:
            assert isPow2(beatBytes), "Data channel width must be a power of 2"


@dataclass
class TLSlavePortParameters(SimpleProduct):
    slaves:         List[TLSlaveParameters]
    channelBytes:   TLChannelBeatBytes
    endSinkId:      int
    minLatency:     int
    responseFields: List[BundleFieldBase]
    requestKeys:    List[BundleKeyBase]
    productPrefix:  str = "TLSlavePortParameters"
    productArity:   int = 6

    def __post_init__(self):
        assert not self.slaves.isEmpty, "Slave ports must have slaves"
        assert self.endSinkId >= 0, "Sink ids cannot be negative"
        assert self.minLatency >= 0, "Minimum required latency cannot be negative"

        # Diplomatically determined operation sizes emitted by all outward Slaves
        # as opposed to expectsVipChecker which generate circuitry to check which specific addresses
        self.allEmitClaims = self.slaves.map(lambda x: x.emits).reduce(lambda x, y: x.intersect(y))

        # Operation Emitted by at least one outward Slaves
        # as opposed to expectsVipChecker which generate circuitry to check which specific addresses
        self.anyEmitClaims = self.slaves.map(lambda x: x.emits).reduce(lambda x, y: x.mincover(y))

        # Diplomatically determined operation sizes supported by all outward Slaves
        # as opposed to expectsVipChecker which generate circuitry to check which specific addresses
        self.allSupportClaims = self.slaves.map(lambda x: x.supports).reduce(lambda x, y: x.intersect(y))
        self.allSupportAcquireT   = self.allSupportClaims.acquireT
        self.allSupportAcquireB   = self.allSupportClaims.acquireB
        self.allSupportArithmetic = self.allSupportClaims.arithmetic
        self.allSupportLogical    = self.allSupportClaims.logical
        self.allSupportGet        = self.allSupportClaims.get
        self.allSupportPutFull    = self.allSupportClaims.putFull
        self.allSupportPutPartial = self.allSupportClaims.putPartial
        self.allSupportHint       = self.allSupportClaims.hint

        # Operation supported by at least one outward Slaves
        # as opposed to expectsVipChecker which generate circuitry to check which specific addresses
        self.anySupportClaims = self.slaves.map(lambda x: x.supports).reduce(lambda x, y: x.mincover(y))
        self.anySupportAcquireT   = not self.anySupportClaims.acquireT.none
        self.anySupportAcquireB   = not self.anySupportClaims.acquireB.none
        self.anySupportArithmetic = not self.anySupportClaims.arithmetic.none
        self.anySupportLogical    = not self.anySupportClaims.logical.none
        self.anySupportGet        = not self.anySupportClaims.get.none
        self.anySupportPutFull    = not self.anySupportClaims.putFull.none
        self.anySupportPutPartial = not self.anySupportClaims.putPartial.none
        self.anySupportHint       = not self.anySupportClaims.hint.none

        # Supporting Acquire means being routable for GrantAck
        assert (self.endSinkId == 0) == (not self.anySupportAcquireB)


    def canEqual(self, that: Any) -> bool:
        return isinstance(that, TLSlavePortParameters)

    def productElement(self, n: int) -> Any:
        return [self.slaves, self.channelBytes, self.endSinkId, self.minLatency, self.responseFields, self.requestKeys][n]

    # Using this API implies you cannot handle mixed-width busses
    @property
    def beatBytes(self):
        # self.channelBytes.members.foreach(
        #     lambda width: (assert widen.isDefined and widen == channelBytes.a))
        return self.channelBytes.a.get

    # TODO this should be deprecated
    @property
    def managers(self): return self.slaves

    # def requireFifo(policy: TLFIFOFixer.Policy = TLFIFOFixer.allFIFO):
    #    relevant = self.slaves.filter(lambda m: policy(m))
        # relevant.foreach(
        #     lambda m: assert m.fifoId == relevant.head.fifoId, s"${m.name} had fifoId ${m.fifoId}, which was not homogeneous (${slaves.map(s => (s.name, s.fifoId))}) ")

    # Bounds on required sizes
    def maxAddress(self):  return self.slaves.map(lambda x: x.maxAddress).max
    def maxTransfer(self): return self.slaves.map(lambda x: x.maxTransfer).max
    def mayDenyGet(self):  return self.slaves.exists(lambda x: x.mayDenyGet)
    def mayDenyPut(self):  return self.slaves.exists(lambda x: x.mayDenyPut)

    # These return Optional[TLSlaveParameters] for your convenience
    def find(self, address: int): return slaves.find(lambda x: x.address.exists(lambda x: x.contains(address)))

    # The safe version will check the entire address
    def findSafe(self, address: U): return vec(self.slaves.map(lambda x: x.address.map(lambda x: x.contains(address)).reduce(lambda x, y: x|y)))
    # The fast version assumes the address is valid (you probably want fastProperty instead of this function)
    def findFast(self, address: U):
        routingMask = AddressDecoder(self.slaves.map(lambda x: x.address))
        return vec(self.slaves.map(lambda x: x.address.map(lambda x: x.widen(~routingMask)).distinct.map(lambda x: x.contains(address)).reduce(lambda x, y: x|y)))

    # Compute the simplest AddressSets that decide a key
    def fastPropertyGroup(self, p: Callable[[TLSlaveParameters], Any]) -> List[Tuple[Any, List[AddressSet]]]:
        groups = groupByIntoSeq(self.slaves.map(lambda m: (p(m), m.address)))( lambda x: x._1).map(lambda k, vs: (k, vs.flatMap(lambda x: x._2)))
        reductionMask = AddressDecoder(groups.map(lambda x: x._2))
        return groups.map(lambda k, seq: (k, AddressSet.unify(seq.map(lambda x: x.widen(~reductionMask)).distinct)))

    # Select a property
    def fastProperty(self, address: U, p: Callable, d: Callable):
        Mux1H(fastPropertyGroup(p).map(lambda v, a: (a.map(lambda x: x.contains(address)).reduce(lambda x, y: x|y), d(v))))

    # Note: returns the actual fifoId + 1 or 0 if None
    def findFifoIdFast(self, address: U) : return self.fastProperty(address, lambda x: x.fifoId+1 if x.fifoId else 0, lambda i: U(i))
    def hasFifoIdFast(self, address: U)  : return self.fastProperty(address, lambda x: x.fifoId.isDefined, lambda b: Bool(b))

    # Does this Port manage this ID/address?
    def containsSafe(self, address: U): return self.findSafe(address).reduce(lambda x, y: x|y)

    def addressHelper(self,
        # setting safe to False indicates that all addresses are expected to be legal, which might reduce circuit complexity
        safe:    bool,
        # member filters out the sizes being checked based on the opcode being emitted or supported
        member:  Callable[[TLSlaveParameters], TransferSizes],
        address: U,
        lgSize:  U,
        # _range provides a limit on the sizes that are expected to be evaluated, which might reduce circuit complexity
        _range:   Optional[TransferSizes]) -> Bool:
      # trim reduces circuit complexity by intersecting checked sizes with the _range argument
        def trim(x: TransferSizes):
            v = _range.intersect(x)
            return v if v else x
        # groupBy returns an unordered map, convert back to Seq and sort the result for determinism
        # groupByIntoSeq is turning slaves into trimmed membership sizes
        # We are grouping all the slaves by their transfer size where
        # if they support the trimmed size then
        # member is the type of transfer that you are looking for (What you are trying to filter on)
        # When you consider membership, you are trimming the sizes to only the ones that you care about
        # you are filtering the slaves based on both whether they support a particular opcode and the size
        # Grouping the slaves based on the actual transfer size _range they support
        # intersecting the _range and checking their membership
        # FOR SUPPORTCASES instead of returning the list of slaves,
        # you are returning a map from transfer size to the set of
        # address sets that are supported for that transfer size

        # find all the slaves that support a certain type of operation and then group their addresses by the supported size
        # for every size there could be multiple address ranges
        # safety is a trade off between checking between all possible addresses vs only the addresses
        # that are known to have supported sizes
        # the trade off is 'checking all addresses is a more expensive circuit but will always give you
        # the right answer even if you give it an illegal address'
        # the not safe version is a cheaper circuit but if you give it an illegal address then it might produce the wrong answer
        # fast presumes address legality
        supportCases = groupByIntoSeq(self.slaves)(lambda m: trim(member(m))).map(
            lambda t: (t[0], t[1].flatMap(lambda x: x.address)))

        # safe produces a circuit that compares against all possible addresses,
        # whereas fast presumes that the address is legal but uses an efficient address decoder
        mask = ~int(0) if (safe) else AddressDecoder(supportCases.map(lambda x: x._2))
        # Simplified creates the most concise possible representation of each cases' address sets based on the mask.
        simplified = supportCases.map(lambda t: (t[0], AddressSet.unify(t[1].map(lambda x: x.widen(~mask)).distinct)))
        # s is a size, you are checking for this size either the size of the operation is in s
        # We return an or-reduction of all the cases, checking whether any contains both the dynamic size and dynamic address on the wire.
        return simplified.map (lambda t: (Bool(Some(t[0]) == _range) or t[1].containsLg(lgSize)) and t[1].map(lambda x: x.contains(address)).reduce(lambda x, y: x|y)
                ).foldLeft(Bool(False))(lambda x, y: x|y)
        

    #@deprecated("Use edge.expectsVipCheckerMasterToSlaveAcquireT instead of manager.supportsAcquireTSafe","")
    def supportsAcquireTSafe   (self, address: U, lgSize: U, _range: Optional[TransferSizes] = None) : return self.addressHelper(True, lambda x: x.supports.acquireT,   address, lgSize, _range)
    #@deprecated("Use edge.expectsVipCheckerMasterToSlaveAcquireB instead of manager.supportsAcquireBSafe","")
    def supportsAcquireBSafe   (self, address: U, lgSize: U, _range: Optional[TransferSizes] = None) : return self.addressHelper(True, lambda x: x.supports.acquireB,   address, lgSize, _range)
    #@deprecated("Use edge.expectsVipCheckerMasterToSlaveArithmetic instead of manager.supportsArithmeticSafe","")
    def supportsArithmeticSafe (self, address: U, lgSize: U, _range: Optional[TransferSizes] = None) : return self.addressHelper(True, lambda x: x.supports.arithmetic,   address, lgSize, _range)
    #@deprecated("Use edge.expectsVipCheckerMasterToSlaveLogical instead of manager.supportsLogicalSafe","")
    def supportsLogicalSafe    (self, address: U, lgSize: U, _range: Optional[TransferSizes] = None) : return self.addressHelper(True, lambda x: x.supports.logical,   address, lgSize, _range)
    #@deprecated("Use edge.expectsVipCheckerMasterToSlaveGet instead of manager.supportsGetSafe","")
    def supportsGetSafe        (self, address: U, lgSize: U, _range: Optional[TransferSizes] = None) : return self.addressHelper(True, lambda x: x.supports.get,   address, lgSize, _range)
    #@deprecated("Use edge.expectsVipCheckerMasterToSlavePutFull instead of manager.supportsPutFullSafe","")
    def supportsPutFullSafe    (self, address: U, lgSize: U, _range: Optional[TransferSizes] = None) : return self.addressHelper(True, lambda x: x.supports.putFull,   address, lgSize, _range)
    #@deprecated("Use edge.expectsVipCheckerMasterToSlavePutPartial instead of manager.supportsPutPartialSafe","")
    def supportsPutPartialSafe (self, address: U, lgSize: U, _range: Optional[TransferSizes] = None) : return self.addressHelper(True, lambda x: x.supports.putPartial,   address, lgSize, _range)
    #@deprecated("Use edge.expectsVipCheckerMasterToSlaveHint instead of manager.supportsHintSafe","")
    def supportsHintSafe       (self, address: U, lgSize: U, _range: Optional[TransferSizes] = None) : return self.addressHelper(True, lambda x: x.supports.hint,   address, lgSize, _range)

    #@deprecated("Use edge.expectsVipCheckerMasterToSlaveAcquireT instead of manager.supportsAcquireTFast","")
    def supportsAcquireTFast   (self, address: U, lgSize: U, _range: Optional[TransferSizes] = None) : return self.addressHelper(False, lambda x: x.supports.acquireT,   address, lgSize, _range)
    #@deprecated("Use edge.expectsVipCheckerMasterToSlaveAcquireB instead of manager.supportsAcquireBFast","")
    def supportsAcquireBFast   (self, address: U, lgSize: U, _range: Optional[TransferSizes] = None) : return self.addressHelper(False, lambda x: x.supports.acquireB,   address, lgSize, _range)
    #@deprecated("Use edge.expectsVipCheckerMasterToSlaveArithmetic instead of manager.supportsArithmeticFast","")
    def supportsArithmeticFast (self, address: U, lgSize: U, _range: Optional[TransferSizes] = None) : return self.addressHelper(False, lambda x: x.supports.arithmetic,   address, lgSize, _range)
    #@deprecated("Use edge.expectsVipCheckerMasterToSlaveLogical instead of manager.supportsLogicalFast","")
    def supportsLogicalFast    (self, address: U, lgSize: U, _range: Optional[TransferSizes] = None) : return self.addressHelper(False, lambda x: x.supports.logical,   address, lgSize, _range)
    #@deprecated("Use edge.expectsVipCheckerMasterToSlaveGet instead of manager.supportsGetFast","")
    def supportsGetFast        (self, address: U, lgSize: U, _range: Optional[TransferSizes] = None) : return self.addressHelper(False, lambda x: x.supports.get,   address, lgSize, _range)
    #@deprecated("Use edge.expectsVipCheckerMasterToSlavePutFull instead of manager.supportsPutFullFast","")
    def supportsPutFullFast    (self, address: U, lgSize: U, _range: Optional[TransferSizes] = None) : return self.addressHelper(False, lambda x: x.supports.putFull,   address, lgSize, _range)
    #@deprecated("Use edge.expectsVipCheckerMasterToSlavePutPartial instead of manager.supportsPutPartialFast","")
    def supportsPutPartialFast (self, address: U, lgSize: U, _range: Optional[TransferSizes] = None) : return self.addressHelper(False, lambda x: x.supports.putPartial,   address, lgSize, _range)
    #@deprecated("Use edge.expectsVipCheckerMasterToSlaveHint instead of manager.supportsHintFast","")
    def supportsHintFast       (self, address: U, lgSize: U, _range: Optional[TransferSizes] = None) : return self.addressHelper(False, lambda x: x.supports.hint,   address, lgSize, _range)

    # Check for support of a given operation at a specific address
    def expectsVipCheckerSupportsAcquireT  (self, address: U, lgSize: U, _range: Optional[TransferSizes] = None): return self.addressHelper(False, lambda x: x.supports.acquireT,   address, lgSize, _range)
    def expectsVipCheckerSupportsAcquireB  (self, address: U, lgSize: U, _range: Optional[TransferSizes] = None): return self.addressHelper(False, lambda x: x.supports.acquireB,   address, lgSize, _range)
    def expectsVipCheckerSupportsArithmetic(self, address: U, lgSize: U, _range: Optional[TransferSizes] = None): return self.addressHelper(False, lambda x: x.supports.arithmetic, address, lgSize, _range)
    def expectsVipCheckerSupportsLogical   (self, address: U, lgSize: U, _range: Optional[TransferSizes] = None): return self.addressHelper(False, lambda x: x.supports.logical,    address, lgSize, _range)
    def expectsVipCheckerSupportsGet       (self, address: U, lgSize: U, _range: Optional[TransferSizes] = None): return self.addressHelper(False, lambda x: x.supports.get,        address, lgSize, _range)
    def expectsVipCheckerSupportsPutFull   (self, address: U, lgSize: U, _range: Optional[TransferSizes] = None): return self.addressHelper(False, lambda x: x.supports.putFull,    address, lgSize, _range)
    def expectsVipCheckerSupportsPutPartial(self, address: U, lgSize: U, _range: Optional[TransferSizes] = None): return self.addressHelper(False, lambda x: x.supports.putPartial, address, lgSize, _range)
    def expectsVipCheckerSupportsHint      (self, address: U, lgSize: U, _range: Optional[TransferSizes] = None): return self.addressHelper(False, lambda x: x.supports.hint,       address, lgSize, _range)

    def expectsVipCheckerEmitsProbe        (self, address: U, lgSize: U, _range: Optional[TransferSizes] = None): return self.addressHelper(False, lambda x: x.emits.probe,         address, lgSize, _range)
    def expectsVipCheckerEmitsArithmetic   (self, address: U, lgSize: U, _range: Optional[TransferSizes] = None): return self.addressHelper(False, lambda x: x.emits.arithmetic,    address, lgSize, _range)
    def expectsVipCheckerEmitsLogical      (self, address: U, lgSize: U, _range: Optional[TransferSizes] = None): return self.addressHelper(False, lambda x: x.emits.logical,       address, lgSize, _range)
    def expectsVipCheckerEmitsGet          (self, address: U, lgSize: U, _range: Optional[TransferSizes] = None): return self.addressHelper(False, lambda x: x.emits.get,           address, lgSize, _range)
    def expectsVipCheckerEmitsPutFull      (self, address: U, lgSize: U, _range: Optional[TransferSizes] = None): return self.addressHelper(False, lambda x: x.emits.putFull,       address, lgSize, _range)
    def expectsVipCheckerEmitsPutPartial   (self, address: U, lgSize: U, _range: Optional[TransferSizes] = None): return self.addressHelper(False, lambda x: x.emits.putPartial,    address, lgSize, _range)
    def expectsVipCheckerEmitsHint         (self, address: U, lgSize: U, _range: Optional[TransferSizes] = None): return self.addressHelper(False, lambda x: x.emits.hint,          address, lgSize, _range)

    def findTreeViolation(self):
        self.slaves.flatMap(lambda x: x.findTreeViolation()).headOptional

    @property
    def isTree(self):
        return not self.slaves.exists(lambda x: not x.isTree)

    @property
    def infoString(self):
        return "Slave Port Beatbytes = " + self.beatBytes + "\n" + "Slave Port MinLatency = " + self.minLatency + "\n\n" + self.slaves.map(lambda x: x.infoString).mkString

    def v1copy(self,
        managers:       List[TLSlaveParameters] = None,
        beatBytes:      int                     = -1,
        endSinkId:      int                     = None,
        minLatency:     int                     = None,
        responseFields: List[BundleFieldBase]   = None,
        requestKeys:    List[BundleKeyBase]     = None):

        if not managers: managers = self.managers      
        if not endSinkId: endSinkId = self.endSinkId     
        if not minLatency: minLatency = self.minLatency    
        if not responseFields: responseFields = self.responseFields
        if not requestKeys: requestKeys = self.requestKeys   

        return  TLSlavePortParameters(
            slaves       = managers,
            channelBytes = TLChannelBeatBytes(self.beatBytes) if (self.beatBytes != -1) else self.channelBytes,
            endSinkId    = endSinkId,
            minLatency   = minLatency,
            responseFields = responseFields,
            requestKeys    = requestKeys)

    def v2copy(self,
        slaves:         List[TLSlaveParameters] = None,
        channelBytes:   TLChannelBeatBytes      = None,
        endSinkId:      int                     = None,
        minLatency:     int                     = None,
        responseFields: List[BundleFieldBase]   = None,
        requestKeys:    List[BundleKeyBase]     = None):

        if not slaves: slaves = self.slaves
        if not channelBytes: channelBytes = self.channelBytes
        if not endSinkId: endSinkId = self.endSinkId
        if not minLatency: minLatency = self.minLatency
        if not responseFields: responseFields = self.responseFields
        if not requestKeys: requestKeys = self.requestKeys

        return TLSlavePortParameters(
            slaves         = slaves,
            channelBytes   = channelBytes,
            endSinkId      = endSinkId,
            minLatency     = minLatency,
            responseFields = responseFields,
            requestKeys    = requestKeys)

    #@deprecated("Use v1copy instead of copy","")
    def copy(self,
        managers:       List[TLSlaveParameters] = None,
        beatBytes:      int                     = -1,
        endSinkId:      int                     = None,
        minLatency:     int                     = None,
        responseFields: List[BundleFieldBase]   = None,
        requestKeys:    List[BundleKeyBase]     = None):

        if not slaves: slaves = self.slaves
        if not endSinkId: endSinkId = self.endSinkId
        if not minLatency: minLatency = self.minLatency
        if not responseFields: responseFields = self.responseFields
        if not requestKeys: requestKeys = self.requestKeys

        return self.v1copy(
            managers,
            beatBytes,
            endSinkId,
            minLatency,
            responseFields,
            requestKeys)

    @classmethod
    def v1(cls,
        managers:       List[TLSlaveParameters],
        beatBytes:      int,
        endSinkId:      int = 0,
        minLatency:     int = 0,
        responseFields: List[BundleFieldBase] = [],
        requestKeys:    List[BundleKeyBase]   = []):

        return  TLSlavePortParameters(
          slaves       = managers,
          channelBytes = TLChannelBeatBytes(beatBytes),
          endSinkId    = endSinkId,
          minLatency   = minLatency,
          responseFields = responseFields,
          requestKeys    = requestKeys)


# @deprecated("Use TLSlavePortParameters.v1 instead of TLManagerPortParameters","")
class TLManagerPortParameters:
    def __new__(cls, *args, **kwargs):
        return TLSlavePortParameters.v1(*args, **kwargs)


@dataclass
class TLMasterParameters(SimpleProduct):
    nodePath:          List[BaseNode]
    resources:         List[Resource]
    name:              str
    visibility:        List[AddressSet]
    unusedRegionTypes: Set[RegionType.T]
    executesOnly:      bool
    requestFifo:       bool # only a request not a requirement. applies to A not C.
    supports:          TLSlaveToMasterTransferSizes
    emits:             TLMasterToSlaveTransferSizes
    neverReleasesData: bool
    sourceId:          IdRange
    productPrefix:     str = "TLMasterParameters"
    # We intentionally omit nodePath for equality testing / formatting
    productArity:      int = 10

    def canEqual(that: Any) -> bool:
        return that.isInstanceOf[TLMasterParameters]


    def productElement(n: int) -> Any:
        return [
            self.name,
            self.sourceId,
            self.resources,
            self.visibility,
            self.unusedRegionTypes,
            self.executesOnly,
            self.requestFifo,
            self.supports,
            self.emits,
            self.neverReleasesData,
        ][n]

    def __post_init__(self):

        # @deprecated("Use supports.probe instead of supportsProbe","")
        supportsProbe:       TransferSizes   = self.supports.probe
        # @deprecated("Use supports.arithmetic instead of supportsArithmetic","")
        supportsArithmetic:  TransferSizes   = self.supports.arithmetic
        # @deprecated("Use supports.logical instead of supportsLogical","")
        supportsLogical:     TransferSizes   = self.supports.logical
        # @deprecated("Use supports.get instead of supportsGet","")
        supportsGet:         TransferSizes   = self.supports.get
        # @deprecated("Use supports.putFull instead of supportsPutFull","")
        supportsPutFull:     TransferSizes   = self.supports.putFull
        # @deprecated("Use supports.putPartial instead of supportsPutPartial","")
        supportsPutPartial:  TransferSizes   = self.supports.putPartial
        # @deprecated("Use supports.hint instead of supportsHint","")
        supportsHint:        TransferSizes   = self.supports.hint

        assert not self.sourceId.isEmpty
        assert not self.visibility.isEmpty
        assert self.supports.putFull.contains(self.supports.putPartial)
        # We only support these operations if we support Probe (ie: we're a cache
        assert self.supports.probe.contains(self.supports.arithmetic)
        assert self.supports.probe.contains(self.supports.logical)
        assert self.supports.probe.contains(self.supports.get)
        assert self.supports.probe.contains(self.supports.putFull)
        assert self.supports.probe.contains(self.supports.putPartial)
        assert self.supports.probe.contains(self.supports.hint)

        # visibility.combinations(2).foreach { case List(x,y) => require (not x.overlaps(y), s"$x and $y overlap.") }

        self.maxTransfer = [
          self.supports.probe.max,
          self.supports.arithmetic.max,
          self.supports.logical.max,
          self.supports.get.max,
          self.supports.putFull.max,
          self.supports.putPartial.max].max

    def infoString(self):
        return f"""Master Name = {self.name}
            |visibility = {self.visibility}
            |emits = {self.emits.infoString}
            |sourceId = {self.sourceId}
            |
            |""".stripMargin

    def v1copy(
        name:                str             = None, 
        sourceId:            IdRange         = None, 
        nodePath:            List[BaseNode]  = None, 
        requestFifo:         bool            = None, 
        visibility:          List[AddressSet]= None, 
        supportsProbe:       TransferSizes   = None, 
        supportsArithmetic:  TransferSizes   = None, 
        supportsLogical:     TransferSizes   = None, 
        supportsGet:         TransferSizes   = None, 
        supportsPutFull:     TransferSizes   = None, 
        supportsPutPartial:  TransferSizes   = None, 
        supportsHint:        TransferSizes   = None):

        if not name: name = self.name
        if not sourceId: sourceId = self.sourceId
        if not nodePath: nodePath = self.nodePath
        if not requestFifo: requestFifo = self.requestFifo
        if not visibility: visibility = self.visibility
        if not supports: supports = self.supports.probe
        if not supports: supports = self.supports.arithmetic
        if not supports: supports = self.supports.logical
        if not supports: supports = self.supports.get
        if not supports: supports = self.supports.putFull
        if not supports: supports = self.supports.putPartial
        if not supports: supports = self.supports.hint

        return  TLMasterParameters(
          nodePath          = nodePath,
          resources         = this.resources,
          name              = name,
          visibility        = visibility,
          unusedRegionTypes = this.unusedRegionTypes,
          executesOnly      = this.executesOnly,
          requestFifo       = requestFifo,
          supports          = TLSlaveToMasterTransferSizes(
            probe             = supportsProbe,
            arithmetic        = supportsArithmetic,
            logical           = supportsLogical,
            get               = supportsGet,
            putFull           = supportsPutFull,
            putPartial        = supportsPutPartial,
            hint              = supportsHint),
          emits             = this.emits,
          neverReleasesData = this.neverReleasesData,
          sourceId          = sourceId)

    def v2copy(
        nodePath:          List[BaseNode]                = None,
        resources:         List[Resource]                = None,
        name:              str                           = None,
        visibility:        List[AddressSet]              = None,
        unusedRegionTypes: Set[RegionType.T]             = None,
        executesOnly:      bool                          = None,
        requestFifo:       bool                          = None,
        supports:          TLSlaveToMasterTransferSizes  = None,
        emits:             TLMasterToSlaveTransferSizes  = None,
        neverReleasesData: bool                          = None,
        sourceId:          IdRange                       = None):

        if not nodePath: nodePath = self.nodePath
        if not resources: resources = self.resources
        if not name: name = self.name
        if not visibility: visibility = self.visibility
        if not unusedRegionTypes: unusedRegionTypes = self.unusedRegionTypes
        if not executesOnly: executesOnly = self.executesOnly
        if not requestFifo: requestFifo = self.requestFifo
        if not supports: supports = self.supports
        if not emits: emits = self.emits
        if not neverReleasesData: neverReleasesData = self.neverReleasesData
        if not sourceId: sourceId = self.sourceId

        return  TLMasterParameters(
          nodePath          = nodePath,
          resources         = resources,
          name              = name,
          visibility        = visibility,
          unusedRegionTypes = unusedRegionTypes,
          executesOnly      = executesOnly,
          requestFifo       = requestFifo,
          supports          = supports,
          emits             = emits,
          neverReleasesData = neverReleasesData,
          sourceId          = sourceId)

    # @deprecated("Use v1copy instead of copy","")
    def copy(
        name:                str             = None,
        sourceId:            IdRange         = None,
        nodePath:            List[BaseNode]  = None,
        requestFifo:         bool            = None,
        visibility:          List[AddressSet]= None,
        supportsProbe:       TransferSizes   = None,
        supportsArithmetic:  TransferSizes   = None,
        supportsLogical:     TransferSizes   = None,
        supportsGet:         TransferSizes   = None,
        supportsPutFull:     TransferSizes   = None,
        supportsPutPartial:  TransferSizes   = None,
        supportsHint:        TransferSizes   = None):

        if not name: name = self.name
        if not sourceId: sourceId = self.sourceId
        if not nodePath: nodePath = self.nodePath
        if not requestFifo: requestFifo = self.requestFifo
        if not visibility: visibility = self.visibility
        if not supports: supports = self.supports.probe
        if not supports: supports = self.supports.arithmetic
        if not supports: supports = self.supports.logical
        if not supports: supports = self.supports.get
        if not supports: supports = self.supports.putFull
        if not supports: supports = self.supports.putPartial
        if not supports: supports = self.supports.hint

        return self.v1copy(
            name               = name,
            sourceId           = sourceId,
            nodePath           = nodePath,
            requestFifo        = requestFifo,
            visibility         = visibility,
            supportsProbe      = supportsProbe,
            supportsArithmetic = supportsArithmetic,
            supportsLogical    = supportsLogical,
            supportsGet        = supportsGet,
            supportsPutFull    = supportsPutFull,
            supportsPutPartial = supportsPutPartial,
            supportsHint       = supportsHint)

    @classmethod
    def v1(cls,
        name:                str,
        sourceId:            IdRange         = IdRange(0,1),
        nodePath:            List[BaseNode]  = [],
        requestFifo:         bool            = False,
        visibility:          List[AddressSet]= [AddressSet(0, ~0)],
        supportsProbe:       TransferSizes   = TransferSizes(),
        supportsArithmetic:  TransferSizes   = TransferSizes(),
        supportsLogical:     TransferSizes   = TransferSizes(),
        supportsGet:         TransferSizes   = TransferSizes(),
        supportsPutFull:     TransferSizes   = TransferSizes(),
        supportsPutPartial:  TransferSizes   = TransferSizes(),
        supportsHint:        TransferSizes   = TransferSizes()):

        return TLMasterParameters(
          nodePath          = nodePath,
          resources         = [],
          name              = name,
          visibility        = visibility,
          unusedRegionTypes = Set(),
          executesOnly      = False,
          requestFifo       = requestFifo,
          supports          = TLSlaveToMasterTransferSizes(
            probe             = supportsProbe,
            arithmetic        = supportsArithmetic,
            logical           = supportsLogical,
            get               = supportsGet,
            putFull           = supportsPutFull,
            putPartial        = supportsPutPartial,
            hint              = supportsHint),
          emits             = TLMasterToSlaveTransferSizes.unknownEmits,
          neverReleasesData = False,
          sourceId          = sourceId)

    @classmethod
    def v2(cls,
        nodePath:          List[BaseNode]               = [],
        resources:         List[Resource]               = [],
        name:              str                          = '',
        visibility:        List[AddressSet]             = [AddressSet(0, ~0)],
        unusedRegionTypes: Set[RegionType.T]            = set(),
        executesOnly:      bool                         = False,
        requestFifo:       bool                         = False,
        supports:          TLSlaveToMasterTransferSizes = TLSlaveToMasterTransferSizes.unknownSupports,
        emits:             TLMasterToSlaveTransferSizes = TLMasterToSlaveTransferSizes.unknownEmits,
        neverReleasesData: bool                         = False,
        sourceId:          IdRange                      = IdRange(0,1)):

        return TLMasterParameters(
            nodePath          = nodePath,
            resources         = resources,
            name              = name,
            visibility        = visibility,
            unusedRegionTypes = unusedRegionTypes,
            executesOnly      = executesOnly,
            requestFifo       = requestFifo,
            supports          = supports,
            emits             = emits,
            neverReleasesData = neverReleasesData,
            sourceId          = sourceId)


if __name__ == "__main__":
    pass
