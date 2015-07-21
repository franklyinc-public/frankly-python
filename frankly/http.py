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
from six.moves import urllib
urlparse = urllib.parse.urlparse

import json
import os
import requests

from . import auth
from . import async
from . import events
from . import errors
from . import fmp
from . import util

__all__ = [
    'Backend',
    'decode_response_payload',
    'encode_request_payload',
]

class Backend(events.Emitter):

    def __init__(self, address, session):
        events.Emitter.__init__(self)

        url = urlparse(address)
        assert url.scheme in ('http', 'https'), "http backend cannot connect to " + address

        self.address = url.scheme + '://' + url.netloc
        self.headers = { 'Accept': 'application/json', 'User-Agent' : auth.USER_AGENT }
        self.workers = None
        self.opened  = False

        if session.cookies is not None:
            cookie = session.cookies.get('app-token')
            if cookie is not None:
                self.headers['Cookie'] = 'app-token=' + cookie
        else:
            if session.key is not None:
                self.headers['Frankly-App-Key'] = session.key

            if session.secret is not None:
                self.headers['Frankly-App-Secret'] = session.secret

            if session.user is not None:
                self.headers['Frankly-App-User-Id'] = session.user

            if session.role is not None:
                self.headers['Frankly-App-User-Role'] = session.role

    def open(self, **kwargs):
        self.opened = True

        if kwargs.get('async'):
            self.workers = async.WorkerPool()
            self.workers.start()
            self.workers.schedule(None, self.emit, 'open')
            return

        self.emit('open')

    def close(self, code, reason):
        self.opened = False

        if self.workers is None:
            self.emit('close', code, reason)

        else:
            self.workers.schedule(None, self.emit, 'close', code, reason)
            self.workers.stop()
            self.workers.join()

    def send(self, packet, timeout=None):
        if self.workers is None:
            return self._send(packet, timeout)

        def success(payload):
            self.emit('packet', fmp.Packet(0, packet.seed, packet.id, packet.path, packet.params, payload))

        def failure(error):
            if not isinstance(error, errors.Error):
                error = errors.Error(packet.operation, packet.path, 500, str(error))
            self.emit('packet', fmp.Packet(1, packet.seed, packet.id, packet.path, packet.params, util.Object(
                status = error.status,
                error  = error.reason,
            )))

        self.workers.schedule(async.Promise(None), self._send, packet, timeout).then(success, failure)

    def _send(self, packet, timeout=None):
        try:
            content = None
            headers = copy(self.headers)

            if packet.payload is not None:
                content = encode_request_payload(packet.payload)
                headers.update({
                    'Content-Length' : len(content),
                    'Content-Type'   : 'application/json',
                })

            response = requests.request(
                method  = make_method(packet.type),
                url     = self.address + '/' + os.path.join(*packet.path),
                headers = headers,
                params  = packet.params,
                data    = content,
                timeout = timeout,
            )
        except errors.Error:
            raise
        except Exception as e:
            raise errors.Error(packet.operation, packet.path, 500, str(e))
        response.encoding = 'utf-8'

        status = response.status_code
        result = decode_response_payload(response.text)

        if status < 200 or status >= 300:
            raise errors.Error(packet.operation, packet.path, status, result)

        return result

def make_method(type):
    if type == 0: return 'GET'
    if type == 1: return 'POST'
    if type == 2: return 'PUT'
    if type == 3: return 'DELETE'
    assert False, "invalid packet type: " + type

def decode_response_payload(payload, default=None):
    if len(payload) == 0:
        return default
    return json.loads(payload, cls=util.JsonDecoder)

def encode_request_payload(payload):
    return json.dumps(payload, cls=util.JsonEncoder)
