# SPDX-License-Identifier: Apache-2.0
import unittest

from pin_timing import (CAPTURE,FALLING,HALT,LOW,PERIOD_PS,RELEASE,RISING,assemble,bit,
                        envelope_errors,events,gpio,literal_image,response_errors,transport_word,wire_word)
from phase_programs import compact_program,encode


class PinTimingTests(unittest.TestCase):
    def test_literal_image_independent_cross_check(self):
        for order in (0,1):
            self.assertEqual(literal_image(order),[encode(w) for w in compact_program(msb_first=order)])
            self.assertEqual(len(literal_image(order))*32,256)
        self.assertEqual((LOW[0],RISING[-1],CAPTURE[-1],RELEASE,HALT),(2,377,379,402,403))
        self.assertTrue(all(f-r==25 for r,f in zip(RISING,FALLING)))

    def test_all_bytes_and_both_aperture_boundaries(self):
        for order in (0,1):
            for byte in range(256):
                self.assertEqual(assemble([bit(byte,j,order) for j in range(8)],order),byte)
                for noise in (False,True):
                    e=events(byte,order,[499999]*8,noise=noise)
                    self.assertEqual(envelope_errors(e,byte,order),[])
                    self.assertEqual(wire_word(e,order),byte)
                    self.assertEqual(transport_word(e,order),byte)

    def test_original_response_envelope(self):
        for d in range(1,97):
            e=events(0x69,1,[5000*d]*8)
            self.assertEqual(envelope_errors(e,0x69,1,setup_ps=20000,hold_ps=20000),[])
            self.assertEqual(transport_word(e,1),0x69)

    def test_early_capture_counterexample(self):
        for order,expected in ((1,0xB4),(0,0xD3)):
            e=events(0x69,order,[499999]*8)
            self.assertEqual(wire_word(e,order),0x69)
            self.assertEqual(transport_word(e,order,early=True),expected)
        e=events(0,1,[500001]*8)
        self.assertTrue(envelope_errors(e,0,1))
        self.assertNotEqual(wire_word(e,1),0)

    def test_gpio_edges_are_independent_of_input(self):
        old=8; rises=[]; falls=[]
        for n in range(1,HALT+1):
            value,oe=gpio(n,0x96,1)
            resolved=(value&oe)|(8&~oe)
            self.assertEqual(oe&2,0)
            if not old&4 and resolved&4: rises.append(n)
            if old&4 and not resolved&4: falls.append(n)
            old=resolved
        self.assertEqual(rises,RISING); self.assertEqual(falls,FALLING)
        self.assertEqual(gpio(RELEASE,0x96,1)[0]&12,8)

    def test_unchanged_ones_cannot_qualify_a_late_response_profile(self):
        e=events(255,0,[500001]*8)
        self.assertEqual(e,[])
        self.assertEqual(envelope_errors(e,255,0),[])
        self.assertEqual(wire_word(e,0),255)
        self.assertEqual(response_errors([500001]*8),list(range(8)))
        self.assertEqual(response_errors([499999]*8),[])


if __name__=='__main__': unittest.main()
