from tile import CoreModule, CoreBundle
from util.common import *


class SFenceReq(CoreBundle):
    def __init__(self, p, **kwargs):
        CoreBundle.__init__(self, p, **kwargs)
        self.rs1 = Bool(True)
        self.rs2 = Bool(True)
        self.addr = U.w(vaddrBits)(0)
        self.asid = U.w(max(1, asIdBits))(0)


class TLBReq(CoreBundle):
    def __init__(self, lgMaxSize, p, **kwargs):
        CoreBundle.__init__(self, p, **kwargs)
        self.vaddr = U.w(vaddrBitsExtended)(0)
        self.passthrough = Bool(True)
        self.size = U.w(log2Ceil(lgMaxSize + 1))(0)
        self.cmd  = U.w(M_SZ)(0) # we have not bits
        

class TLBExceptions(Bundle):
    def __init__(self, **kwargs):
        Bundle.__init__(self, **kwargs)
        self.ld = Bool()
        self.st = Bool()
        self.inst = Bool()


class TLBResp(CoreBundle):
    def __init__(self, p, **kwargs):
        CoreBundle.__init__(self, p, **kwargs)
        self.miss = Bool()
        self.paddr = U.w(paddrBits)
        self.pf = TLBExceptions()
        self.ae = TLBExceptions()
        self.ma = TLBExceptions()
        self.cacheable = Bool()
        self.must_alloc = Bool()
        self.prefetchable = Bool()
        

class TLBEntryData(CoreBundle):
    def __init__(self, p, **kwargs):
        CoreBundle.__init__(self, p, **kwargs)
        self.ppn = U.w(ppnBits)
        self.u = Bool()
        self.g = Bool()
        self.ae = Bool()
        self.sw = Bool()
        self.sx = Bool()
        self.sr = Bool()
        self.pw = Bool()
        self.px = Bool()
        self.pr = Bool()
        self.ppp = Bool() # PutPartial
        self.pal = Bool() # AMO logical
        self.paa = Bool() # AMO arithmetic
        self.eff = Bool() # get/put effects
        self.c = Bool()
        self.fragmented_superpage = Bool()



class TLBEntry(CoreBundle):

    def __init__(self, nSectors: int, superpage: bool, superpageOnly: bool, p: Paramters, **kwargs):
        assert(nSectors == 1 or not superpage) # replace require by assert
        assert(not superpageOnly or superpage)

        CoreBundle.__init__(self, p, **kwargs)

        self.nSectors = nSectors
        self.superpage = superpage
        self.superpageOnly = superpageOnly

        self.level = U.w(log2Ceil(pgLevels))
        self.tag = U.w(vpnBits)
        self.data = Vec(nSectors, U(TLBEntryData.getWidth())) # impl getWidth
        self.valid = Vec(nSectors, Bool())
        self.entry_data = map(asTypeOf(TLBEntryData), self.data) # impl asTypeOf

    def sectorIdx(self, vpn: U):
        return vpn[log2(self.nSectors)-1, 0]

    def getData(self, vpn: U):
        return OptimizationBarrier(self.data[self.sectorIdx(vpn)].asTypeOf(TLBEntryData)) # impl asTypeOf
    def sectorHit(self, vpn: U):
        return self.valid.orR && self.sectorTagMatch(vpn)

    def sectorTagMatch(self, vpn: U):
        return ((self.tag ^ vpn) >> log2(self.nSectors)) == 0

    def hit(self, vpn: U):
        if self.superpage and usingVM:
            tagMatch = self.valid.head # impl head
            for j in range(pgLevels):
                base = vpnBits - (j + 1) * pgLevelBits
                ignore = self.level < j or self.superpageOnly and j == pgLevels - 1
                tagMatch = tagMatch and (ignore or self.tag[base + pgLevelBits - 1, base] == vpn[base + pgLevelBits - 1, base])
            return tagMatch
        idx = self.sectorIdx(vpn)
        return self.valid[idx] and self.sectorTagMatch(vpn)

    def ppn(self, vpn: U):
        data = self.getData(vpn)
        if self.superpage and usingVM:
            res = self.data.ppn >> pgLevelBits*(pgLevels - 1) # data.ppn ?
            for j in range(pgLevels):
                ignore = level < j or self.superpageOnly and j == pgLevels - 1
                res = Cat(res, (Mux(ignore, vpn, U(0)) | data.ppn)(vpnBits - j*pgLevelBits - 1, vpnBits - (j + 1)*pgLevelBits))
            return res
        return data.ppn

    def insert(self, tag: U, level: U, entry: TLBEntryData) -> Unit:
        self.tag = tag
        self.level = level[log2Ceil(pgLevels - self.superpageOnly.toInt)-1, 0]
        val idx = sectorIdx(tag)
        self.valid[idx] = True
        self.data[idx] = entry.asUInt

    def invalidate(self) -> Unit:
        for i in range(self.valid.size()):
            self.valid[i] = False

    def invalidateVPN(self, vpn: U) -> Unit: 
        if self.superpage:
            with when (self.hit(vpn)): self.invalidate()
        else:
            with when (self.sectorTagMatch(vpn)):
                self.valid[self.sectorIdx(vpn)] = False

            # For fragmented self.superpage mappings, we assume the worst (largest)
            # case, and zap entries whose most-significant VPNs match
            with when (((self.tag ^ vpn) >> (pgLevelBits * (pgLevels - 1))) == 0):
                for i in range(self.entry_data.size()):
                    with when(not self.entry_data[i].fragmented_superpage):
                        self.valid[i] = False

    def invalidateNonGlobal(self) -> Unit:
        for i in range(self.entry_data.size()):
            with when(not self.entry_data[i].g):
                self.valid[i] = False


