circuit clsSimpleHellaCacheIF :
  module clsQueue :
    input clock : Clock
    input reset : UInt<1>
    output io : {flip enq : {flip ready : UInt<1>, valid : UInt<1>, bits : UInt<1>}, deq : {flip ready : UInt<1>, valid : UInt<1>, bits : UInt<1>}, count : UInt<2>}
  
    wire do_enq : UInt<1>
    node _T = and(io.enq.valid, io.enq.ready)
    do_enq <= _T
    wire do_deq : UInt<1>
    node _T_1 = and(io.deq.valid, io.deq.ready)
    do_deq <= _T_1
    cmem ram : UInt<1>[2]
    reg _T_2 : UInt<1>, clock with : 
      reset => (reset, UInt<1>("h0"))
    when do_enq :
      write mport _T_3 = ram[_T_2], clock
      _T_3 <= io.enq.bits
      node _T_4 = add(_T_2, UInt<1>("h1"))
      _T_2 <= _T_4
    reg _T_5 : UInt<1>, clock with : 
      reset => (reset, UInt<1>("h0"))
    when do_deq :
      node _T_6 = add(_T_5, UInt<1>("h1"))
      _T_5 <= _T_6
    node _T_7 = neq(do_enq, do_deq)
    reg maybe_full : UInt<1>, clock with : 
      reset => (reset, UInt<1>("h0"))
    when _T_7 :
      maybe_full <= do_enq
    node ptr_match = eq(_T_2, _T_5)
    node _T_8 = not(maybe_full)
    node empty = and(ptr_match, _T_8)
    node _T_9 = not(empty)
    io.deq.valid <= _T_9
    node full = and(ptr_match, maybe_full)
    node _T_10 = not(full)
    io.enq.ready <= _T_10
    read mport _T_11 = ram[_T_5], clock
    io.deq.bits <= _T_11
    node _T_13 = and(maybe_full, ptr_match)
    node _T_12 = mux(_T_13, UInt<2>("h2"), UInt<1>("h0"))
    node ptr_diff = sub(_T_2, _T_5)
    node _T_14 = or(_T_12, ptr_diff)
    io.count <= _T_14

  module clsSimpleHellaCacheIFReplayQueue :
    input clock : Clock
    input reset : UInt<1>
    output io : {flip req : {flip ready : UInt<1>, valid : UInt<1>, bits : {phys : UInt<1>, no_alloc : UInt<1>, no_xcpt : UInt<1>, addr : UInt<32>, tag : UInt<19>, cmd : UInt<16>, _size : UInt<2>, signed : UInt<1>, dprv : UInt<2>, data : UInt<32>, mask : UInt<4>}}, flip nack : {valid : UInt<1>, bits : UInt<16>}, flip resp : {valid : UInt<1>, bits : {data : UInt<32>, mask : UInt<4>, addr : UInt<32>, tag : UInt<19>, cmd : UInt<16>, _size : UInt<2>, signed : UInt<1>, dprv : UInt<2>, replay : UInt<1>, has_data : UInt<1>, data_word_bypass : UInt<32>, data_raw : UInt<32>, store_data : UInt<32>}}, replay : {flip ready : UInt<1>, valid : UInt<1>, bits : {phys : UInt<1>, no_alloc : UInt<1>, no_xcpt : UInt<1>, addr : UInt<32>, tag : UInt<19>, cmd : UInt<16>, _size : UInt<2>, signed : UInt<1>, dprv : UInt<2>, data : UInt<32>, mask : UInt<4>}}}
  
    inst nackq of clsQueue
    nackq.clock <= clock
    nackq.reset <= reset
    node _T = and(io.nack.valid, nackq.io.deq.valid)
    reg reqs : {phys : UInt<1>, no_alloc : UInt<1>, no_xcpt : UInt<1>, addr : UInt<32>, tag : UInt<19>, cmd : UInt<16>, _size : UInt<2>, signed : UInt<1>, dprv : UInt<2>, data : UInt<32>, mask : UInt<4>}[2], clock
    node _T_1 = eq(io.nack.bits, reqs[nackq.io.deq.bits].tag)
    node nack_head = and(_T, _T_1)
    node _T_2 = not(nack_head)
    node _T_3 = and(io.nack.valid, _T_2)
    nackq.io.enq.valid <= _T_3
    node _T_4 = eq(reqs[1].tag, io.nack.bits)
    node _T_5 = eq(reqs[0].tag, io.nack.bits)
    node _T_6 = cat(_T_4, _T_5)
    reg inflight : UInt<2>, clock with : 
      reset => (reset, UInt<2>("h0"))
    node nack_onehot = and(_T_6, inflight)
    node _T_7 = bits(nack_onehot, 1, 1)
    nackq.io.enq.bits <= _T_7
    reg replaying : UInt<1>, clock with : 
      reset => (reset, UInt<1>("h0"))
    node _T_8 = and(io.resp.valid, replaying)
    node _T_9 = eq(io.resp.bits.tag, reqs[nackq.io.deq.bits].tag)
    node replay_complete = and(_T_8, _T_9)
    nackq.io.deq.ready <= replay_complete
    node _T_11 = and(io.req.valid, io.req.ready)
    node _T_12 = not(inflight)
    node _T_13 = bits(_T_12, 0, 0)
    node _T_15 = bits(_T_12, 1, 1)
    node _T_14 = mux(_T_15, UInt<2>("h2"), UInt<3>("h0"))
    node next_inflight_onehot = mux(_T_13, UInt<1>("h1"), _T_14)
    node _T_10 = mux(_T_11, next_inflight_onehot, UInt<1>("h0"))
    node _T_16 = or(inflight, _T_10)
    node _T_18 = eq(reqs[1].tag, io.resp.bits.tag)
    node _T_19 = eq(reqs[0].tag, io.resp.bits.tag)
    node _T_20 = cat(_T_18, _T_19)
    node resp_onehot = and(_T_20, inflight)
    node _T_17 = mux(io.resp.valid, resp_onehot, UInt<1>("h0"))
    node _T_21 = not(_T_17)
    node _T_22 = and(_T_16, _T_21)
    inflight <= _T_22
    node _T_23 = and(io.req.valid, io.req.ready)
    node _T_24 = bits(next_inflight_onehot, 2, 2)
    node _T_25 = orr(_T_24)
    node _T_26 = bits(next_inflight_onehot, 1, 0)
    node _T_27 = or(_T_24, _T_26)
    node _T_28 = bits(_T_27, 1, 1)
    node next_inflight = cat(_T_25, _T_28)
    when _T_23 :
      reqs[next_inflight] <= io.req.bits
    node _T_29 = and(io.replay.valid, io.replay.ready)
    when _T_29 :
      replaying <= UInt<1>("h1")
    node _T_30 = or(nack_head, replay_complete)
    when _T_30 :
      replaying <= UInt<1>("h0")

  module clsArbiter :
    input clock : Clock
    input reset : UInt<1>
    output io : {flip _in : {flip ready : UInt<1>, valid : UInt<1>, bits : {phys : UInt<1>, no_alloc : UInt<1>, no_xcpt : UInt<1>, addr : UInt<32>, tag : UInt<19>, cmd : UInt<16>, _size : UInt<2>, signed : UInt<1>, dprv : UInt<2>, data : UInt<32>, mask : UInt<4>}}[2], out : {flip ready : UInt<1>, valid : UInt<1>, bits : {phys : UInt<1>, no_alloc : UInt<1>, no_xcpt : UInt<1>, addr : UInt<32>, tag : UInt<19>, cmd : UInt<16>, _size : UInt<2>, signed : UInt<1>, dprv : UInt<2>, data : UInt<32>, mask : UInt<4>}}, chosen : UInt<1>}
  
    io.chosen <= UInt<1>("h1")
    io.out.bits.signed <= io._in[1].bits.signed
    io.out.bits._size <= io._in[1].bits._size
    io.out.bits.no_xcpt <= io._in[1].bits.no_xcpt
    io.out.bits.cmd <= io._in[1].bits.cmd
    io.out.bits.phys <= io._in[1].bits.phys
    io.out.bits.dprv <= io._in[1].bits.dprv
    io.out.bits.no_alloc <= io._in[1].bits.no_alloc
    io.out.bits.tag <= io._in[1].bits.tag
    io.out.bits.addr <= io._in[1].bits.addr
    io.out.bits.data <= io._in[1].bits.data
    io.out.bits.mask <= io._in[1].bits.mask
    when io._in[0].valid :
      io.chosen <= UInt<1>("h0")
      io.out.bits.signed <= io._in[0].bits.signed
      io.out.bits._size <= io._in[0].bits._size
      io.out.bits.no_xcpt <= io._in[0].bits.no_xcpt
      io.out.bits.cmd <= io._in[0].bits.cmd
      io.out.bits.phys <= io._in[0].bits.phys
      io.out.bits.dprv <= io._in[0].bits.dprv
      io.out.bits.no_alloc <= io._in[0].bits.no_alloc
      io.out.bits.tag <= io._in[0].bits.tag
      io.out.bits.addr <= io._in[0].bits.addr
      io.out.bits.data <= io._in[0].bits.data
      io.out.bits.mask <= io._in[0].bits.mask
    node _T = and(UInt<1>("h1"), io.out.ready)
    io._in[0].ready <= _T
    node g = eq(io._in[0].valid, UInt<1>("h0"))
    node _T_1 = and(g, io.out.ready)
    io._in[1].ready <= _T_1
    node _T_2 = eq(g, UInt<1>("h0"))
    node _T_3 = or(_T_2, io._in[1].valid)
    io.out.valid <= _T_3

  module clsSimpleHellaCacheIF :
    input clock : Clock
    input reset : UInt<1>
    output io : {flip requestor : {req : {flip ready : UInt<1>, valid : UInt<1>, bits : {phys : UInt<1>, no_alloc : UInt<1>, no_xcpt : UInt<1>, addr : UInt<32>, tag : UInt<19>, cmd : UInt<16>, _size : UInt<2>, signed : UInt<1>, dprv : UInt<2>, data : UInt<32>, mask : UInt<4>}}, s1_kill : UInt<1>, s1_data : {}, s2_nack : UInt<1>, s2_nack_cause_raw : UInt<1>, s2_kill : UInt<1>, s2_uncached : UInt<1>, s2_paddr : UInt<6>("h20"), resp : {valid : UInt<1>, bits : {data : UInt<32>, mask : UInt<4>, addr : UInt<32>, tag : UInt<19>, cmd : UInt<16>, _size : UInt<2>, signed : UInt<1>, dprv : UInt<2>, replay : UInt<1>, has_data : UInt<1>, data_word_bypass : UInt<32>, data_raw : UInt<32>, store_data : UInt<32>}}, replay_next : UInt<1>, s2_xcpt : {ma : {ld : UInt<1>, st : UInt<1>}, pf : {ld : UInt<1>, st : UInt<1>}, ae : {ld : UInt<1>, st : UInt<1>}}, uncached_resp : {flip ready : UInt<1>, valid : UInt<1>, bits : {data : UInt<32>, mask : UInt<4>, addr : UInt<32>, tag : UInt<19>, cmd : UInt<16>, _size : UInt<2>, signed : UInt<1>, dprv : UInt<2>, replay : UInt<1>, has_data : UInt<1>, data_word_bypass : UInt<32>, data_raw : UInt<32>, store_data : UInt<32>}}, ordered : UInt<1>, keep_clock_enabled : UInt<1>, clock_enabled : UInt<1>}, cache : {req : {flip ready : UInt<1>, valid : UInt<1>, bits : {phys : UInt<1>, no_alloc : UInt<1>, no_xcpt : UInt<1>, addr : UInt<32>, tag : UInt<19>, cmd : UInt<16>, _size : UInt<2>, signed : UInt<1>, dprv : UInt<2>, data : UInt<32>, mask : UInt<4>}}, s1_kill : UInt<1>, s1_data : {}, s2_nack : UInt<1>, s2_nack_cause_raw : UInt<1>, s2_kill : UInt<1>, s2_uncached : UInt<1>, s2_paddr : UInt<6>("h20"), resp : {valid : UInt<1>, bits : {data : UInt<32>, mask : UInt<4>, addr : UInt<32>, tag : UInt<19>, cmd : UInt<16>, _size : UInt<2>, signed : UInt<1>, dprv : UInt<2>, replay : UInt<1>, has_data : UInt<1>, data_word_bypass : UInt<32>, data_raw : UInt<32>, store_data : UInt<32>}}, replay_next : UInt<1>, s2_xcpt : {ma : {ld : UInt<1>, st : UInt<1>}, pf : {ld : UInt<1>, st : UInt<1>}, ae : {ld : UInt<1>, st : UInt<1>}}, uncached_resp : {flip ready : UInt<1>, valid : UInt<1>, bits : {data : UInt<32>, mask : UInt<4>, addr : UInt<32>, tag : UInt<19>, cmd : UInt<16>, _size : UInt<2>, signed : UInt<1>, dprv : UInt<2>, replay : UInt<1>, has_data : UInt<1>, data_word_bypass : UInt<32>, data_raw : UInt<32>, store_data : UInt<32>}}, ordered : UInt<1>, keep_clock_enabled : UInt<1>, clock_enabled : UInt<1>}}
  
    inst replayq of clsSimpleHellaCacheIFReplayQueue
    replayq.clock <= clock
    replayq.reset <= reset
    inst req_arb of clsArbiter
    req_arb.clock <= clock
    req_arb.reset <= reset
    replayq.io.replay.ready <= req_arb.io._in[0].ready
    req_arb.io._in[0].bits.signed <= replayq.io.replay.bits.signed
    req_arb.io._in[0].bits._size <= replayq.io.replay.bits._size
    req_arb.io._in[0].bits.no_xcpt <= replayq.io.replay.bits.no_xcpt
    req_arb.io._in[0].bits.cmd <= replayq.io.replay.bits.cmd
    req_arb.io._in[0].bits.phys <= replayq.io.replay.bits.phys
    req_arb.io._in[0].bits.dprv <= replayq.io.replay.bits.dprv
    req_arb.io._in[0].bits.no_alloc <= replayq.io.replay.bits.no_alloc
    req_arb.io._in[0].bits.tag <= replayq.io.replay.bits.tag
    req_arb.io._in[0].bits.addr <= replayq.io.replay.bits.addr
    req_arb.io._in[0].bits.data <= replayq.io.replay.bits.data
    req_arb.io._in[0].bits.mask <= replayq.io.replay.bits.mask
    req_arb.io._in[0].valid <= replayq.io.replay.valid
    node _T = and(req_arb.io._in[1].ready, replayq.io.req.ready)
    node _T_1 = and(_T, io.requestor.req.valid)
    req_arb.io._in[1].valid <= _T_1
    req_arb.io._in[1].bits <= io.requestor.req.bits
    node _T_2 = and(req_arb.io._in[1].ready, replayq.io.req.ready)
    node _T_3 = and(_T_2, io.requestor.req.valid)
    io.requestor.req.ready <= _T_3
    node _T_4 = and(req_arb.io._in[1].ready, replayq.io.req.ready)
    node _T_5 = and(_T_4, io.requestor.req.valid)
    replayq.io.req.valid <= _T_5
    replayq.io.req.bits <= io.requestor.req.bits
    reg s1_req_fire : UInt<1>, clock
    node s0_req_fire = and(io.cache.req.valid, io.cache.req.ready)
    s1_req_fire <= s0_req_fire
    reg s2_req_fire : UInt<1>, clock
    s2_req_fire <= s1_req_fire
    reg s1_req_tag : UInt<19>, clock
    s1_req_tag <= io.cache.req.bits.tag
    reg s2_req_tag : UInt<19>, clock
    s2_req_tag <= s1_req_tag
    req_arb.io.out.ready <= io.cache.req.ready
    io.cache.req.bits.signed <= req_arb.io.out.bits.signed
    io.cache.req.bits._size <= req_arb.io.out.bits._size
    io.cache.req.bits.no_xcpt <= req_arb.io.out.bits.no_xcpt
    io.cache.req.bits.cmd <= req_arb.io.out.bits.cmd
    io.cache.req.bits.phys <= req_arb.io.out.bits.phys
    io.cache.req.bits.dprv <= req_arb.io.out.bits.dprv
    io.cache.req.bits.no_alloc <= req_arb.io.out.bits.no_alloc
    io.cache.req.bits.tag <= req_arb.io.out.bits.tag
    io.cache.req.bits.addr <= req_arb.io.out.bits.addr
    io.cache.req.bits.data <= req_arb.io.out.bits.data
    io.cache.req.bits.mask <= req_arb.io.out.bits.mask
    io.cache.req.valid <= req_arb.io.out.valid
    reg _T_6 : UInt<32>, clock
    when s0_req_fire :
      _T_6 <= req_arb.io.out.bits.data
