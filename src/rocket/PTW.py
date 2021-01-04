# See LICENSE.Berkeley for license details.
# See LICENSE.SiFive for license details.
from pyhcl import *
from pyhcl.util import *
from tile.Core import *
from helper.common import *
from diplomacy.Parameters import *
from rocket.CSR import *
from rocket.HellaCache import *
from rocket.PMP import *
from rocket.TLBPermissions import *
from helper.test import *
from util.package import *
from util.Replacement import *


class TLEdgeOut:
    pass


class PTWReq(CoreBundle):
    def __init__(self):
        CoreBundle.__init__(self,
            addr = U.w(vpnBits)
        )


class PTWResp(CoreBundle):
    def __init__(self):
        CoreBundle.__init__(self,
            ae = Bool,
            pte = PTE(),
            level = U.w(log2Ceil(pgLevels)),
            fragmented_superpage = Bool,
            homogeneous = Bool,
        )


class TLBPTWIO(CoreBundle, HasCoreParameters):
    def __init__(self):
        from rocket.TLB import SFenceReq
        CoreBundle.__init__(self,
            req=Decoupled(Valid(PTWReq())),
            resp=Valid(PTWResp()),
            ptbr=PTBR(),
            status=MStatus(),
            pmp=Vec(nPMPs, PMP()),
            customCSRs=coreParams.customCSRs,
        )


class PTWPerfEvents(Bundle):
    def __init__(self):
        Bundle.__init__(self,
            l2miss=Bool,
            l2hit=Bool,
            pte_miss=Bool,
            pte_hit=Bool,
        )


class DatapathPTWIO(CoreBundle, HasCoreParameters):
    def __init__(self):
        from rocket.TLB import SFenceReq
        CoreBundle.__init__(self,
            ptbr=PTBR(),
            sfence=Valid(SFenceReq()),
            status=MStatus(),
            pmp=Vec(nPMPs, PMP()),
            perf=PTWPerfEvents(),
            customCSRs=coreParams.customCSRs,
            clock_enabled=Bool # OUTPUT,
        )


class PTE(CoreBundle):
    def __init__(self):
        CoreBundle.__init__(self,
            ppn=U.w(54),
            reserved_for_software=U.w(2),
            d=Bool,
            a=Bool,
            g=Bool,
            u=Bool,
            x=Bool,
            w=Bool,
            r=Bool,
            v=Bool,
        )

    def table(self, dummy: int = 0): 
        return self.v & self.r & self.w & self.x

    def leaf(self, dummy: int = 0): 
        return self.v & (self.r | (self.x & self.w)) & self.a

    def ur(self, dummy: int = 0): 
        return self.sr() & self.u

    def uw(self, dummy: int = 0): 
        return self.sw() & self.u

    def ux(self, dummy: int = 0): 
        return self.sx() & self.u

    def sr(self, dummy: int = 0): 
        return self.leaf() & self.r

    def sw(self, dummy: int = 0): 
        return self.leaf() & self. w & self.d

    def sx(self, dummy: int = 0): 
        return self.leaf() & self.x


class L2TLBEntry(CoreBundle, HasCoreParameters):
    def __init__(self):
        CoreBundle.__init__(self,
            idxBits=log2Ceil(coreParams.nL2TLBEntries),
            tagBits=vpnBits - idxBits,
            tag=U.w(tagBits),
            ppn=U.w(ppnBits),
            d=Bool,
            a=Bool,
            u=Bool,
            x=Bool,
            w=Bool,
            r=Bool,
        )

        # def cloneType = L2TLBEntry().asInstanceOf[this.type]


