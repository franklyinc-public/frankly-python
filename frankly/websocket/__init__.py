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

from copy import copy
from base64 import b64encode
from six.moves import http_client
from six.moves.urllib import parse
quote = parse.quote

import hashlib
import random
import six
import struct

from . import net
from . import http
from . import webtools

__all__ = [
    'CONTINUATION',
    'TEXT',
    'BINARY',
    'CLOSE',
    'PING',
    'PONG',
    'OPCODES',
    'OutOfData',
    'UpgradeFailure',
    'WebSocket',
    'connect',
    'upgrade',
    'hash_key',
    'make_random_key',
    'decode_close_frame',
    'encode_close_frame',
]

CONTINUATION = 0x00
TEXT = 0x01
BINARY = 0x02
CLOSE = 0x08
PING = 0x09
PONG = 0x0A
OPCODES = (CONTINUATION, TEXT, BINARY, CLOSE, PING, PONG)

class OutOfData(Exception):
    pass

class UpgradeFailure(http_client.HTTPException):
    pass

class WebSocket(object):

    def __init__(self, socket, mask=False):
        self.socket  = socket
        self.mask    = mask
        self.pending = None

    def __iter__(self):
        while True:
            message = self.recv()
            if message[0] is None:
                break
            yield message

    def __enter__(self):
        return self

    def __exit__(self, *args):
        try:
            self.shutdown(1001, "bye")
        except Exception:
            pass
        try:
            self.close()
        except Exception as e:
            pass

    def close(self):
        try:
            if self.socket is not None:
                self.socket.close()
        finally:
            self.pending = None

    def detach(self):
        socket, self.socket = self.socket, None
        return socket

    def fileno(self):
        return -1 if self.socket is None else self.socket.fileno()

    def recv_bytes(self, data, size):
        view = memoryview(data)[size:]
        recv = self.socket.recv_into(view)
        if recv == 0:
            raise OutOfData
        return size + recv

    def recv_frame(self, size_max=None):
        header = webtools.websocket_header()
        offset = 0

        if bool(self.pending):
            data, self.pending = self.pending, None
            size = len(data)
            offset = header.decode(data)
        else:
            data = bytearray(16)
            size = 0

        # Load websocket header
        while offset <= 0:
            size   = self.recv_bytes(data, size)
            offset = header.decode(data[:size])

        # BUG: must keep a buffer of extra data read from the socket that don't
        # belong to this frame!
        data  = data[offset:size]
        size -= offset

        # Make sure the mask is valid
        assert bool(self.mask) != bool(header.mask), "got frame with invalid mask bit"

        # Make sure payload length is not greater than 'size_max'
        assert size_max is None or header.length <= size_max, "got frame longer than maixmum allow length"

        # Extend buffer if too small to receive message
        if size < header.length:
            tmp = bytearray(header.length)
            tmp[:size] = data
            data = tmp

        # Load websocket payload
        while size < header.length:
            size = self.recv_bytes(data, size)

        # Make sure we don't consumed more data than we should
        if len(data) > header.length:
            data, self.pending = data[:header.length], data[header.length:]

        # Apply mask if needed
        if header.mask:
            webtools.xor_mask(data, header.key)

        return header.fin, header.opcode, data

    def recv(self, size_max=None):
        opcode  = None
        payload = None

        # Read frames and concatenate them until we get a FIN bit
        try:
            while True:
                fin, code, frame = self.recv_frame(size_max)

                if payload is None:
                    opcode  = code
                    payload = frame

                else:
                    # Only one opcode must be set per message
                    if code != CONTINUATION:
                        raise OutOfData
                    payload.extend(frame)

                if fin:
                    break
        except OutOfData:
            return None, None

        if opcode == TEXT:
            payload = six.text_type(bytes(payload), 'utf-8')

        return opcode, payload

    if six.PY3:
        def send_bytes(self, iovec):
            # SSL sockets don't support sendmsg, for that case we merge the iovec
            # in a single buffer.
            if self.socket.secure:
                data = bytearray()
                for chunk in iovec:
                    data.extend(chunk)
                return self.socket.sendall(data)

            full = sum(len(x) for x in iovec)
            size = 0

            while bool(iovec):
                # Efficiently send data avoiding user-space copy using sendmsg(2)
                rc = self.socket.sendmsg(iovec)
                if rc == 0:
                    raise IOError("failed to send data over websocket")
                size += rc

                # Shortcut if everything got sent, no need to work on the io vector
                if size == full:
                    break

                # Discard data from the io vector, because python documentation says
                # sendmsg may not send all data (although it should if it's used in
                # blocking mode).
                while bool(iovec) and rc >= len(iovec[0]):
                    rc -= len(iovec[0])
                    del iovec[0]
                if rc != 0:
                    iovec[0] = iovec[0][rc:]

            return size
    else:
        def send_bytes(self, iovec):
            data = bytearray()
            for chunk in iovec:
                data.extend(chunk)
            return self.socket.sendall(data)

    def send_frame(self, fin, opcode, frame):
        # Setup websocket header structure
        header          = webtools.websocket_header()
        header.key      = 0
        header.length   = len(frame)
        header.opcode   = opcode
        header.fin      = fin
        header.mask     = 1 if self.mask else 0
        header.reserved = 0

        # Mask payload if required
        if self.mask:
            if not isinstance(frame, bytearray):
                frame = bytearray(frame)
            header.key = random.randint(0, 4294967296)
            webtools.xor_mask(frame, header.key)

        # Encode websocket header
        data = bytearray(16)
        size = header.encode(data)

        # Send message over the socket
        return self.send_bytes([data[:size], frame])

    def send(self, payload):
        if isinstance(payload, six.text_type):
            opcode  = TEXT
            payload = payload.encode('utf-8')
        else:
            opcode  = BINARY
        return self.send_frame(1, opcode, payload)

    def ping(self, payload):
        return self.send_frame(1, PING, payload)

    def pong(self, payload):
        return self.send_frame(1, PONG, payload)

    def shutdown(self, code, reason):
        return self.send_frame(1, CLOSE, encode_close_frame(code, reason))

    def getsockname(self):
        return self.socket.getsockname()

    def getpeername(self):
        return self.socket.getpeername()

    def gettimeout(self):
        return self.socket.gettimeout()

    def settimeout(self, timeout):
        self.socket.settimeout(timeout)

