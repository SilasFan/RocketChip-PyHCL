# See LICENSE.SiFive for license details.
# See LICENSE.Berkeley for license details.

from pyhcl import *
from pyhcl.util import *
from helper.common import *
from helper.test import *
from rocket.HellaCache import *
from util.Misc import *

# This module buffers requests made by the SimpleHellaCacheIF in case they
# are nacked. Nacked requests must be replayed in order, and no other requests
# must be allowed to go through until the replayed requests are successfully
# completed.
def SimpleHellaCacheIFReplayQueue(depth: int):

    class clsSimpleHellaCacheIFReplayQueue(Module, HasL1HellaCacheParameters):
        io = IO(
            req=Input(Decoupled(HellaCacheReq())),
            nack=Input(Valid(U.w(coreParams.dcacheReqTagBits))), # .flip
            resp=Input(Valid(HellaCacheResp())), # .flip
            replay=Output(Decoupled(HellaCacheReq())),
        )

        # Registers to store the sent request
        # When a request is sent the first time,
        # it is stored in one of the reqs registers
        # and the corresponding inflight bit is set.
        # The reqs register will be deallocated once the request is
        # successfully completed.
        inflight = RegInit(U.w(depth)(0))
        reqs = Reg(Vec(depth, HellaCacheReq()))

        # The nack queue stores the index of nacked requests (in the reqs vector)
        # in the order that they were nacked. A request is enqueued onto nackq
        # when it is newly nacked (i.e. not a nack for a previous replay).
        # The head of the nack queue will be replayed until it is
        # successfully completed, at which time the request is dequeued.
        # No new requests will be made or other replays attempted until the head
        # of the nackq is successfully completed.
        nackq = Queue(U.w(log2Up(depth)), depth)
        replaying = RegInit(Bool(False))

        next_inflight_onehot = PriorityEncoderOH(~inflight)
        next_inflight = OHToUInt(next_inflight_onehot)

        next_replay = nackq.io.deq.bits
        next_replay_onehot = UIntToOH(next_replay)
        next_replay_req = reqs[next_replay]

        # Keep sending the head of the nack queue until it succeeds
        io.replay.valid = nackq.io.deq.valid & ~replaying
        io.replay.bits = next_replay_req
        # Don't allow new requests if there is are replays waiting
        # or something being nacked.
        io.req.ready = ~inflight.andR & ~nackq.io.deq.valid & ~io.nack.valid

        def helper(io, reqs):
            ret = list(map(lambda x: x.tag == io.nack.bits, reqs))
            ret.reverse()
            return ret
        # Match on the tags to determine the index of nacks or responses
        nack_onehot = Cat(*helper(io, reqs)) & inflight
        def helper(io, reqs):
            ret = list(map(lambda x: x.tag == io.resp.bits.tag, reqs))
            ret.reverse()
            return ret
        resp_onehot = Cat(*helper(io, reqs)) & inflight

        replay_complete = io.resp.valid & replaying & (io.resp.bits.tag == next_replay_req.tag)
        nack_head = io.nack.valid & nackq.io.deq.valid & (io.nack.bits == next_replay_req.tag)

        # Enqueue to the nack queue if there is a nack that is ~in response to
        # the previous replay
        nackq.io.enq.valid <<= io.nack.valid & ~nack_head
        nackq.io.enq.bits <<= OHToUInt(nack_onehot)
        # assert(not nackq.io.enq.valid or nackq.io.enq.ready,
        #   "SimpleHellaCacheIF: ReplayQueue nack queue overflow")

        # Dequeue from the nack queue if the last replay was successfully completed
        nackq.io.deq.ready <<= replay_complete
        # assert(not nackq.io.deq.ready or nackq.io.deq.valid,
        #   "SimpleHellaCacheIF: ReplayQueue nack queue underflow")

        # Set inflight bit when a request is made
        # Clear it when it is successfully completed
        inflight <<= ((inflight | Mux(io.req.fire(), next_inflight_onehot, U(0))) &
                                ~Mux(io.resp.valid, resp_onehot, U(0)))

        with when (io.req.fire()):
            reqs[next_inflight] <<= io.req.bits

        # Only one replay outstanding at a time
        with when (io.replay.fire()):
            replaying <<= Bool(True)
        with when (nack_head | replay_complete):
            replaying <<= Bool(False)

    return clsSimpleHellaCacheIFReplayQueue()


# exposes a sane decoupled request interface
def SimpleHellaCacheIF():

    class clsSimpleHellaCacheIF(Module):
        io = IO(
            requestor = Input(HellaCacheIO()), #.flip,
            cache = Output(HellaCacheIO()),
        )
        replayq = SimpleHellaCacheIFReplayQueue(2)
        req_arb = Arbiter(HellaCacheReq(), 2)

        req_helper = DecoupledHelper(
          req_arb.io._in[1].ready,
          replayq.io.req.ready,
          io.requestor.req.valid)

        connect_all(req_arb.io._in[0], replayq.io.replay)
        req_arb.io._in[1].valid <<= req_helper.fire(req_arb.io._in[1].ready)
        req_arb.io._in[1].bits <<= io.requestor.req.bits
        io.requestor.req.ready <<= req_helper.fire(io.requestor.req.valid)
        replayq.io.req.valid <<= req_helper.fire(replayq.io.req.ready)
        replayq.io.req.bits <<= io.requestor.req.bits

        s0_req_fire = io.cache.req.fire()
        s1_req_fire = RegNext(s0_req_fire)
        s2_req_fire = RegNext(s1_req_fire)
        s1_req_tag = RegNext(io.cache.req.bits.tag)
        s2_req_tag = RegNext(s1_req_tag)

        # assert(not RegNext(io.cache.s2_nack) or not s2_req_fire or io.cache.s2_nack)
        # assert(not io.cache.s2_nack or not io.cache.req.ready)

        connect_all(io.cache.req, req_arb.io.out)
        io.cache.s1_kill = Bool(False)
        io.cache.s1_data.data = RegEnable(req_arb.io.out.bits.data, s0_req_fire)
        io.cache.s2_kill = Bool(False)

        replayq.io.nack.valid = io.cache.s2_nack & s2_req_fire
        replayq.io.nack.bits = s2_req_tag
        replayq.io.resp = io.cache.resp
        io.requestor.resp = io.cache.resp

        # assert(not s2_req_fire or not io.cache.s2_xcpt.asUInt.orR, "SimpleHellaCacheIF exception")

    return clsSimpleHellaCacheIF()


if __name__ == "__main__":
    Emitter.dump(Emitter.emit(SimpleHellaCacheIF()), f"{__file__}.fir")