# @chiselName
def PTW(n: int, edge: TLEdgeOut, p: Parameters):

    class clsPTW(CoreModule):
        io = IO(
            requestor=Output(Vec(n, TLBPTWIO())),
            mem=Output(HellaCacheIO()),
            dpath=Output(DatapathPTWIO()),
        )
        
        # omSRAMs = collection.mutable.ListBuffer[OMSRAM]()

        s_ready  = U(0)
        s_req    = U(1)
        s_wait1  = U(2)
        s_dummy1 = U(3)
        s_wait2  = U(4)
        s_wait3  = U(5)
        s_dummy2 = U(6)
        s_fragment_superpage = U(7)

        state = RegInit(s_ready)
        l2_refill_wire = Wire(Bool)

        arb = Arbiter(Valid(PTWReq()), n)
        # arb.io._in <> io.requestor.map(lambda x: x.req)
        arb.io.out.ready <<= (state == s_ready) & ~l2_refill_wire

        resp_valid = vec(io.requestor.size(), RegNext(Bool(False)))

        # clock_en = state != s_ready | l2_refill_wire | arb.io.out.valid | io.dpath.sfence.valid | io.dpath.customCSRs.disableDCacheClockGate
        # io.dpath.clock_enabled <<= usingVM & clock_en

        """
        gated_clock = (
            clock if (not usingVM | not tileParams.dcache.get.clockGate)
            else ClockGate(clock, clock_en, "ptw_clock_gate"))

        withClock (gated_clock) { # entering gated-clock domain
        """

        invalidated = Reg(Bool)
        count = Reg(U.w(log2Up(pgLevels)))
        resp_ae = RegNext(Bool(False))
        resp_fragmented_superpage = RegNext(Bool(False))

        r_req = Reg(PTWReq())
        r_req_dest = Reg(U.w(1))
        r_pte = Reg(PTE())

        mem_resp_valid = RegNext(io.mem.resp.valid)
        mem_resp_data = RegNext(io.mem.resp.bits.data)
        def helper(resp, mem_resp_data, mem_resp_valid):
            # assert not (resp.valid and io.mem.resp.valid)
            resp.ready <<= Bool(True)
            with when (resp.valid):
                mem_resp_valid <<= Bool(True)
                mem_resp_data <<= resp.bits.data
            
        helper(io.mem.uncached_resp, mem_resp_data, mem_resp_valid)
        del helper

        def helper(count, mem_resp_data):
            tmp = asTypeOf(mem_resp_data, PTE())
            res = WireDefault(tmp)
            res.ppn <<= tmp.ppn[ppnBits-1: 0]
            with when (tmp.r | tmp.w | tmp.x):
                # for superpage mappings, make sure PPN LSBs are zero
                for i in range(pgLevels - 1):
                    with when (count <= Bool(i) & tmp.ppn[(pgLevels-1-i)*pgLevelBits-1: (pgLevels-2-i)*pgLevelBits] != U(0)):
                        res.v <<= Bool(False)
            
            return res, (tmp.ppn >> ppnBits) != Bool(0)

        pte, invalid_paddr = helper(count, mem_resp_data)
        del helper

        traverse = pte.table() & ~invalid_paddr & count < Bool(pgLevels-1)
        if (not usingVM):
            pte_addr = U(0)
        else:
            def helper(r_req):
                return list(map(lambda i: (r_req.addr >> (pgLevels-i-1)*pgLevelBits)[pgLevelBits-1:0], 
                           [i for i in range(pgLevels)]))
            vpn_idxs = helper(r_req)
            del helper
            vpn_idx = get_from(vpn_idxs, count)
            pte_addr = Cat(r_pte.ppn, vpn_idx) << log2Ceil(xLen/8)
        
        def helper(r_pte, r_req):
            return list(map(
                lambda i: Cat(r_pte.ppn >> (pgLevelBits*i), padTo(r_req.addr[min(pgLevelBits*i, vpnBits)-1: 0], (pgLevelBits*i))),
                [i for i in range(10, 0, -1)]))
        fragmented_superpage_ppn = get_from(helper(r_pte, r_req), count)
        del helper

        with when (arb.io.out.fire()):
            connect_all(r_req, arb.io.out.bits.bits)
            r_req_dest <<= arb.io.chosen
        
        size = 1 << log2Up(pgLevels * 2)
        plru = PseudoLRU(size)
        valid = RegInit(U.w(size)(0))
        tags = Reg(Vec(size, U.w(paddrBits)))
        data = Reg(Vec(size, U.w(ppnBits)))

        def helper(pte_addr, tags, valid):
            return asUInt(list(map(lambda x: x == pte_addr, tags))) & valid
        hits = helper(pte_addr, tags, valid)
        hit = hits
        with when (mem_resp_valid & traverse & ~hit & ~invalidated):
            r = Mux(andRsize(valid, size), plru.way(), PriorityEncoder(valid)) # fix ~valid
            valid <<= valid | UIntToOH(r)
            tags[r] <<= pte_addr
            data[r] <<= pte.ppn
        
        # with when (hit & state == s_req): plru.access(OHToUInt(hits))
        with when (io.dpath.sfence.valid & ~io.dpath.sfence.bits.rs1): valid <<= U(0)

        # for i in range(pgLevels - 1):
        #     ccover(hit & state == s_req & count == i, f"PTE_CACHE_HIT_L{i}", f"PTE cache hit, level {i}")

        pte_cache_hit, pte_cache_data = hit & count < U(pgLevels-1), Mux1H(hits, data)

        
        io.dpath.perf.pte_miss <<= Bool(False)
        io.dpath.perf.pte_hit <<= Bool(False)

        l2_refill = RegNext(Bool(False))
        l2_refill_wire <<= l2_refill
        io.dpath.perf.l2miss <<= Bool(False)
        io.dpath.perf.l2hit <<= Bool(False)

        if (coreParams.nL2TLBEntries == 0):
            (l2_hit, l2_error, l2_pte, l2_tlb_ram) = (Bool(False), Bool(False), Wire(PTE()), None)
        else:
            code = ParityCode
            require(isPow2(coreParams.nL2TLBEntries))
            idxBits = log2Ceil(coreParams.nL2TLBEntries)

            (ram, omSRAM) =    DescribedSRAM(
                name = "l2_tlb_ram",
                desc = "L2 TLB",
                size = coreParams.nL2TLBEntries,
                data = U.w(code.width(L2TLBEntry().getWidth))
            )

            g = Reg(U.w(coreParams.nL2TLBEntries))
            valid = RegInit(U(0, coreParams.nL2TLBEntries))
            (r_tag, r_idx) = Split(r_req.addr, idxBits)
            with when (l2_refill & ~invalidated):
                entry = Wire(L2TLBEntry)
                entry <<= r_pte
                entry.tag <<= r_tag
                ram.write(r_idx, code.encode(entry.asUInt))

                mask = UIntToOH(r_idx)
                valid <<= valid | mask
                g <<= Mux(r_pte.g, g | mask, g & ~mask)
            
            with when (io.dpath.sfence.valid):
                valid <<= (
                    Mux(io.dpath.sfence.bits.rs1, valid & ~UIntToOH(io.dpath.sfence.bits.addr(idxBits+pgIdxBits-1, pgIdxBits)),
                    Mux(io.dpath.sfence.bits.rs2, valid & g, U(0))))
            

            s0_valid = ~l2_refill & arb.io.out.fire()
            s1_valid = RegNext(s0_valid & arb.io.out.bits.valid)
            s2_valid = RegNext(Bool, s1_valid)
            s1_rdata = ram.read(arb.io.out.bits.bits.addr(idxBits-1, 0), s0_valid)
            s2_rdata = code.decode(RegEnable(s1_rdata, s1_valid))
            s2_valid_bit = RegEnable(valid(r_idx), s1_valid)
            s2_g = RegEnable(g(r_idx), s1_valid)
            with when (s2_valid & s2_valid_bit & s2_rdata.error): valid <<= U(0)

            s2_entry = s2_rdata.uncorrected.asTypeOf(L2TLBEntry)
            s2_hit = s2_valid & s2_valid_bit & r_tag == s2_entry.tag
            io.dpath.perf.l2miss <<= s2_valid & ~(s2_valid_bit & r_tag == s2_entry.tag)
            io.dpath.perf.l2hit <<= s2_hit
            s2_pte = Wire(PTE)
            s2_pte <<= s2_entry
            s2_pte.g <<= s2_g
            s2_pte.v <<= True

            ccover(s2_hit, "L2_TLB_HIT", "L2 TLB hit")

            # omSRAMs += omSRAM
            (l2_hit, l2_error, l2_pte, l2_tlb_ram) = (s2_hit, s2_rdata.error, s2_pte, Some(ram))
        

        # if SFENCE occurs during walk, don't refill PTE cache or L2 TLB until next walk
        invalidated <<= io.dpath.sfence.valid | (invalidated & state != s_ready)

        io.mem.req.valid <<= state == s_req | state == s_dummy1
        io.mem.req.bits.phys <<= Bool(True)
        io.mem.req.bits.cmd    <<= M_XRD
        io.mem.req.bits._size <<= U(log2Ceil(xLen/8))
        io.mem.req.bits.signed <<= Bool(False)
        io.mem.req.bits.addr <<= pte_addr
        io.mem.req.bits.dprv <<= U(PRV.S)     # PTW accesses are S-mode by definition
        io.mem.s1_kill <<= l2_hit | state != s_wait1
        io.mem.s2_kill <<= Bool(False)

        pageGranularityPMPs = pmpGranularity >= (1 << pgIdxBits)
        # def helper(i):
        #     pgSize = int(1) << (pgIdxBits + ((pgLevels - 1 - i) * pgLevelBits))
        #     if (pageGranularityPMPs and i == pgLevels - 1):
        #         # require (TLBPageLookup.homogeneous(edge.manager.managers, pgSize), s"All memory regions must be $pgSize-byte aligned")
        #         return Bool(True)
        #     else:
        #         return TLBPageLookup(edge.manager.managers, xLen, p(CacheBlockBytes), pgSize)(pte_addr).homogeneous

        # pmaPgLevelHomogeneous = list(map(helper, [i for i in range(pgLevels)]))
        # pmaHomogeneous = pmaPgLevelHomogeneous[count]
        # pmpHomogeneous = PMPHomogeneityChecker(io.dpath.pmp).apply(pte_addr >> pgIdxBits << pgIdxBits, count)
        # homogeneous = pmaHomogeneous & pmpHomogeneous
        homogeneous = U.w(8)(0)

        for i in range(io.requestor.size()):
            io.requestor[i].resp.valid <<= resp_valid[i]
            io.requestor[i].resp.bits.ae <<= resp_ae
            connect_all(io.requestor[i].resp.bits.pte, r_pte)
            io.requestor[i].resp.bits.level <<= count
            io.requestor[i].resp.bits.homogeneous <<= homogeneous | Bool(pageGranularityPMPs)
            io.requestor[i].resp.bits.fragmented_superpage <<= resp_fragmented_superpage & Bool(pageGranularityPMPs)
            connect_all(io.requestor[i].ptbr, io.dpath.ptbr)
            io.requestor[i].customCSRs <<= io.dpath.customCSRs
            connect_all(io.requestor[i].status, io.dpath.status)
            connect_all(io.requestor[i].pmp, io.dpath.pmp)
        

        # control state machine
        next_state = WireDefault(state)
        state <<= OptimizationBarrier(next_state)

        with when(state == s_ready):
            with when (arb.io.out.fire()):
                next_state <<= Mux(arb.io.out.bits.valid, s_req, s_ready)
            count <<= U(pgLevels - minPgLevels) - io.dpath.ptbr.additionalPgLevels()
        
        with elsewhen(state == s_req):
            with when (pte_cache_hit):
                count <<= count + U(1)
                io.dpath.perf.pte_hit <<= Bool(True)
            with otherwise():
                next_state <<= Mux(io.mem.req.ready, s_wait1, s_req)
                io.dpath.perf.pte_miss <<= io.mem.req.ready
        
        with elsewhen(state == s_wait1):
            # This Mux is for the l2_error case; the l2_hit and not l2_error case is overriden below
            next_state <<= Mux(l2_hit, s_req, s_wait2)
        
        with elsewhen(state == s_wait2):
            next_state <<= s_wait3
            with when (io.mem.s2_xcpt.ae.ld):
                resp_ae <<= Bool(True)
                next_state <<= s_ready
                v = get_from(resp_valid, r_req_dest)
                v <<= Bool(True)
        
        with elsewhen(state == s_fragment_superpage):
            next_state <<= s_ready
            v = get_from(resp_valid, r_req_dest)
            v <<= Bool(True)
            resp_ae <<= Bool(False)
            with when (~homogeneous):
                count <<= U(pgLevels-1)
                resp_fragmented_superpage <<= Bool(True)

        def makePTE(ppn: U, default: PTE):
            pte = WireDefault(default)
            pte.ppn <<= ppn
            return pte
        
        r_pte <<= OptimizationBarrier(
            Mux(mem_resp_valid, pte,
            Mux(l2_hit & ~l2_error, l2_pte,
            Mux(state == s_fragment_superpage & ~homogeneous, makePTE(fragmented_superpage_ppn, r_pte),
            Mux(state == s_req & pte_cache_hit, makePTE(pte_cache_data, l2_pte),
            Mux(arb.io.out.fire(), makePTE(io.dpath.ptbr.ppn, r_pte),
            r_pte))))))

        with when (l2_hit & ~l2_error):
            # assert(state == s_req | state == s_wait1)
            next_state <<= s_ready
            v = get_from(resp_valid, r_req_dest)
            v <<= Bool(True)
            resp_ae <<= Bool(False)
            count <<= U(pgLevels-1)
        
        with when (mem_resp_valid):
            # assert(state == s_wait3)
            with when (traverse):
                next_state <<= s_req
                count <<= count + U(1)
            with otherwise():
                l2_refill <<= pte.v & ~invalid_paddr & count == U(pgLevels-1)
                ae = pte.v & invalid_paddr
                resp_ae <<= ae
                # with when (pageGranularityPMPs & count != U(pgLevels-1) & ~ae):
                #     next_state <<= s_fragment_superpage
                # with otherwise():
                #     next_state <<= s_ready
                #     v = get_from(resp_valid, r_req_dest)
                #     v <<= Bool(True)
                
        with when (io.mem.s2_nack):
            # assert(state == s_wait2)
            next_state <<= s_req
        
        """

        # for i in range(pgLevels):
        #     leaf = mem_resp_valid & ~traverse & count == i
        #     ccover(leaf & pte.v & ~invalid_paddr, f"L{i}", f"successful page-table access, level {i}")
        #     ccover(leaf & pte.v & invalid_paddr, f"L{i}_BAD_PPN_MSB", f"PPN too large, level {i}")
        #     ccover(leaf & ~mem_resp_data(0), f"L{i}_INVALID_PTE", f"page ~present, level {i}")
        #     if (i != pgLevels-1):
        #         ccover(leaf & ~pte.v & mem_resp_data(0), f"L{i}_BAD_PPN_LSB", f"PPN LSBs ~zero, level {i}")
        # 
        # ccover(mem_resp_valid & count == pgLevels-1 & pte.table(), f"TOO_DEEP", f"page table too deep")
        # ccover(io.mem.s2_nack, "NACK", "D$ nacked page-table access")
        # ccover(state == s_wait2 & io.mem.s2_xcpt.ae.ld, "AE", "access exception while walking page table")

        """
        """

        # leaving gated-clock domain

        # def ccover(cond: Bool, label: String, desc: String, sourceInfo: SourceInfo):
        #     if (usingVM): cover(cond, f"PTW_{label}", "MemorySystem;;" + desc)
        """

    return clsPTW()


# /** Mix-ins for constructing tiles that might have a PTW */
"""
trait CanHavePTW extends HasTileParameters with HasHellaCache: this: BaseTile =>
    module: CanHavePTWModule
    utlbOMSRAMs = collection.mutable.ListBuffer[OMSRAM]()
    var nPTWPorts = 1
    nDCachePorts += usingPTW.toInt


trait CanHavePTWModule extends HasHellaCacheModule:
    outer: CanHavePTW
    ptwPorts = ListBuffer(outer.dcache.module.io.ptw)
    ptw = Module(PTW(outer.nPTWPorts)(outer.dcache.node.edges.out(0), outer.p))
    if (outer.usingPTW):
        dcachePorts += ptw.io.mem
        outer.utlbOMSRAMs ++= ptw.omSRAMs
"""

if __name__ == "__main__":
    Emitter.dump(Emitter.emit(PTW(2, None, None)), f"{__file__}.fir")