def hash_key(key):
    key += '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'
    key = key.encode('utf-8')
    sha = hashlib.sha1()
    sha.update(key)
    key = sha.digest()
    return six.text_type(b64encode(key), 'utf-8')

def make_random_key():
    return six.text_type(b64encode(bytes(random.choice(range(0, 255)) for _ in range(16))), 'utf-8')

def upgrade(http_client, key, subprotocol=None, fields=None):
    assert isinstance(http_client, http.HttpClient)

    if fields is None:
        fields = http.HttpFields()
    elif not isinstance(fields, http.HttpFields):
        fields = http.HttpFields(fields)
    else:
        fields = copy(fields)

    fields['Connection'] = 'Upgrade'
    fields['Upgrade'] = 'websocket'
    fields['Sec-WebSocket-Accept'] = hash_key(key)

    if subprotocol is not None:
        fields['Sec-WebSocket-Protocol'] = subprotocol

    http_client.server = None
    http_client.send(101, fields)
    return WebSocket(http_client.detach())

def connect(host, port='http', path='/', query=None, fragment=None, protocols=None, extensions=None, fields=None, key=None, **kwargs):
    if fields is None:
        fields = http.HttpFields()
    elif not isinstance(fields, http.HttpFields):
        fields = http.HttpFields(fields)
    else:
        fields = copy(fields)

    if key is None:
        key = make_random_key()

    fields['Connection'] = 'Upgrade'
    fields['Upgrade'] = 'websocket'
    fields['Sec-WebSocket-Key'] = key
    fields['Sec-WebSocket-Version'] = '13'

    if protocols is not None:
        fields['Sec-WebSocket-Protocol'] = ', '.join(quote(x) for x in protocols)

    if extensions is not None:
        fields['Sec-WebSocket-Extensions'] = ', '.join(quote(x) for x in extensions)

    key = hash_key(key)
    http_socket = http.connect(host, port, **kwargs)
    status, fields, content = http_socket.get(path, query, fragment, fields)
    accept = fields.get('Sec-WebSocket-Accept')
    version = fields.get('Sec-WebSocket-Version')

    if status != 101:
        raise UpgradeFailure(http.reasons[status])

    if accept != key:
        raise UpgradeFailure("http server responded with an invalid key (%s)" % accept)

    if version is not None and version != '13':
        raise UpgradeFailure("http server responded with another websocket version (%s)" % version)

    if bool(content.read(1)):
        raise UpgradeFailure("http server responded to upgrade with a non-empty content")

    return WebSocket(http_socket.detach(), mask=True)

def decode_close_frame(payload):
    if len(payload) == 0:
        return 1001, ''
    return struct.unpack(b'!H', payload[:2]), six.text_type(payload[2:], 'utf-8')

def encode_close_frame(code, reason):
    return struct.pack(b'!H', code) + reason.encode('utf-8')
