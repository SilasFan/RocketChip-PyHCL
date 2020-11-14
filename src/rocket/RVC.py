# See LICENSE.SiFive for license details.
from dataclasses import dataclass
from pyhcl import *
from util.common import *

"""
usingCompressed = True
XLen = 32

class HasCoreParameters:
    pass


class Parameters:
    pass
"""

class ExpandedInstruction():
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def RVCDecoder(x: U, xLen: int):

    rs1p = Cat(U.w(2)(1), x[9:7])
    rs2p = Cat(U.w(2)(1), x[4:2])
    rs2 = x[6:2]
    rd = x[11:7]
    addi4spnImm = Cat(x[10:7], x[12:11], x[5], x[6], U.w(2)(0))
    lwImm = Cat(x[5], x[12:10], x[6], U.w(2)(0))
    ldImm = Cat(x[6:5], x[12:10], U.w(3)(0))
    lwspImm = Cat(x[3:2], x[12], x[6:4], U.w(2)(0))
    ldspImm = Cat(x[4:2], x[12], x[6:5], U.w(3)(0))
    swspImm = Cat(x[8:7], x[12:9], U.w(2)(0))
    sdspImm = Cat(x[9:7], x[12:10], U.w(3)(0))
    luiImm = Cat(Fill(15, x[12]), x[6:2], U.w(12)(0))
    addi16spImm = Cat(Fill(3, x[12]), x[4:3], x[5], x[2], x[6], U.w(4)(0))
    addiImm = Cat(Fill(7, x[12]), x[6:2])
    jImm = Cat(Fill(10, x[12]), x[8], x[10:9], x[6], x[7], x[2], x[11], x[5:3], U.w(1)(0))
    bImm = Cat(Fill(5, x[12]), x[6:5], x[2], x[11:10], x[4:3], U.w(1)(0))
    shamt = Cat(x[12], x[6:2])
    x0 = U.w(5)(0)
    ra = U.w(5)(1)
    sp = U.w(5)(2)

    class clsRVCDecoder():

        def inst(self, bits, rd = x[11,7], rs1 = x[19,15], rs2 = x[24,20], rs3 = x[31,27]):
            return ExpandedInstruction(
                bits = bits,
                rd = rd,
                rs1 = rs1,
                rs2 = rs2,
                rs3 = rs3
            )

        def q0(self):
            addi4spn = self.inst(Cat(addi4spnImm, sp, U.w(3)(0), rs2p, Mux(orR(x[12:5]), U.w(7)(0x13), U.w(7)(0x1F))), rs2p, sp, rs2p)
            ld = self.inst(Cat(ldImm, rs1p, U.w(3)(3), rs2p, U.w(7)(0x03)), rs2p, rs1p, rs2p)
            lw = self.inst(Cat(lwImm, rs1p, U.w(3)(2), rs2p, U.w(7)(0x03)), rs2p, rs1p, rs2p)
            fld = self.inst(Cat(ldImm, rs1p, U.w(3)(3), rs2p, U.w(7)(0x07)), rs2p, rs1p, rs2p)
            flw = self.inst(Cat(lwImm, rs1p, U.w(3)(2), rs2p, U.w(7)(0x07)), rs2p, rs1p, rs2p) if (xLen == 32) else ld
            unimp = self.inst(Cat(lwImm >> 5, rs2p, rs1p, U.w(3)(2), lwImm[4:0], U.w(7)(0x3F)), rs2p, rs1p, rs2p)
            sd = self.inst(Cat(ldImm >> 5, rs2p, rs1p, U.w(3)(3), ldImm[4:0], U.w(7)(0x23)), rs2p, rs1p, rs2p)
            sw = self.inst(Cat(lwImm >> 5, rs2p, rs1p, U.w(3)(2), lwImm[4:0], U.w(7)(0x23)), rs2p, rs1p, rs2p)
            fsd = self.inst(Cat(ldImm >> 5, rs2p, rs1p, U.w(3)(3), ldImm[4:0], U.w(7)(0x27)), rs2p, rs1p, rs2p)
            fsw = self.inst(Cat(lwImm >> 5, rs2p, rs1p, U.w(3)(2), lwImm[4:0], U.w(7)(0x27)), rs2p, rs1p, rs2p) if (xLen == 32) else sd
            return [addi4spn, fld, lw, flw, unimp, fsd, sw, fsw]

        def q1(self):
            addi = self.inst(Cat(addiImm, rd, U.w(3)(0), rd, U.w(7)(0x13)), rd, rd, rs2p)
            opc = Mux(orR(rd), U.w(7)(0x1B), U.w(7)(0x1F))
            addiw = self.inst(Cat(addiImm, rd, U.w(3)(0), rd, opc), rd, rd, rs2p)
            jal = self.inst(Cat(jImm[20], jImm[10:1], jImm[11], jImm[19:12], ra, U.w(7)(0x6F)), ra, rd, rs2p) if (xLen == 32) else addiw
            li = self.inst(Cat(addiImm, x0, U.w(3)(0), rd, U.w(7)(0x13)), rd, x0, rs2p)
            opc = Mux(orRsize(addiImm, 12), U.w(7)(0x13), U.w(7)(0x1F))
            addi16sp = self.inst(Cat(addi16spImm, rd, U.w(3)(0), rd, opc), rd, rd, rs2p)
            opc = Mux(orRsize(addiImm, 12), U.w(7)(0x37), U.w(7)(0x3F))
            me = self.inst(Cat(luiImm[31:12], rd, opc), rd, rd, rs2p)
            lui = addi16sp
            # with when (rd == x0):
            #     lui = addi16sp
            # with elsewhen (rd == x0):
            #     lui = addi16sp
            # with otherwise():
            #     lui = me
            # lui = Mux(rd == x0 or rd == sp, addi16sp, me)
            j = self.inst(Cat(jImm[20], jImm[10:1], jImm[11], jImm[19:12], x0, U.w(7)(0x6F)), x0, rs1p, rs2p)
            beqz = self.inst(Cat(bImm[12], bImm[10:5], x0, rs1p, U.w(3)(0), bImm[4:1], bImm[11], U.w(7)(0x63)), rs1p, rs1p, x0)
            bnez = self.inst(Cat(bImm[12], bImm[10:5], x0, rs1p, U.w(3)(1), bImm[4:1], bImm[11], U.w(7)(0x63)), x0, rs1p, x0)
            def arith():
                srli = Cat(shamt, rs1p, U.w(3)(5), rs1p, U.w(7)(0x13))
                srai = srli | U(1 << 30)
                andi = Cat(addiImm, rs1p, U.w(3)(7), rs1p, U.w(7)(0x13))
                def rtype():
                    funct = get_from([U(0), U(4), U(6), U(7), U(0), U(0), U(2), U(3)], Cat(x[12], x[6:5]))
                    sub = Mux(x[6:5] == U(0), U(1 << 30), U(0))
                    opc = Mux(x[12], U.w(7)(0x3B), U.w(7)(0x33))
                    return Cat(rs2p, rs1p, funct, rs1p, opc) | sub
                return self.inst(get_from([srli, srai, andi, rtype()], x[11:10]), rs1p, rs1p, rs2p)

            arith = arith()
            return [addi, jal, li, lui, arith, j, beqz, bnez]
        
        def q2(self):
            load_opc = Mux(orR(rd), U.w(7)(0x03), U.w(7)(0x1F))
            slli = self.inst(Cat(shamt, rd, U.w(3)(1), rd, U.w(7)(0x13)), rd, rd, rs2)
            ldsp = self.inst(Cat(ldspImm, sp, U.w(3)(3), rd, load_opc), rd, sp, rs2)
            lwsp = self.inst(Cat(lwspImm, sp, U.w(3)(2), rd, load_opc), rd, sp, rs2)
            fldsp = self.inst(Cat(ldspImm, sp, U.w(3)(3), rd, U.w(7)(0x07)), rd, sp, rs2)
            flwsp = self.inst(Cat(lwspImm, sp, U.w(3)(2), rd, U.w(7)(0x07)), rd, sp, rs2) if (xLen == 32) else ldsp
            sdsp = self.inst(Cat(sdspImm >> 5, rs2, sp, U.w(3)(3),  sdspImm[4,0], U.w(7)(0x23)), rd, sp, rs2)
            swsp = self.inst(Cat(swspImm >> 5, rs2, sp, U.w(3)(2),  swspImm[4,0], U.w(7)(0x23)), rd, sp, rs2)
            fsdsp = self.inst(Cat(sdspImm >> 5, rs2, sp, U.w(3)(3), sdspImm[4,0], U.w(7)(0x27)), rd, sp, rs2)
            fswsp = self.inst(Cat(swspImm >> 5, rs2, sp, U.w(3)(2), swspImm[4,0], U.w(7)(0x27)), rd, sp, rs2) if (xLen == 32) else sdsp
            
            def jalr():
                mv = self.inst(Cat(rs2, x0, U.w(3)(0), rd, U.w(7)(0x33)), rd, x0, rs2)
                add = self.inst(Cat(rs2, rd, U.w(3)(0), rd, U.w(7)(0x33)), rd, rd, rs2)
                jr = Cat(rs2, rd, U.w(3)(0), x0, U.w(7)(0x67))
                reserved = Cat(jr >> 7, U.w(7)(0x1F))
                jr_reserved = self.inst(Mux(orR(rd), jr, reserved), x0, rd, rs2)
                # with when (orR(rs2)): 
                #     jr_mv = mv
                # with otherwise(): 
                #     jr_mv = jr_reserved
                jr_mv = mv
                # jr_mv = Mux(orR(rs2), mv, jr_reserved)
                jalr = Cat(rs2, rd, U.w(3)(0), ra, U.w(7)(0x67))
                ebreak = Cat(jr >> 7, U.w(7)(0x73)) | U(1 << 20)
                jalr_ebreak = self.inst(Mux(orR(rd), jalr, ebreak), ra, rd, rs2)
                # with when (orR(rs2)): 
                #     jalr_add = add
                # with otherwise(): 
                #     jalr_add = jalr_ebreak
                # jalr_add = Mux(orR(rs2), add, jalr_ebreak)
                jalr_add = add
                #with when (x[12]): 
                #    ret = jalr_add
                #with otherwise(): 
                #    ret = jr_mv
                #return ret
                return jr_mv

            jalr = jalr()
            return [slli, fldsp, lwsp, flwsp, jalr, fsdsp, swsp, fswsp]

        def q3(self):
            return [self.passthrough() for _ in range(8)]

        def passthrough(self):
            return self.inst(x)

        def decode(self):
            s = self.q0() + self.q1() + self.q2() + self.q3()
            return s[1]
            # return get_from(s, Cat(x[1:0], x[15:13]))

    return clsRVCDecoder()


def RVCExpander(p: Parameters):
    class clsRVCExpander(Module, HasCoreParameters):
        io = IO(
            in0 = Input(U.w(32)),
            out = Output(Bundle(
                bits = U.w(32),
                rd =  U.w(5),
                rs1 = U.w(5),
                rs2 = U.w(5),
                rs3 = U.w(5),
            )),
            rvc = Output(Bool)
        )

        if (usingCompressed):
            io.rvc <<= io.in0[1,0] != U(3)
            ret = RVCDecoder(io.in0, 1).decode()
            io.out.bits <<= ret.bits
            io.out.rd   <<= ret.rd 
            io.out.rs1  <<= ret.rs1
            io.out.rs2  <<= ret.rs2
            io.out.rs3  <<= ret.rs3
        else:
            io.rvc <<= Bool(False)
            ret = RVCDecoder(io.in0, 1).passthrough()
            io.out.bits <<= ret.bits
            io.out.rd   <<= ret.rd 
            io.out.rs1  <<= ret.rs1
            io.out.rs2  <<= ret.rs2
            io.out.rs3  <<= ret.rs3


    return clsRVCExpander()


if __name__ == "__main__":
    Emitter.dump(Emitter.emit(RVCExpander(1)), f"__file__.fir")
