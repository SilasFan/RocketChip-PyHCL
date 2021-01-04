from pyhcl import *


lgMaxSize = 32
asIdBits = 10
vaddrBits = 32
vaddrBitsExtended = 10
usingCompressed = True
XLen = 32
xLen = 32
maxPAddrBits = 32
pgIdxBits = 10
paddrBits = 32
coreDataBits = 32
coreDataBytes = 4
ppnBits = 32
vpnBits = 32
pgLevels = 10
pgLevelBits = 32
nPMPs = 16
usingVM = True
coreMaxAddrBits = 32
dcacheArbPorts = 8
M_SZ = 16
M_XRD = U.w(8)(1)
pmpGranularity = 8
minPgLevels=8


class Parameters:
    pass

class HasCoreParameters:
    pass


class coreParams:
    customCSRs=U.w(10)
    nL2TLBEntries=0
    dcacheReqTagBits=16