class TLBConfig:
    def __init__(self, nSets: int, nWays: int, nSectors: int = 4, nSuperpageEntries: int = 4):
        self.nSets = nSets
        self.nWays = nWays
        self.nSectors = nSectors
        self.nSuperpageEntries = nSuperpageEntries


def TLB(instruction: bool, lgMaxSize: int, cfg: TLBConfig, edge: TLEdgeOut, p: Parameters):

    class clsTLB(CoreModule):
        # use IO replace Bundle
        io = IO {
            req=Decoupled(TLBReq(lgMaxSize)).flip # ?
            resp=Output(TLBResp())
            sfence=Input(Valid(SFenceReq()))
            ptw=TLBPTWIO
            kill=Bool(INPUT) # suppress a TLB refill, one cycle after a miss
        }

        pageGranularityPMPs = pmpGranularity >= (1 << pgIdxBits)
        vpn = io.req.bits.vaddr[vaddrBits-1, pgIdxBits]
        memIdx = vpn[log2(cfg.nSectors) + log2(cfg.nSets) - 1, log2(cfg.nSectors)]
        sectored_entries = Reg(VecInit(cfg.nSets, VecInit(cfg.nWays / cfg.nSectors, TLBEntry(cfg.nSectors, False, False))))
        superpage_entries = Reg(VecInit(cfg.nSuperpageEntries, TLBEntry(1, True, True)))
        special_entry = (not pageGranularityPMPs).option(RegInit(TLBEntry(1, True, False))) # .option?


        ordinary_entries = sectored_entries[memIdx] + superpage_entries
        all_entries = ordinary_entries + special_entry
        all_real_entries = sectored_entries.flatten + superpage_entries + special_entry

        # how to compare U?
        s_ready = U(1)
        s_request = U(2)
        s_wait = U(3)
        s_wait_invalidate = U(4)

        state = RegInit(s_ready)
        r_refill_tag = Reg(U.w(vpnBits))
        r_superpage_repl_addr = Reg(U.w(log2Ceil(superpage_entries.size())))
        r_sectored_repl_addr = Reg(U.w(log2Ceil(sectored_entries[0].size())))
        r_sectored_hit_addr = Reg(U.w(log2Ceil(sectored_entries[0].size())))
        r_sectored_hit = Reg(Bool)

        priv = io.ptw.status.prv if instruction else io.ptw.status.dprv
        priv_s = priv[0]
        priv_uses_vm = priv <= PRV.S
        vm_enabled = Bool(usingVM) and io.ptw.ptbr.mode(io.ptw.ptbr.mode.getWidth-1) and priv_uses_vm and not io.req.bits.passthrough

        # share a single physical memory attribute checker (unshare if critical path)
        refill_ppn = io.ptw.resp.bits.pte.ppn(ppnBits-1, 0)
        do_refill = Bool(usingVM) and io.ptw.resp.valid
        invalidate_refill = state.isOneOf(s_request, s_wait_invalidate) or io.sfence.valid
        mpu_ppn = Mux(do_refill, refill_ppn,
                      Mux(vm_enabled and special_entry.nonEmpty, special_entry.map(_.ppn(vpn)).getOrElse(U(0)), io.req.bits.vaddr >> pgIdxBits))
        mpu_physaddr = Cat(mpu_ppn, io.req.bits.vaddr(pgIdxBits-1, 0))
        mpu_priv = Mux[UInt](Bool(usingVM) and (do_refill or io.req.bits.passthrough), PRV.S, Cat(io.ptw.status.debug, priv))
        pmp = Module(PMPChecker(lgMaxSize))
        pmp.io.addr = mpu_physaddr
        pmp.io.size = io.req.bits.size
        pmp.io.pmp = (io.ptw.pmp: Seq[PMP])
        pmp.io.prv = mpu_priv
        legal_address = edge.manager.findSafe(mpu_physaddr).reduce(_or_)

        def fastCheck(member):
            legal_address and edge.manager.fastProperty(mpu_physaddr, member, (b:Boolean) => Bool(b))

        cacheable = fastCheck(_.supportsAcquireT) and (instruction or not usingDataScratchpad)
        homogeneous = TLBPageLookup(edge.manager.managers, xLen, p(CacheBlockBytes), BigInt(1) << pgIdxBits)(mpu_physaddr).homogeneous
        deny_access_to_debug = mpu_priv <= PRV.M and p(DebugModuleKey).map(dmp => dmp.address.contains(mpu_physaddr)).getOrElse(False)
        prot_r = fastCheck(_.supportsGet) and not deny_access_to_debug and pmp.io.r
        prot_w = fastCheck(_.supportsPutFull) and not deny_access_to_debug and pmp.io.w
        prot_pp = fastCheck(_.supportsPutPartial)
        prot_al = fastCheck(_.supportsLogical)
        prot_aa = fastCheck(_.supportsArithmetic)
        prot_x = fastCheck(_.executable) and not deny_access_to_debug and pmp.io.x
        prot_eff = fastCheck(Seq(RegionType.PUT_EFFECTS, RegionType.GET_EFFECTS) contains _.regionType)

        sector_hits = sectored_entries(memIdx).map(_.sectorHit(vpn))
        superpage_hits = superpage_entries.map(_.hit(vpn))
        hitsVec = all_entries.map(vm_enabled and _.hit(vpn))
        real_hits = hitsVec.asUInt
        hits = Cat(not vm_enabled, real_hits)
        ppn = Mux1H(hitsVec :+ not vm_enabled, all_entries.map(_.ppn(vpn)) :+ vpn(ppnBits-1, 0))

        # permission bit arrays
        with when(do_refill):
            pte = io.ptw.resp.bits.pte
            newEntry = Wire(TLBEntryData)
            newEntry.ppn = pte.ppn
            newEntry.c = cacheable
            newEntry.u = pte.u
            newEntry.g = pte.g and pte.v
            newEntry.ae = io.ptw.resp.bits.ae
            newEntry.sr = pte.sr()
            newEntry.sw = pte.sw()
            newEntry.sx = pte.sx()
            newEntry.pr = prot_r
            newEntry.pw = prot_w
            newEntry.px = prot_x
            newEntry.ppp = prot_pp
            newEntry.pal = prot_al
            newEntry.paa = prot_aa
            newEntry.eff = prot_eff
            newEntry.fragmented_superpage = io.ptw.resp.bits.fragmented_superpage

            with when(special_entry.nonEmpty and not io.ptw.resp.bits.homogeneous):
                for i in range(special_entry.size()):
                    special_entry[i].insert(
                            r_refill_tag, io.ptw.resp.bits.level, newEntry)
                    with when(invalidate_refill):
                        special_entry[i].invalidate()
            with elsewhen(io.ptw.resp.bits.level < pgLevels-1):
                for i in range(superpage_entries.size()):
                    with when(r_superpage_repl_addr == i):
                        superpage_entries[i].insert(r_refill_tag, io.ptw.resp.bits.level, newEntry)
                    with when(invalidate_refill): 
                        superpage_entries[i].invalidate()
            with otherwise():
                r_memIdx = r_refill_tag[log2(cfg.nSectors) + log2(cfg.nSets) - 1, log2(cfg.nSectors)]
                waddr = Mux(r_sectored_hit, r_sectored_hit_addr, r_sectored_repl_addr)
                for i in range(sectored_entries[r_memIdx].size()):
                    with when(waddr == i):
                        with when(not r_sectored_hit):
                            e.invalidate()
                    sectored_entries[r_memIdx][i].insert(r_refill_tag, U(0), newEntry)
                    with when(invalidate_refill):
                        sectored_entries[r_memIdx][i].invalidate()


        entries = all_entries.map(lambda x: x.getData(vpn))
        normal_entries = ordinary_entries.map(lambda x: x.getData(vpn))
        nPhysicalEntries = 1 + special_entry.size()
        ptw_ae_array = Cat(Bool(False), entries.map(lambda x: x.ae).asUInt)
        priv_rw_ok = Mux(not priv_s or io.ptw.status.sum, entries.map(lambda x: x.u).asUInt, U(0)) | Mux(priv_s, ~entries.map(lambda x: x.u).asUInt, U(0))
        priv_x_ok = Mux(priv_s, ~entries.map(lambda x: x.u).asUInt, entries.map(lambda x: x.u).asUInt)
        r_array = Cat(Bool(True), priv_rw_ok & (entries.map(lambda x: x.sr).asUInt | Mux(io.ptw.status.mxr, entries.map(lambda x: x.sx).asUInt, UInt(0))))
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
        prefetchable_array = Cat((cacheable and homogeneous) << (nPhysicalEntries-1), normal_entries.map(lambda x: x.c).asUInt)

        misaligned = (io.req.bits.vaddr & (UIntToOH(io.req.bits.size()) - 1)).orR

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

        cmd_lrsc = Bool(usingAtomics) and io.req.bits.cmd.isOneOf(M_XLR, M_XSC)
        cmd_amo_logical = Bool(usingAtomics) and isAMOLogical(io.req.bits.cmd)
        cmd_amo_arithmetic = Bool(usingAtomics) and isAMOArithmetic(io.req.bits.cmd)
        cmd_put_partial = io.req.bits.cmd == M_PWR
        cmd_read = isRead(io.req.bits.cmd)
        cmd_write = isWrite(io.req.bits.cmd)
        cmd_write_perms = cmd_write or
          io.req.bits.cmd.isOneOf(M_FLUSH_ALL, M_WOK) # not a write, but needs write permissions

        lrscAllowed = Mux(Bool(usingDataScratchpad or usingAtomicsOnlyForIO), U(0), c_array)
        ae_array =
          Mux(misaligned, eff_array, U(0)) |
          Mux(cmd_lrsc, ~lrscAllowed, U(0))
        ae_ld_array = Mux(cmd_read, ae_array | ~pr_array, U(0))
        ae_st_array =
          Mux(cmd_write_perms, ae_array | ~pw_array, U(0)) |
          Mux(cmd_put_partial, ~ppp_array_if_cached, U(0)) |
          Mux(cmd_amo_logical, ~pal_array_if_cached, U(0)) |
          Mux(cmd_amo_arithmetic, ~paa_array_if_cached, U(0))
        must_alloc_array =
          Mux(cmd_put_partial, ~ppp_array, U(0)) |
          Mux(cmd_amo_logical, ~paa_array, U(0)) |
          Mux(cmd_amo_arithmetic, ~pal_array, U(0)) |
          Mux(cmd_lrsc, ~U(0)(pal_array.getWidth.W), U(0))
        ma_ld_array = Mux(misaligned and cmd_read, ~eff_array, U(0))
        ma_st_array = Mux(misaligned and cmd_write, ~eff_array, U(0))
        pf_ld_array = Mux(cmd_read, ~(r_array | ptw_ae_array), U(0))
        pf_st_array = Mux(cmd_write_perms, ~(w_array | ptw_ae_array), U(0))
        pf_inst_array = ~(x_array | ptw_ae_array)

        tlb_hit = real_hits.orR
        tlb_miss = vm_enabled and not bad_va and not tlb_hit

        sectored_plru = SetAssocLRU(cfg.nSets, sectored_entries(0).size, "plru")
        superpage_plru = PseudoLRU(superpage_entries.size)
        with when(io.req.valid and vm_enabled):
            with when(sector_hits.orR): sectored_plru.access(memIdx, OHToUInt(sector_hits))
            with when(superpage_hits.orR): superpage_plru.access(OHToUInt(superpage_hits))

        # Superpages create the possibility that two entries in the TLB may match.
        # This corresponds to a software bug, but we can't return complete garbage;
        # we must return either the old translation or the new translation.  This
        # isn't compatible with the Mux1H approach.  So, flush the TLB and report
        # a miss on duplicate entries.
        multipleHits = PopCountAtLeast(real_hits, 2)

        io.req.ready = state == s_ready
        io.resp.pf.ld = (bad_va and cmd_read) or (pf_ld_array & hits).orR
        io.resp.pf.st = (bad_va and cmd_write_perms) or (pf_st_array & hits).orR
        io.resp.pf.inst = bad_va or (pf_inst_array & hits).orR
        io.resp.ae.ld = (ae_ld_array & hits).orR
        io.resp.ae.st = (ae_st_array & hits).orR
        io.resp.ae.inst = (~px_array & hits).orR
        io.resp.ma.ld = (ma_ld_array & hits).orR
        io.resp.ma.st = (ma_st_array & hits).orR
        io.resp.ma.inst = False // this is up to the pipeline to figure out
        io.resp.cacheable = (c_array & hits).orR
        io.resp.must_alloc = (must_alloc_array & hits).orR
        io.resp.prefetchable = (prefetchable_array & hits).orR and edge.manager.managers.forall(m => not m.supportsAcquireB or m.supportsHint)
        io.resp.miss = do_refill or tlb_miss or multipleHits
        io.resp.paddr = Cat(ppn, io.req.bits.vaddr(pgIdxBits-1, 0))

        io.ptw.req.valid = state == s_request
        io.ptw.req.bits.valid = not io.kill
        io.ptw.req.bits.bits.addr = r_refill_tag

        if (usingVM):
            sfence = io.sfence.valid
            with when (io.req.fire() and tlb_miss):
                state = s_request
                r_refill_tag = vpn
                r_superpage_repl_addr = replacementEntry(superpage_entries, superpage_plru.way)
                r_sectored_repl_addr = replacementEntry(sectored_entries(memIdx), sectored_plru.way(memIdx))
                r_sectored_hit_addr = OHToUInt(sector_hits)
                r_sectored_hit = sector_hits.orR

            with when (state == s_request):
                with when (sfence): state = s_ready
                with when (io.ptw.req.ready): state = Mux(sfence, s_wait_invalidate, s_wait)
                with when (io.kill): state = s_ready

            with when (state == s_wait and sfence):
                state = s_wait_invalidate

            with when (io.ptw.resp.valid):
                state = s_ready

            with when (sfence):
                assert(not io.sfence.bits.rs1 or (io.sfence.bits.addr >> pgIdxBits) == vpn)
                for i in range(all_real_entries.size()):
                    with when (io.sfence.bits.rs1): all_real_entries[i].invalidateVPN(vpn)
                    with elsewhen (io.sfence.bits.rs2): all_real_entries[i].invalidateNonGlobal()
                    with otherwise(): all_real_entries[i].invalidate()

            with when (multipleHits or reset):
                all_real_entries.foreach(_.invalidate())

            ccover(io.ptw.req.fire(), "MISS", "TLB miss")
            ccover(io.ptw.req.valid and not io.ptw.req.ready, "PTW_STALL", "TLB miss, but PTW busy")
            ccover(state == s_wait_invalidate, "SFENCE_DURING_REFILL", "flush TLB during TLB refill")
            ccover(sfence and not io.sfence.bits.rs1 and not io.sfence.bits.rs2, "SFENCE_ALL", "flush TLB")
            ccover(sfence and not io.sfence.bits.rs1 and io.sfence.bits.rs2, "SFENCE_ASID", "flush TLB ASID")
            ccover(sfence and io.sfence.bits.rs1 and not io.sfence.bits.rs2, "SFENCE_LINE", "flush TLB line")
            ccover(sfence and io.sfence.bits.rs1 and io.sfence.bits.rs2, "SFENCE_LINE_ASID", "flush TLB line/ASID")
            ccover(multipleHits, "MULTIPLE_HITS", "Two matching translations in TLB")

        def ccover(cond: Bool, label: String, desc: String)(implicit sourceInfo: SourceInfo):
            cover(cond, s"${if (instruction) "I" else "D"}TLB_$label", "MemorySystem;;" + desc)

        def replacementEntry(set: Seq[TLBEntry], alt: UInt):
            valids = set.map(_.valid.orR).asUInt
            Mux(valids.andR, alt, PriorityEncoder(~valids))

    return clsTLB
    
