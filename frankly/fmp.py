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

import msgpack
import os
import six

from . import util
from . import errors
from . import logger as log

__all__ = [
    'OK',
    'ERROR',
    'READ',
    'CREATE',
    'UPDATE',
    'DELETE',
    'RequestStore',
    'Request',
    'Packet',
    'encode',
    'decode',
]

OK     = 0
ERROR  = 1
READ   = 0
CREATE = 1
UPDATE = 2
DELETE = 3

class RequestStore(object):

    def __init__(self):
        self.requests = { }

    def __iter__(self):
        for _, req in six.iteritems(self.requests):
            yield req

    def __len__(self):
        return len(self.requests)

    def load(self, packet):
        try:
            req = self.requests[packet.id]
        except KeyError:
            return None
        del self.requests[packet.id]
        return req

    def store(self, packet, expire, resolve, reject):
        req = Request(packet, expire, resolve, reject)
        self.requests[packet.id] = req
        return req

    def timeout(self, now):
        expired = [ ]

        for _, req in six.iteritems(self.requests):
            if req.expire <= now:
                expired.append(req)

        for req in expired:
            del self.requests[req.packet.id]

        for req in expired:
            try:
                req.timeout()
            except Exception as e:
                log.exception(e)

    def cancel(self):
        requests, self.requests = self.requests, { }

        for _, req in six.iteritems(requests):
            try:
                req.cancel()
            except Exception as e:
                log.exception(e)

    def clear(self):
        self.requests = { }

class Request(object):

    def __init__(self, packet, expire, resolve, reject):
        self.packet  = packet
        self.expire  = expire
        self.resolve = resolve
        self.reject  = reject

    def timeout(self):
        self.reject(errors.Error(self.packet.operation, self.packet.path, 408, "the request timed out"))

    def cancel(self):
        self.reject(errors.Error(self.packet.operation, self.packet.path, 500, "the request got canceled"))

    @property
    def operation(self):
        return type_string(self.packet.type)

class Packet(object):

    def __init__(self, type, seed, id, path, params, payload):
        self.type    = type
        self.seed    = seed
        self.id      = id
        self.path    = path
        self.params  = params
        self.payload = payload

    def __str__(self):
        return 'packet { type = %s, seed = %s, id = %s, path = %s, params = %s, payload = %s }' % (
            type_string(self.type),
            self.seed,
            self.id,
            path_string(self.path),
            params_string(self.params),
            payload_string(self.payload),
        )

    def __repr__(self):
        return 'frankly.fmp.Packet { type = %s, seed = %s, id = %s, path = %s, params = %s, payload = %s }' % (
            type_string(self.type),
            self.seed,
            self.id,
            path_string(self.path),
            self.params,
            self.payload,
        )

    def __ne__(self, packet):
        return not self.__eq__(packet)

    def __eq__(self, packet):
        return \
            self.type == packet.type and \
            self.seed == packet.seed and \
            self.id   == packet.id   and \
            self.path == packet.path and \
            self.payload == packet.payload

    @property
    def operation(self):
        return type_string(self.type)

def encode(packet):
    packer = msgpack.Packer(autoreset=False, encoding='utf-8')
    properties = int(packet.type) | (1 << 4)

    if packet.seed:
        properties |= (1 << 6)

    if packet.id:
        properties |= (1 << 5)

    packer.pack(properties)

    if packet.seed:
        packer.pack(packet.seed)

    if packet.id:
        packer.pack(packet.id)

    packer.pack(packet.path)
    packer.pack(packet.params)
    packer.pack(packet.payload)
    return packer.bytes()

def decode(chunk):
    packet = Packet(0, 0, 0, None, None, None)
    unpacker = msgpack.Unpacker(six.BytesIO(chunk), encoding='utf-8', object_pairs_hook=util.Object)
    properties = unpacker.unpack()

    packet.type = properties & 0x7

    if properties & (1 << 6):
        packet.seed = unpacker.unpack()

    if properties & (1 << 5):
        packet.id = unpacker.unpack()

    packet.path = unpacker.unpack()
    packet.params = unpacker.unpack()
    packet.payload = unpacker.unpack()
    return packet

def type_string(t):
    if t == READ:   return 'read'
    if t == CREATE: return 'create'
    if t == UPDATE: return 'update'
    if t == DELETE: return 'delete'
    return 'unknown'

def path_string(p):
    if len(p) == 0:
        return '/'
    return '/' + os.path.join(*p)

def params_string(p):
    return 'null' if p is None else '{ ... }'

def payload_string(p):
    if p is None:
        return 'null'

    if isinstance(p, dict):
        return '{ ... }'

    if isinstance(p, list):
        return '[ ... ]'

    return type(p)
