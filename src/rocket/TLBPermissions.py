class TLBPageLookup:
    class TLBFixedPermissions
        def __init__(self, 
                     e: Bool, # get-/put-effects
                     r: Bool, # readable
                     w: Bool, # writeable
                     x: Bool, # executable
                     c: Bool, # cacheable
                     a: Bool, # arithmetic ops
                     l: Bool):
            # logical ops
            self.e = e
            self.r = r
            self.w = w
            self.x = x
            self.c = c
            self.a = a
            self.l = l
            self.useful = r or w or x or c or a or l

    @staticmethod
    def groupRegions(managers: Seq[TLManagerParameters]) -> Map[TLBFixedPermissions, Seq[AddressSet]]:
        permissions = map(
            lambda m: (m.address, TLBFixedPermissions(
            e = Seq(RegionType.PUT_EFFECTS, RegionType.GET_EFFECTS) contains m.regionType,
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
    def apply(managers: Seq[TLManagerParameters], xLen: Int, cacheBlockBytes: Int, pageSize: BigInt):
        assert (isPow2(xLen) and xLen >= 8)
        assert (isPow2(cacheBlockBytes) and cacheBlockBytes >= xLen/8)
        assert (isPow2(pageSize) and pageSize >= cacheBlockBytes)

        xferSizes = TransferSizes(cacheBlockBytes, cacheBlockBytes)
        allSizes = TransferSizes(1, cacheBlockBytes)
        amoSizes = TransferSizes(4, xLen/8)

        permissions = managers.foreach { m =>
        require (not m.supportsGet        or m.supportsGet       .contains(allSizes),  s"Memory region '${m.name}' at ${m.address} only supports ${m.supportsGet} Get, but must support ${allSizes}")
        require (not m.supportsPutFull    or m.supportsPutFull   .contains(allSizes),  s"Memory region '${m.name}' at ${m.address} only supports ${m.supportsPutFull} PutFull, but must support ${allSizes}")
        require (not m.supportsPutPartial or m.supportsPutPartial.contains(allSizes),  s"Memory region '${m.name}' at ${m.address} only supports ${m.supportsPutPartial} PutPartial, but must support ${allSizes}")
        require (not m.supportsAcquireB   or m.supportsAcquireB  .contains(xferSizes), s"Memory region '${m.name}' at ${m.address} only supports ${m.supportsAcquireB} AcquireB, but must support ${xferSizes}")
        require (not m.supportsAcquireT   or m.supportsAcquireT  .contains(xferSizes), s"Memory region '${m.name}' at ${m.address} only supports ${m.supportsAcquireT} AcquireT, but must support ${xferSizes}")
        require (not m.supportsLogical    or m.supportsLogical   .contains(amoSizes),  s"Memory region '${m.name}' at ${m.address} only supports ${m.supportsLogical} Logical, but must support ${amoSizes}")
        require (not m.supportsArithmetic or m.supportsArithmetic.contains(amoSizes),  s"Memory region '${m.name}' at ${m.address} only supports ${m.supportsArithmetic} Arithmetic, but must support ${amoSizes}")
      }

        grouped = mapValues(TLBPageLookup.groupRegions(managers), 
                lambda l: filter(lambda x: x.alignment >= pageSize, l)) # discard any region that's not big enough

        def lowCostProperty(prop):
            (yesm, nom) = grouped.partition { case (k, eq) => prop(k) }
            (yes, no) = (yesm.values.flatten.toList, nom.values.flatten.toList)
            # Find the minimal bits needed to distinguish between yes and no
            decisionMask = AddressDecoder(Seq(yes, no))
            simplify = lambda x: AddressSet.unify(x.map(lambda x: x.widen(~decisionMask)).distinct)
            (yesf, nof) = (simplify(yes), simplify(no))
            if (yesf.size < no.size):
                (x: UInt) => yesf.map(lambda x: x.contains(x)).foldLeft(false.B)(_ or _)
            else:
                (x: UInt) => not nof.map(lambda x: x.contains(x)).foldLeft(false.B)(_ or _)

        # Derive simplified property circuits (don't care when not homo)
        rfn = lowCostProperty(lambda x: x.r)
        wfn = lowCostProperty(lambda x: x.w)
        xfn = lowCostProperty(lambda x: x.x)
        cfn = lowCostProperty(lambda x: x.c)
        afn = lowCostProperty(lambda x: x.a)
        lfn = lowCostProperty(lambda x: x.l)

        homo = AddressSet.unify(grouped.values.flatten.toList)
        (x: UInt) => TLBPermissions(
          homogeneous = homo.map(lambda x: x.contains(x)).foldLeft(false.B)(_ or _),
          r = rfn(x),
          w = wfn(x),
          x = xfn(x),
          c = cfn(x),
          a = afn(x),
          l = lfn(x))

    # Are all pageSize intervals of mapped regions homogeneous?
    @staticmethod
    def homogeneous(managers: Seq[TLManagerParameters], pageSize: BigInt) -> Bool:
        TLBPageLookup.groupRegions(managers).values.forall(lambda x: x.forall(lambda x: x.alignment >= pageSize))
