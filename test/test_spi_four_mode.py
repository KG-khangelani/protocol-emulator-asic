# SPDX-License-Identifier: Apache-2.0
"""Small independent boundary and mutation checks for the four-mode ruler."""
import copy
import unittest
from experiments.spi_phase.phase_programs import PhaseMachine
from experiments.spi_phase.four_mode_programs import image, execute_reference, describe
from tools.spi_four_mode_oracle import timing, raw_at, assess, wire_value


def case(mode=0, order=1, family="exact", profile="held", half=25, rx=0x69, tx=0x96):
    program, cs = image(mode, order, family, half)
    schedule = timing(mode, cs, half)
    raw = lambda n: raw_at(n, schedule, rx, order, profile, [4*half-4]*8)
    trace, commits = execute_reference(program, tx=tx, raw=raw, steps=schedule["halt"])
    captures = [s+(half-1 if family == "held" else 2) for s in schedule["sample"]]
    return program, schedule, trace, captures, commits


class FourModeOracleTests(unittest.TestCase):
    def test_hand_written_edge_tables(self):
        for mode in (0, 2):
            s = timing(mode, 3)
            self.assertEqual((s["leading"], s["trailing"]),
                             ([28,78,128,178,228,278,328,378], [53,103,153,203,253,303,353,403]))
            self.assertEqual((s["sample"], s["release"], s["halt"]), (s["leading"],403,404))
        for mode in (1, 3):
            s = timing(mode, 2)
            self.assertEqual(s["sample"], [52,102,152,202,252,302,352,402])
            self.assertEqual((s["release"],s["halt"]), (427,428))
        for mode in range(4):
            s=timing(mode,2)
            self.assertEqual((wire_value(s["leading"][0],s,0,0)>>2)&1,1-(mode>>1))
            self.assertEqual((wire_value(s["trailing"][0],s,0,0)>>2)&1,mode>>1)

    def test_reference_capacity_is_not_public_capacity(self):
        for mode in range(4):
            for family, count in (("exact",11 if mode&1 else 9),("held",10 if mode&1 else 8),("naive",8)):
                program,_=image(mode,0,family)
                self.assertEqual(len(program),count)
                self.assertEqual(describe(program)["fits_eight_word_store"],count<=8)
                if count>8:
                    with self.assertRaises(ValueError):
                        PhaseMachine().edge(program)

    def test_exact_and_held_contracts_in_both_orders(self):
        for mode in range(4):
            for order in (0,1):
                for family, profile in (("exact","held"),("exact","edge_only"),("held","held")):
                    p,s,t,c,commits=case(mode,order,family,profile)
                    self.assertEqual(assess(t,s,0x96,0x69,order,c),[])
                    self.assertEqual(commits,[[c[-1],0x69]])

    def test_held_optimization_rejects_edge_only_data(self):
        for mode in range(4):
            for order in (0,1):
                p,s,t,c,commits=case(mode,order,"held","edge_only")
                self.assertEqual(commits,[[c[-1],0x96]])
                self.assertEqual({e["kind"] for e in assess(t,s,0x96,0x69,order,c)},{"received_byte"})

    def test_naive_polarity_change_can_hide_boundary_failure(self):
        p,s,t,c,commits=case(2,1,"naive")
        self.assertEqual(commits,[[379,0x69]])
        self.assertEqual(assess(t,s,0x96,0x69,1,c),[{"kind":"idle_before_cs","edge":1}])
        for mode in (1,3):
            p,s,t,c,commits=case(mode,1,"naive")
            self.assertTrue(assess(t,s,0x96,0x69,1,c))

    def test_oracle_rejects_clock_release_and_contention_mutants(self):
        p,s,original,c,_=case(1)
        for kind,edge,field,mask in (("pins",s["leading"][0],"out",4),
                                     ("pins",s["release"]-1,"out",8),
                                     ("miso_contention",s["sample"][0],"oe",2)):
            trace=copy.deepcopy(original)
            trace[edge][field]^=mask
            self.assertIn(kind,{e["kind"] for e in assess(trace,s,0x96,0x69,1,c)})

    def test_invalid_parameters_and_small_half_period(self):
        for mode in (-1,4,True):
            with self.assertRaises(ValueError): timing(mode,2)
        with self.assertRaises(ValueError): timing(0,0)
        with self.assertRaises(ValueError): raw_at(10,timing(0,2),0,0,"held",[97]*8)
        for mode in range(4):
            for family in ("exact","held"):
                p,s,t,c,_=case(mode,0,family,half=4)
                self.assertEqual(assess(t,s,0x96,0x69,0,c),[])


if __name__ == "__main__":
    unittest.main()
