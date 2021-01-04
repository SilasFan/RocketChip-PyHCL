from pyhcl import *
from dataclasses import dataclass
from typing import Any
from pyhcl.util.decoupled import Decoupled
from pyhcl.util.math import *
from pyhcl.util.counter import Counter
from pyhcl.util.wire import *


def Queue(gen: Any, entries: int, pipe: bool = False, flow: bool = False):
    assert entries > -1, "Queue must have non-negative number of entries"
    assert entries != 0, "Use companion object Queue.apply for zero entries"

    class clsQueue(Module):
        io = IO(
            enq = Input(Decoupled(gen)),
            deq = Output(Decoupled(gen)),
            count = Output(U.w(log2Ceil(entries + 1))),
        )

        ram = Mem(entries, gen)
        enq_ptr = Counter(entries)
        deq_ptr = Counter(entries)
        maybe_full = RegInit(Bool(False))

        ptr_match = enq_ptr.value == deq_ptr.value
        empty = ptr_match & ~maybe_full
        full = ptr_match & maybe_full

        do_enq = WireDefault(io.enq.fire())
        do_deq = WireDefault(io.deq.fire())

        with when (do_enq):
            ram[enq_ptr.value] <<= io.enq.bits
            enq_ptr.inc()

        with when (do_deq):
            deq_ptr.inc()

        with when (do_enq != do_deq):
            maybe_full <<= do_enq

        io.deq.valid <<= ~empty
        io.enq.ready <<= ~full
        io.deq.bits <<= ram[deq_ptr.value]

        if (flow):
            with when (io.enq.valid): io.deq.valid <<= Bool(True)
            with when (empty):
                io.deq.bits <<= io.enq.bits
                do_deq <<= Bool(False)
                with when (io.deq.ready): do_enq <<= Bool(False)

        if (pipe):
            with when (io.deq.ready): io.enq.ready <<= Bool(True)

        ptr_diff = enq_ptr.value - deq_ptr.value
        if (isPow2(entries)):
            io.count <<= Mux(maybe_full & ptr_match, U(entries), U(0)) | ptr_diff
        else:
            io.count <<= Mux(ptr_match,
                             Mux(maybe_full,
                                 U(entries), U(0)),
                             Mux(deq_ptr.value > enq_ptr.value,
                                 U(entries) + ptr_diff, ptr_diff))

    return clsQueue()


def QueueDefault(gen: Any, enq: Decoupled, entries: int = 2, 
                 pipe: bool = False, flow: bool = False) -> Decoupled:
    assert entries > 0
    _que = Queue(gen, entries, pipe, flow)
    _que.io.enq.valid <<= enq.valid
    _que.io.enq.bits <<= enq.bits
    enq.ready <<= _que.io.enq.ready
    return _que.io.deq

