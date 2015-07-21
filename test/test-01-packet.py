##
# The MIT License (MIT)
#
# Copyright (c) 2015 Frankly Inc.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
##
from __future__ import division
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import frankly.fmp as fmp
import frankly.util as util
import unittest

class TestPacket(unittest.TestCase):

    def test_encode_decode_01(self):
        packet = fmp.Packet(0, 0, 0, [ ], util.Object(), None)
        string = fmp.encode(packet)
        self.assertEqual(packet, fmp.decode(string))

    def test_encode_decode_02(self):
        packet = fmp.Packet(1, 0, 0, [ ], util.Object(), None)
        string = fmp.encode(packet)
        self.assertEqual(packet, fmp.decode(string))

    def test_encode_decode_03(self):
        packet = fmp.Packet(2, 0, 0, [ ], util.Object(), None)
        string = fmp.encode(packet)
        self.assertEqual(packet, fmp.decode(string))

    def test_encode_decode_04(self):
        packet = fmp.Packet(3, 0, 0, [ ], util.Object(), None)
        string = fmp.encode(packet)
        self.assertEqual(packet, fmp.decode(string))

    def test_encode_decode_05(self):
        packet = fmp.Packet(0, 0, 0, ['path'], util.Object(hello='world'), None)
        string = fmp.encode(packet)
        self.assertEqual(packet, fmp.decode(string))

    def test_encode_decode_06(self):
        packet = fmp.Packet(1, 1, 42, ['path'], util.Object(), util.Object(hello='world'))
        string = fmp.encode(packet)
        self.assertEqual(packet, fmp.decode(string))

    def test_encode_decode_07(self):
        packet = fmp.Packet(0, 1, 42, ['path', '1234'], util.Object(), None)
        string = fmp.encode(packet)
        self.assertEqual(packet, fmp.decode(string))

    def test_encode_decode_08(self):
        packet = fmp.Packet(2, 1, 42, ['path', '1234'], util.Object(), None)
        string = fmp.encode(packet)
        self.assertEqual(packet, fmp.decode(string))

    def test_encode_decode_09(self):
        packet = fmp.Packet(2, 1, 42, ['path', '42'], util.Object(), util.Object(
            contents = [
                { 'type': 'text/plain', 'value': '\U0001f604' },
            ]
        ))
        string = fmp.encode(packet)
        self.assertEqual(packet, fmp.decode(string))
