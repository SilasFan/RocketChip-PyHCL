from diplomacy.Parameters import *
from dataclasses import dataclass
from typing import List, Optional


class TLCommonTransferSizes:
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
    alwaysGrantsT:      bool # typically only true for CacheCork'd read-write devices; dual: neverReleaseData
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
        name:          Optional[str]            = None,
        regionType:    RegionType.T              = RegionType.GET_EFFECTS,
        executable:    bool                      = False,
        fifoId:        Optional[int]               = None,
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
    def __init__(self,
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
