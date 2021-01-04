from dataclasses import dataclass
from tile.Core import CoreModule, CoreBundle
from rocket.PTW import *
from helper.common import *
from helper.test import *
from pyhcl import *



class TLEdgeOut:
    pass


class SFenceReq(CoreBundle):
    def __init__(self):
        CoreBundle.__init__(self,
            rs1=Bool,
            rs2=Bool,
            addr=U.w(vaddrBits),
            asid=U.w(max(1, asIdBits)),
        )



class TLBReq(CoreBundle):
    def __init__(self, lgMaxSize):
        CoreBundle.__init__(self,
            vaddr=U.w(vaddrBitsExtended),
            passthrough=Bool,
            size=U.w(log2Ceil(lgMaxSize + 1)),
            cmd =U.w(M_SZ) # we have not bits,
        )
        

class TLBExceptions(Bundle):
    def __init__(self):
        Bundle.__init__(self,
            ld=Bool,
            st=Bool,
            inst=Bool,
        )


class TLBResp(CoreBundle):
    def __init__(self):
        CoreBundle.__init__(self,
            miss=Bool,
            paddr=U.w(paddrBits),
            pf=TLBExceptions(),
            ae=TLBExceptions(),
            ma=TLBExceptions(),
            cacheable=Bool,
            must_alloc=Bool,
            prefetchable=Bool,
        )
        

class TLBEntryData(CoreBundle):
    def __init__(self):
        CoreBundle.__init__(self,
            ppn=U.w(ppnBits),
            u=Bool,
            g=Bool,
            ae=Bool,
            sw=Bool,
            sx=Bool,
            sr=Bool,
            pw=Bool,
            px=Bool,
            pr=Bool,
            ppp=Bool, # PutPartial
            pal=Bool, # AMO logical
            paa=Bool, # AMO arithmetic
            eff=Bool, # get/put effects
            c=Bool,
            fragmented_superpage=Bool,
        )


class TLBEntry(CoreBundle):

    def __init__(self, nSectors: int, superpage: bool, superpageOnly: bool):
        assert nSectors == 1 or not superpage
        assert not superpageOnly or superpage
        self.nSectors = nSectors
        self.superpage = superpage
        self.superpageOnly = superpageOnly

        CoreBundle.__init__(self,
            level=U.w(log2Ceil(pgLevels)),
            tag=U.w(vpnBits),
            data=Vec(nSectors, U.w(TLBEntryData().width)),
            valid=Vec(nSectors, Bool),
        )
        self.entry_data=list(map(lambda x: asTypeOf(x, TLBEntryData()), self.data)),

    def sectorIdx(self, vpn: U):
        return vpn[log2(self.nSectors)-1: 0]

    def getData(self, vpn: U):
        return OptimizationBarrier(asTypeOf(self.data[self.sectorIdx(vpn)], TLBEntryData()))

    def sectorHit(self, vpn: U):
        return orR(self.valid) & self.sectorTagMatch(vpn)

    def sectorTagMatch(self, vpn: U):
        return ((self.tag ^ vpn) >> log2(self.nSectors)) == U(0)

    def hit(self, vpn: U):
        if self.superpage and usingVM:
            tagMatch = self.valid[0]
            for j in range(pgLevels):
                base = vpnBits - (j + 1) * pgLevelBits
                ignore = Bool(self.level < j or self.superpageOnly and j == pgLevels - 1)
                tagMatch = tagMatch & (ignore | self.tag[base + pgLevelBits - 1: base] == vpn[base + pgLevelBits - 1: base])
            return tagMatch
        idx = self.sectorIdx(vpn)
        return self.valid[idx] & self.sectorTagMatch(vpn)

    def ppn(self, vpn: U):
        data = self.getData(vpn)
        if self.superpage and usingVM:
            res = data.ppn >> pgLevelBits*(pgLevels - 1)
            for j in range(pgLevels):
                ignore = Bool(level < j or self.superpageOnly and j == pgLevels - 1)
                res = Cat(res, (Mux(ignore, vpn, U(0)) | data.ppn)[vpnBits - j*pgLevelBits - 1: vpnBits - (j + 1)*pgLevelBits])
            return res
        return data.ppn

    def insert(self, tag: U, level: U, entry: TLBEntryData):
        self.tag <<= tag
        self.level <<= level[log2Ceil(pgLevels - self.superpageOnly.toInt)-1: 0]
        idx = sectorIdx(tag)
        self.valid[idx] <<= Bool(True)
        self.data[idx] <<= entry.asUInt # impl asUInt

    def invalidate(self):
        for i in range(len(self.valid)):
            self.valid[i] <<= Bool(False)

    def invalidateVPN(self, vpn: U): 
        if self.superpage:
            with when (self.hit(vpn)): self.invalidate()
        else:
            with when (self.sectorTagMatch(vpn)):
                self.valid[self.sectorIdx(vpn)] <<= Bool(False)

            # For fragmented self.superpage mappings, we assume the worst (largest)
            # case, and zap entries whose most-significant VPNs match
            with when (((self.tag ^ vpn) >> (pgLevelBits * (pgLevels - 1))) == 0):
                for i in range(len(self.entry_data)):
                    with when(~self.entry_data[i].fragmented_superpage):
                        self.valid[i] <<= Bool(False)

    def invalidateNonGlobal(self):
        for i in range(len(self.entry_data)):
            with when(~self.entry_data[i].g):
                self.valid[i] <<= Bool(False)


