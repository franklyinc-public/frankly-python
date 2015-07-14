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

from six.moves import urllib
urlparse = urllib.parse.urlparse

import ssl
import six

from . import auth
from . import async
from . import events
from . import fmp
from . import logger as log
from . import websocket as ws

__all__ = [
    'Backend',
]

class Backend(events.Emitter):

    def __init__(self, address, session):
        events.Emitter.__init__(self)

        url = urlparse(address)
        assert url.scheme in ('ws', 'wss'), "ws backend cannot connect to " + address

        address = url.scheme + '://' + url.netloc
        headers = { 'Accept': 'application/json', 'User-Agent': auth.USER_AGENT }

        if session.cookies is not None:
            cookie = session.cookies.get('app-token')
            if cookie is not None:
                headers['Cookie'] = 'app-token=' + cookie
        else:
            if session.key is not None:
                headers['Frankly-App-Key'] = session.key

            if session.secret is not None:
                headers['Frankly-App-Secret'] = session.secret

            if session.user is not None:
                headers['Frankly-App-User-Id'] = session.user

            if session.role is not None:
                headers['Frankly-App-User-Role'] = session.role

        self.url         = url
        self.address     = address
        self.headers     = headers
        self.socket      = None
        self.recv_worker = None
        self.ping_worker = None

    @property
    def opened(self):
        return self.socket is not None

    def open(self, **kwargs):
        host = self.url.hostname
        port = self.url.port

        if port is None:
            port = url.scheme

        self.socket = ws.connect(host, port=port, fields=self.headers, protocols=['chat'])

        self.recv_worker = async.Worker()
        self.ping_worker = async.Timer(20, self._pulse)

        self.recv_worker.start()
        self.ping_worker.start()

        self.recv_worker.schedule(None, self._run)

    def close(self, code, reason):
        if code is None:
            code = 1001

        if reason is None:
            reason = 'the connection was closed'

        self.socket.shutdown(code, reason)

        self.recv_worker.stop()
        self.ping_worker.stop()

        self.recv_worker.join()
        self.ping_worker.join()

        self.socket.close()
        self.socket = None

    def send(self, packet):
        self.socket.send(fmp.encode(packet))

    def _pulse(self):
        try:
            self.socket.ping(b'hi')
        except Exception as e:
            log.exception(e)

    def _run(self):
        try:
            while True:
                opcode, payload = self.socket.recv()

                if opcode == ws.CLOSE:
                    self.emit('close', *ws.decode_close_frame(payload))
                    break

                if opcode == ws.PING:
                    self.socket.pong(payload)
                    continue

                if opcode == ws.PONG:
                    continue

                if opcode == ws.TEXT:
                    continue

                if opcode == ws.BINARY:
                    try:
                        packet = fmp.decode(payload)
                    except Exception as e:
                        log.exception(e)
                    else:
                        self.emit('packet', packet)
                    continue
        except Exception as e:
            log.exception(e)
            self.emit('close')
