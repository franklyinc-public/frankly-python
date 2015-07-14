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

import six
import struct

__all__ = [
    'xor_mask',
    'websocket_header',
]

try:
    from wsaccel.xormask import XorMaskerSimple

    def _xor_mask(data, key):
        data[:] = XorMaskerSimple(key).process(data)

except ImportError:
    if six.PY3:
        def _xor_mask(data, key):
            for i in range(len(data)):
                data[i] ^= key[i % 4]
    else:
        def _xor_mask(data, key):
            for i in xrange(len(data)):
                data[i] ^= ord(key[i % 4])

def xor_mask(data, key):
    if type(key) in six.integer_types:
        key = struct.pack(b'=I', key)
    _xor_mask(data, key)

class websocket_header(object):

    def __init__(self):
        self.length   = 0
        self.key      = 0
        self.opcode   = 0
        self.fin      = 0
        self.mask     = 0
        self.reserved = 0

    def encode(self, data):
        if len(data) < 16:
            return -1

        paylen, key, opcode, fin, mask, offset = self.length, self.key, self.opcode, self.fin, self.mask, 2
        data[0] = opcode
        data[1] = 0

        if self.fin:
            data[0] |= 1 << 7

        if self.mask:
            data[1] |= 1 << 7

        if paylen < 126:
            data[1] |= paylen

        elif paylen < 65536:
            data[1] |= 126
            data[2:4] = struct.pack(b'!H', paylen)
            offset = 4

        else:
            data[1] |= 127
            data[2:10] = struct.pack(b'!Q', paylen)
            offset = 10

        if mask:
            data[offset:(offset + 4)] = struct.pack(b'=I', key)
            offset += 4

        return offset

    def decode(self, data):
        if len(data) < 2:
            return -1
        offset = 2

        byte   = data[0]
        fin    = byte >> 7
        opcode = byte & 0x0F

        byte   = data[1]
        mask   = byte >> 7
        paylen = byte & 0x7F

        if paylen == 126:
            if len(data) < 4:
                return -1
            paylen = struct.unpack(b'!H', data[2:4])[0]
            offset = 4

        elif paylen == 127:
            if len(data) < 10:
                return -1
            paylen = struct.unpack(b'!Q', data[2:10])[0]
            offset = 10

        if mask:
            if len(data) < (offset + 4):
                return -1
            key = struct.unpack(b'=I', data[offset:(offset + 4)])[0]
            offset += 4
        else:
            key = 0

        self.length = paylen
        self.key    = key
        self.fin    = fin
        self.opcode = opcode
        self.mask   = mask
        return offset