@dataclass
class TLBConfig:
    nSets: int
    nWays: int
    nSectors: int = 4
    nSuperpageEntries: int = 4


# impl TLBPTWIO, TLEdgeOut, Parameters

def TLB(instruction: bool, lgMaxSize: int, cfg: TLBConfig, edge: TLEdgeOut, p: Parameters):

    class clsTLB(CoreModule):
        # use IO replace Bundle
        io = IO(
            req=Input(Decoupled(TLBReq(lgMaxSize))),
            resp=Output(TLBResp()),
            sfence=Input(Valid(SFenceReq())),
            ptw=Output(TLBPTWIO()),
            kill=Input(Bool), # suppress a TLB refill, one cycle after a miss
        )

        pageGranularityPMPs = pmpGranularity >= (1 << pgIdxBits)
        vpn = io.req.bits.vaddr[vaddrBits-1: pgIdxBits]
        memIdx = vpn[log2(cfg.nSectors) + log2(cfg.nSets) - 1: log2(cfg.nSectors)]
        sectored_entries = RegInit(Vec(cfg.nSets, Vec(int(cfg.nWays / cfg.nSectors), TLBEntry(cfg.nSectors, False, False))))

        superpage_entries = RegInit(Vec(cfg.nSuperpageEntries, TLBEntry(1, True, True)))
        special_entry = RegInit(TLBEntry(1, True, False)) if not pageGranularityPMPs else None

        ordinary_entries = sectored_entries[memIdx] + superpage_entries
        all_entries = ordinary_entries + [special_entry] if special_entry else []
        all_real_entries = sectored_entries.flatten + superpage_entries + [special_entry] if special_entry else []

        s_ready = U(1)
        s_request = U(2)
        s_wait = U(3)
        s_wait_invalidate = U(4)

        state = RegInit(s_ready)
        r_refill_tag = Reg(U.w(vpnBits))
        r_superpage_repl_addr = Reg(U.w(log2Ceil(len(superpage_entries))))
        r_sectored_repl_addr = Reg(U.w(log2Ceil(sectored_entries[0].size())))
        r_sectored_hit_addr = Reg(U.w(log2Ceil(sectored_entries[0].size())))
        r_sectored_hit = Reg(Bool)

        priv = io.ptw.status.prv if instruction else io.ptw.status.dprv
        priv_s = priv[0]
        priv_uses_vm = priv <= PRV.S
        vm_enabled = Bool(usingVM) & io.ptw.ptbr.mode(io.ptw.ptbr.mode.getWidth-1) & priv_uses_vm & ~io.req.bits.passthrough

        # share a single physical memory attribute checker (unshare if critical path)
        refill_ppn = io.ptw.resp.bits.pte.ppn[ppnBits-1: 0]
        do_refill = Bool(usingVM) & io.ptw.resp.valid
        invalidate_refill = isOneOf(state, s_request, s_wait_invalidate) | io.sfence.valid
        mpu_ppn = Mux(do_refill, refill_ppn,
                  Mux(vm_enabled & Bool(not special_entry is None),
                      special_entry.ppn[vpn] if special_entry else U(0),
                      io.req.bits.vaddr >> pgIdxBits))

        mpu_physaddr = Cat(mpu_ppn, io.req.bits.vaddr[pgIdxBits-1: 0])
        mpu_priv = Mux(Bool(usingVM) & (do_refill | io.req.bits.passthrough), PRV.S, Cat(io.ptw.status.debug, priv))
        pmp = Module(PMPChecker(lgMaxSize)) # fix
        pmp.io.addr <<= mpu_physaddr
        pmp.io.size <<= io.req.bits.size
        pmp.io.pmp <<= io.ptw.pmp
        pmp.io.prv <<= mpu_priv
        legal_address = reduce(lambda x,y: x|y, edge.manager.findSafe(mpu_physaddr)) # fix

        def fastCheck(member):
            return legal_address & edge.manager.fastProperty(mpu_physaddr, member, lambda b: Bool(b)) # fix

        cacheable = fastCheck(lambda x: x.supportsAcquireT) & (instruction | ~usingDataScratchpad)
        homogeneous = TLBPageLookup(edge.manager.managers, xLen, p(CacheBlockBytes), 1 << pgIdxBits)(mpu_physaddr).homogeneous

        deny_access_to_debug = mpu_priv <= PRV.M & p(DebugModuleKey).map(lambda dmp: dmp.address.contains(mpu_physaddr)).getOrElse(False) # fix

        prot_r = fastCheck(lambda x: x.supportsGet) & ~deny_access_to_debug & pmp.io.r
        prot_w = fastCheck(lambda x: x.supportsPutFull) & ~deny_access_to_debug & pmp.io.w
        prot_pp = fastCheck(lambda x: x.supportsPutPartial)
        prot_al = fastCheck(lambda x: x.supportsLogical)
        prot_aa = fastCheck(lambda x: x.supportsArithmetic)
        prot_x = fastCheck(lambda x: x.executable) & ~deny_access_to_debug & pmp.io.x
        prot_eff = fastCheck(lambda x: x.regionType in [RegionType.PUT_EFFECTS, RegionType.GET_EFFECTS])

        sector_hits = sectored_entries(memIdx).map(lambda x: x.sectorHit(vpn))
        superpage_hits = superpage_entries.map(lambda x: x.hit(vpn))
        hitsVec = all_entries.map(lambda x: vm_enabled & x.hit(vpn))
        real_hits = hitsVec.asUInt
        hits = Cat(~vm_enabled, real_hits)
        ppn = Mux1H(hitsVec.append(~vm_enabled), all_entries.map(lambda x: x.ppn(vpn)).append(vpn[ppnBits-1: 0])) # fix

        # permission bit arrays
        with when(do_refill):
            pte = io.ptw.resp.bits.pte
            newEntry = Wire(TLBEntryData)
            newEntry.ppn <<= pte.ppn
            newEntry.c <<= cacheable
            newEntry.u <<= pte.u
            newEntry.g <<= pte.g & pte.v
            newEntry.ae <<= io.ptw.resp.bits.ae
            newEntry.sr <<= pte.sr()
            newEntry.sw <<= pte.sw()
            newEntry.sx <<= pte.sx()
            newEntry.pr <<= prot_r
            newEntry.pw <<= prot_w
            newEntry.px <<= prot_x
            newEntry.ppp <<= prot_pp
            newEntry.pal <<= prot_al
            newEntry.paa <<= prot_aa
            newEntry.eff <<= prot_eff
            newEntry.fragmented_superpage <<= io.ptw.resp.bits.fragmented_superpage

            with when(Bool(not special_entry is None) & ~io.ptw.resp.bits.homogeneous):
                for i in range(len(special_entry)):
                    special_entry[i].insert(
                            r_refill_tag, io.ptw.resp.bits.level, newEntry)
                    with when(invalidate_refill):
                        special_entry[i].invalidate()
            with elsewhen(io.ptw.resp.bits.level < pgLevels-1):
                for i in range(len(superpage_entries)):
                    with when(r_superpage_repl_addr == i):
                        superpage_entries[i].insert(r_refill_tag, io.ptw.resp.bits.level, newEntry)
                    with when(invalidate_refill):
                        superpage_entries[i].invalidate()
            with otherwise():
                r_memIdx = r_refill_tag[log2(cfg.nSectors) + log2(cfg.nSets) - 1: log2(cfg.nSectors)]
                waddr = Mux(r_sectored_hit, r_sectored_hit_addr, r_sectored_repl_addr)
                for i in range(sectored_entries[r_memIdx].size()):
                    with when(waddr == i):
                        with when(~r_sectored_hit):
                            e.invalidate()
                    sectored_entries[r_memIdx][i].insert(r_refill_tag, U(0), newEntry)
                    with when(invalidate_refill):
                        sectored_entries[r_memIdx][i].invalidate()


        entries = all_entries.map(lambda x: x.getData(vpn))
        normal_entries = ordinary_entries.map(lambda x: x.getData(vpn))
        nPhysicalEntries = 1 + len(special_entry)
        ptw_ae_array = Cat(Bool(False), entries.map(lambda x: x.ae).asUInt)
        priv_rw_ok = Mux(~priv_s | io.ptw.status.sum, entries.map(lambda x: x.u).asUInt, U(0)) | Mux(priv_s, ~entries.map(lambda x: x.u).asUInt, U(0))
        priv_x_ok = Mux(priv_s, ~entries.map(lambda x: x.u).asUInt, entries.map(lambda x: x.u).asUInt)
        r_array = Cat(Bool(True), priv_rw_ok & (entries.map(lambda x: x.sr).asUInt | Mux(io.ptw.status.mxr, entries.map(lambda x: x.sx).asUInt, U(0))))
        w_array = Cat(Bool(True), priv_rw_ok & entries.map(lambda x: x.sw).asUInt)
        x_array = Cat(Bool(True), priv_x_ok & entries.map(lambda x: x.sx).asUInt)
        pr_array = Cat(Fill(nPhysicalEntries, prot_r), normal_entries.map(lambda x: x.pr).asUInt) & ~ptw_ae_array
        pw_array = Cat(Fill(nPhysicalEntries, prot_w), normal_entries.map(lambda x: x.pw).asUInt) & ~ptw_ae_array
        px_array = Cat(Fill(nPhysicalEntries, prot_x), normal_entries.map(lambda x: x.px).asUInt) & ~ptw_ae_array
        eff_array = Cat(Fill(nPhysicalEntries, prot_eff), normal_entries.map(lambda x: x.eff).asUInt)
        c_array = Cat(Fill(nPhysicalEntries, cacheable), normal_entries.map(lambda x: x.c).asUInt)
        ppp_array = Cat(Fill(nPhysicalEntries, prot_pp), normal_entries.map(lambda x: x.ppp).asUInt)
        paa_array = Cat(Fill(nPhysicalEntries, prot_aa), normal_entries.map(lambda x: x.paa).asUInt)
        pal_array = Cat(Fill(nPhysicalEntries, prot_al), normal_entries.map(lambda x: x.pal).asUInt)
        ppp_array_if_cached = ppp_array | c_array
        paa_array_if_cached = paa_array | Mux(usingAtomicsInCache, c_array, U(0))
        pal_array_if_cached = pal_array | Mux(usingAtomicsInCache, c_array, U(0))
        prefetchable_array = Cat((cacheable & homogeneous) << (nPhysicalEntries-1), normal_entries.map(lambda x: x.c).asUInt)

        misaligned = orR(io.req.bits.vaddr & (UIntToOH(len(io.req.bits)) - 1))

        if (not usingVM or (minPgLevels == pgLevels and vaddrBits == vaddrBitsExtended)):
            bad_va = Bool(False)
        else:
            nPgLevelChoices = pgLevels - minPgLevels + 1
            minVAddrBits = pgIdxBits + minPgLevels * pgLevelBits
            ret = 0
            for i in range(nPgLevelChoices):
                mask = (1 << vaddrBitsExtended) - (1 << (minVAddrBits + i * pgLevelBits - 1))
                maskedVAddr = io.req.bits.vaddr & mask
                ret |= (io.ptw.ptbr.additionalPgLevels == i and not (maskedVAddr == 0 or maskedVAddr == mask))
            bad_va = Bool(True) if ret == 1 else Bool(False)

        cmd_lrsc = Bool(usingAtomics) & io.req.bits.cmd.isOneOf(M_XLR, M_XSC)
        cmd_amo_logical = Bool(usingAtomics) & isAMOLogical(io.req.bits.cmd)
        cmd_amo_arithmetic = Bool(usingAtomics) & isAMOArithmetic(io.req.bits.cmd)
        cmd_put_partial = io.req.bits.cmd == M_PWR
        cmd_read = isRead(io.req.bits.cmd)
        cmd_write = isWrite(io.req.bits.cmd)
        cmd_write_perms = (cmd_write |
          io.req.bits.cmd.isOneOf(M_FLUSH_ALL, M_WOK)) # not a write, but needs write permissions

        lrscAllowed = Mux(Bool(usingDataScratchpad | usingAtomicsOnlyF|IO), U(0), c_array)
        ae_array = (
          Mux(misaligned, eff_array, U(0)) |
          Mux(cmd_lrsc, ~lrscAllowed, U(0)))
        ae_ld_array = Mux(cmd_read, ae_array | ~pr_array, U(0))
        ae_st_array = (
          Mux(cmd_write_perms, ae_array | ~pw_array, U(0)) |
          Mux(cmd_put_partial, ~ppp_array_if_cached, U(0)) |
          Mux(cmd_amo_logical, ~pal_array_if_cached, U(0)) |
          Mux(cmd_amo_arithmetic, ~paa_array_if_cached, U(0)))
        must_alloc_array = (
          Mux(cmd_put_partial, ~ppp_array, U(0)) |
          Mux(cmd_amo_logical, ~paa_array, U(0)) |
          Mux(cmd_amo_arithmetic, ~pal_array, U(0)) |
          Mux(cmd_lrsc, ~U(0)(pal_array.getWidth.W), U(0)))
        ma_ld_array = Mux(misaligned & cmd_read, ~eff_array, U(0))
        ma_st_array = Mux(misaligned & cmd_write, ~eff_array, U(0))
        pf_ld_array = Mux(cmd_read, ~(r_array | ptw_ae_array), U(0))
        pf_st_array = Mux(cmd_write_perms, ~(w_array | ptw_ae_array), U(0))
        pf_inst_array = ~(x_array | ptw_ae_array)

        tlb_hit = real_hits.orR
        tlb_miss = vm_enabled & ~bad_va & ~tlb_hit

        sectored_plru = SetAssocLRU(cfg.nSets, sectored_entries(0).size, "plru")
        superpage_plru = PseudoLRU(superpage_entries.size)
        with when(io.req.valid & vm_enabled):
            with when(sector_hits.orR): sectored_plru.access(memIdx, OHToUInt(sector_hits))
            with when(superpage_hits.orR): superpage_plru.access(OHToUInt(superpage_hits))

        # Superpages create the possibility that two entries in the TLB may match.
        # This corresponds to a software bug, but we can't return complete garbage;
        # we must return either the old translation or the new translation.  This
        # isn't compatible with the Mux1H approach.  So, flush the TLB and report
        # a miss on duplicate entries.
        multipleHits = PopCountAtLeast(real_hits, 2)

        io.req.ready <<= state == s_ready
        io.resp.pf.ld <<= (bad_va & cmd_read) | orR(pf_ld_array & hits)
        io.resp.pf.st <<= (bad_va & cmd_write_perms) | orR(pf_st_array & hits)
        io.resp.pf.inst <<= bad_va | orR(pf_inst_array & hits)
        io.resp.ae.ld <<= orR(ae_ld_array & hits)
        io.resp.ae.st <<= orR(ae_st_array & hits)
        io.resp.ae.inst <<= orR(~px_array & hits)
        io.resp.ma.ld <<= orR(ma_ld_array & hits)
        io.resp.ma.st <<= orR(ma_st_array & hits)
        io.resp.ma.inst <<= False # this is up to the pipeline to figure out
        io.resp.cacheable <<= orR(c_array & hits)
        io.resp.must_alloc <<= orR(must_alloc_array & hits)
        io.resp.prefetchable <<= orR(prefetchable_array & hits) & edge.manager.managers.forall(lambda m: not m.supportsAcquireB or m.supportsHint)
        io.resp.miss <<= do_refill or tlb_miss or multipleHits
        io.resp.paddr <<= Cat(ppn, io.req.bits.vaddr[pgIdxBits-1: 0])

        io.ptw.req.valid <<= state == s_request
        io.ptw.req.bits.valid <<= ~io.kill
        io.ptw.req.bits.bits.addr <<= r_refill_tag

        if (usingVM):
            sfence = io.sfence.valid
            with when (io.req.fire() & tlb_miss):
                state <<= s_request
                r_refill_tag <<= vpn
                r_superpage_repl_addr <<= replacementEntry(superpage_entries, superpage_plru.way)
                r_sectored_repl_addr <<= replacementEntry(sectored_entries(memIdx), sectored_plru.way(memIdx))
                r_sectored_hit_addr <<= OHToUInt(sector_hits)
                r_sectored_hit <<= orR(sector_hits)

            with when (state == s_request):
                with when (sfence): state <<= s_ready
                with when (io.ptw.req.ready): state <<= Mux(sfence, s_wait_invalidate, s_wait)
                with when (io.kill): state <<= s_ready

            with when (state == s_wait & sfence):
                state <<= s_wait_invalidate

            with when (io.ptw.resp.valid):
                state <<= s_ready

            with when (sfence):
                assert(~io.sfence.bits.rs1 or (io.sfence.bits.addr >> pgIdxBits) == vpn)
                for i in range(len(all_real_entries)):
                    with when (io.sfence.bits.rs1): all_real_entries[i].invalidateVPN(vpn)
                    with elsewhen (io.sfence.bits.rs2): all_real_entries[i].invalidateNonGlobal()
                    with otherwise(): all_real_entries[i].invalidate()

            with when (multipleHits or reset):
                all_real_entries.foreach(_.invalidate())

            ccover(io.ptw.req.fire(), "MISS", "TLB miss")
            ccover(io.ptw.req.valid & ~io.ptw.req.ready, "PTW_STALL", "TLB miss, but PTW busy")
            ccover(state == s_wait_invalidate, "SFENCE_DURING_REFILL", "flush TLB during TLB refill")
            ccover(sfence & ~io.sfence.bits.rs1 & ~io.sfence.bits.rs2, "SFENCE_ALL", "flush TLB")
            ccover(sfence & ~io.sfence.bits.rs1 & io.sfence.bits.rs2, "SFENCE_ASID", "flush TLB ASID")
            ccover(sfence & io.sfence.bits.rs1 & ~io.sfence.bits.rs2, "SFENCE_LINE", "flush TLB line")
            ccover(sfence & io.sfence.bits.rs1 & io.sfence.bits.rs2, "SFENCE_LINE_ASID", "flush TLB line/ASID")
            ccover(multipleHits, "MULTIPLE_HITS", "Two matching translations in TLB")

        def ccover(cond: Bool, label: String, desc: String): # (implicit sourceInfo: SourceInfo):
            cover(cond, f"{{if (instruction) 'I' else 'D'}}TLB_{label}", "MemorySystem;;" + desc)

        def replacementEntry(set: Seq[TLBEntry], alt: U):
            valids = set.map(lambda x: orR(x.valid)).asUInt
            Mux(valids.andR, alt, PriorityEncoder(~valids))

    return clsTLB()
    

if __name__ == "__main__":
    cfg = TLBConfig(4, 4, 4, 4)
    Emitter.dump(Emitter.emit(TLB(True, lgMaxSize, cfg, None, None)), "{__file__}.fir")
    # e = TLBEntry(32, False, False)
