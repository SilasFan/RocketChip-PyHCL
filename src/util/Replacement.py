from typing import List, Union
from pyhcl import *
from pyhcl.util import *
from helper.common import *
from util.package import *


class PseudoLRU():
    # Pseudo-LRU tree algorithm: https:#en.wikipedia.org/wiki/Pseudo-LRU#Tree-PLRU
    #
    #
    # - bits storage example for 4-way PLRU binary tree:
    #                  bit[2]: ways 3+2 older than ways 1+0
    #                  /                                  \
    #     bit[1]: way 3 older than way 2    bit[0]: way 1 older than way 0
    #
    #
    # - bits storage example for 3-way PLRU binary tree:
    #                  bit[1]: way 2 older than ways 1+0
    #                                                  \
    #                                       bit[0]: way 1 older than way 0
    #
    #
    # - bits storage example for 8-way PLRU binary tree:
    #                      bit[6]: ways 7-4 older than ways 3-0
    #                      /                                  \
    #            bit[5]: ways 7+6 > 5+4                bit[2]: ways 3+2 > 1+0
    #            /                    \                /                    \
    #     bit[4]: way 7>6    bit[3]: way 5>4    bit[1]: way 3>2    bit[0]: way 1>0
    def __init__(self, n_ways: int):
        nBits = n_ways - 1
        self.n_ways = n_ways
        self.nBits = n_ways - 1
        self.perSet = True
        self.state_reg = Reg(U.w(0)) if (nBits == 0) else RegInit(U.w(nBits)(0))
        self.state_read = WireDefault(self.state_reg)

    def access(self, touch_way: Union[U, List[Valid]]):
        if not isinstance(touch_way, list):
            self.state_reg <<= self.get_next_state(self.state_reg, touch_way)
            return
        touch_ways = touch_way
        with when (orR(list(map(lambda x: x.valid, touch_ways)))):
            self.state_reg <<= self.get_next_state(self.state_reg, touch_ways)
        # for (i <- 1 until touch_ways.size):
        #     cover(PopCount(touch_ways.map(_.valid)) === i.U, s"PLRU_UpdateCount$i", s"PLRU Update $i simultaneous")

    """
        @param state self.state_reg bits for this sub-tree
        @param touch_way touched way encoded value bits for this sub-tree
        @param tree_nways number of ways in this sub-tree
    """
    def get_next_state(self, state: U, touch_way: U, tree_nways: int = None) -> U:
        if not tree_nways:
            n_ways = self.n_ways
            if (touch_way.width < log2Ceil(n_ways)):
                touch_way_sized = padTo(touch_way, log2Ceil(n_ways))
            else:
                touch_way_sized = extract(touch_way, log2Ceil(n_ways)-1, 0)
            return self.get_next_state(state, touch_way_sized, n_ways)

        # assert state.width == (tree_nways-1), f"wrong state bits width {state.width} for {tree_nways} ways"
        # assert touch_way.width == (max(log2Ceil(tree_nways), 1)), f"wrong encoded way width {touch_way.width} for {tree_nways} ways"

        if (tree_nways > 2):
            # we are at a branching node in the tree, so recurse
            right_nways: int = 1 << (log2Ceil(tree_nways) - 1)    # number of ways in the right sub-tree
            left_nways: int = tree_nways - right_nways                 # number of ways in the left sub-tree
            set_left_older = ~touch_way(log2Ceil(tree_nways)-1)
            left_subtree_state = extract(state, tree_nways-3, right_nways-1)
            right_subtree_state = state[right_nways-2: 0]

            if (left_nways > 1):
                # we are at a branching node in the tree with both left and right sub-trees, so recurse both sub-trees
                return Cat(set_left_older,
                           Mux(set_left_older,
                               left_subtree_state,    # if setting left sub-tree as older, do NOT recurse into left sub-tree
                               self.get_next_state(left_subtree_state, extract(touch_way, log2Ceil(left_nways)-1,0), left_nways)),    # recurse left if newer
                           Mux(set_left_older,
                               self.get_next_state(right_subtree_state, touch_way[log2Ceil(right_nways)-1:0], right_nways),    # recurse right if newer
                               right_subtree_state))    # if setting right sub-tree as older, do NOT recurse into right sub-tree
            else:
                # we are at a branching node in the tree with only a right sub-tree, so recurse only right sub-tree
                return Cat(set_left_older,
                           Mux(set_left_older,
                               self.get_next_state(right_subtree_state, touch_way[log2Ceil(right_nways)-1:0], right_nways),    # recurse right if newer
                               right_subtree_state))    # if setting right sub-tree as older, do NOT recurse into right sub-tree
        elif (tree_nways == 2):
            # we are at a leaf node at the end of the tree, so set the single state bit opposite of the lsb of the touched way encoded value
            return ~touch_way[0]
        else:    # tree_nways <= 1
            # we are at an empty node in an empty tree for 1 way, so return single zero bit for Chisel (no zero-width wires)
            return U.w(1)(0)

    """
        @param state self.state_reg bits for this sub-tree
        @param tree_nways number of ways in this sub-tree
    """
    def get_replace_way(self, state: U, tree_nways: int = None):

        if not tree_nways:
            return self.get_replace_way(state, self.n_ways)

        # assert state.width == (tree_nways-1), f"wrong state bits width {state.width} for {tree_nways} ways"

        # this algorithm recursively descends the binary tree, filling in the way-to-replace encoded value from msb to lsb
        if (tree_nways > 2):
            # we are at a branching node in the tree, so recurse
            right_nways: int = 1 << (log2Ceil(tree_nways) - 1)    # number of ways in the right sub-tree
            left_nways: int = tree_nways - right_nways                 # number of ways in the left sub-tree
            left_subtree_older = state[tree_nways-2]
            left_subtree_state = extract(state, tree_nways-3, right_nways-1)
            right_subtree_state = state[right_nways-2: 0]

            if (left_nways > 1):
                # we are at a branching node in the tree with both left and right sub-trees, so recurse both sub-trees
                return Cat(left_subtree_older,            # return the top state bit (current tree node) as msb of the way-to-replace encoded value
                           Mux(left_subtree_older,    # if left sub-tree is older, recurse left, else recurse right
                               self.get_replace_way(left_subtree_state, left_nways),        # recurse left
                               self.get_replace_way(right_subtree_state, right_nways)))    # recurse right
            else:
                # we are at a branching node in the tree with only a right sub-tree, so recurse only right sub-tree
                return Cat(left_subtree_older,            # return the top state bit (current tree node) as msb of the way-to-replace encoded value
                           Mux(left_subtree_older,    # if left sub-tree is older, return and do not recurse right
                               U.w(1)(0),
                               self.get_replace_way(right_subtree_state, right_nways)))    # recurse right
        elif (tree_nways == 2):
            # we are at a leaf node at the end of the tree, so just return the single state bit as lsb of the way-to-replace encoded value
            return state[0]
        else:    # tree_nways <= 1
            # we are at an empty node in an unbalanced tree for non-power-of-2 ways, so return single zero bit as lsb of the way-to-replace encoded value
            return U.w(1)(0)

    def way(self):
        return self.get_replace_way(self.state_reg)

    def miss(self):
        return self.access(self.way())

    def hit(self):
        return {}


if __name__ == "__main__":
    class Test(Module):
        io = IO(
            a = Output(U.w(4))
        )
        lru = PseudoLRU(16)
        io.a <<= lru.way()
    Emitter.dump(Emitter.emit(Test()), f"{__file__}.fir")

