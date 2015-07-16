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
urlparse   = urllib.parse.urlparse
urlunparse = urllib.parse.urlunparse

import requests
import six
import threading
import time

from . import auth
from . import async
from . import events
from . import errors
from . import logger as log
from . import model
from . import fmp
from . import util
from . import http
from . import ws

__all__ = [
    'BaseClient',
    'EventIterator',
]

class BaseClient(events.Emitter):

    def __init__(self, url, connect_timeout=None, request_timeout=None, async=False):
        events.Emitter.__init__(self, logger=log)

        # Immutable members of the client object.
        self._lock            = threading.Lock()
        self._BackendClass    = None
        self._running         = False
        self._async           = async
        self._url             = url
        self._address         = url.scheme + '://' + url.netloc
        self._connect_timeout = connect_timeout
        self._request_timeout = request_timeout

        # Mutable members of the client object (used when an asynchronous worker is
        # started).
        self._pending = None
        self._worker  = None
        self._timer   = None
        self._version = 0
        self._idseq   = 1

        # Mutable members of the client object (used when the backend is accessed
        # directly).
        self._backend = None

        if self._url.scheme in ('http', 'https'):
            # In asynchronous mode the HTTP backend uses a pool of workers to dispatch
            # requests.
            if async:
                workers.start_once()
            self._BackendClass = http.Backend
            return

        if self._url.scheme in ('ws', 'wss'):
            self._BackendClass = ws.Backend
            return

        raise TypeError("url scheme is none of http, https, ws or wss: " + self._address)

    def _open_with_identity_token_generator(self, generate_identity_token):
        assert hasattr(generate_identity_token, '__call__'), \
            "the identity token generator must be a callable"

        address = self._address
        timeout = self._request_timeout
        return self._open(lambda: auth.authenticate(address, generate_identity_token, timeout), ready=False)

    def _open_with_key_and_secret(self, app_key, app_secret, user=None, role=None):
        assert isinstance(app_key, str) or isinstance(app_key, six.text_type), \
            "app_key must be a string but %s was found" % type(app_key)

        assert isinstance(app_secret, str) or isinstance(app_secret, six.text_type), \
            "app_secret must be a string but %s was found" % type(app_secret)

        assert user is None or isinstance(user, int), \
            "user must be an integer but %s was found" % type(user)

        assert role is None or isinstance(role, str) or isinstance(role, six.text_type), \
            "role must be a string but %s was found" % type(role)

        return self._open(lambda: auth.Session(app_key, app_secret, user, role, info=util.Object(seed=0)), ready=True)

    def _open(self, authenticator, ready=False):
        with self._lock:
            if self._running:
                raise RuntimeError("frankly.Client.open called multiple times")
            self._running = True
            self._version += 1

            # This optimization attempts to detects whether we need to start and asynchronous
            # worker for this client, we don't need one if all these conditions are met:
            #
            # - the client authenticates using app key and secret
            # - the client operates using a HTTP backend
            # - the client is configured to use synchronous operation
            #
            if not ready or self._async or self._url.scheme in ('ws', 'wss'):
                log.debug("starting async backend to %s", self._address)
                async.workers.start_once()
                self._pending = fmp.RequestStore()
                self._timer   = async.Timer(1, self._pulse)
                self._worker  = async.Worker(lambda jobs: self._run(jobs, authenticator, self._version))
                self._timer.start()
                self._worker.start()
                return

            # At this point we know we don't need and asynchronous worker, we simply create
            # a backend that will last until the client is closed.
            session = authenticator()
            log.debug("authenticated with %s", session)

            log.debug("opening sync backend to %s", self._address)
            self._backend = self._BackendClass(self._address, session)
            self._backend.open(timeout=self._connect_timeout, async=False)

        # There's no worker to fire these events, we use the current thread to emulate the
        # behavior of the asynchronous worker.
        self.emit('open')
        self.emit('connect')
        self.emit('authenticate', session)

    def _close(self, code=None, reason=None, async=False):
        assert code is None or isinstance(code, int), \
            "code must be an integer but %s was found" % type(code)

        assert reason is None or isinstance(reason, str) or isinstance(reason, six.text_type), \
            "reason must be a string but %s was found" % type(reason)

        assert isinstance(async, bool), \
            "async must be a boolean but %s was found" % type(async)

        with self._lock:
            if not self._running:
                return
            self._running = False
            self._version += 1
            timer  = self._timer
            worker = self._worker

            if worker is None:
                # When no worker is available then the client was opened in synchronous
                # mode on an HTTP backend that authenticated with an app key and secret.
                log.debug("closing sync backend with code = %s and reason = %s", code, reason)
                self._backend.close(code, reason)
                self._backend = None
            else:
                # When a worker is available we schedule the closing method to be called
                # on the worker, stop it and wait for it to terminate.
                log.debug("closing async timer with code = %s and reason = %s", code, reason)
                self._timer.stop()
                log.debug("closing async backend with code = %s and reason = %s", code, reason)
                self._worker.stop()
                self._worker = None

        # When the client had an asynchronous worker running we will wait until it completes
        # if the caller has set the join flag to True, otherwise the worker will terminate
        # in the background.
        if worker is not None:
            if not async:
                log.debug("waiting for async backend to terminate")
                timer.join()
                worker.join()
            return

        # There's no worker to fire these events, we use the current thread to emulate the
        # behavior of the asynchronous worker.
        self.emit('disconnect')
        self.emit('close')

    def _request(self, operation, path, params=None, payload=None):
        assert isinstance(operation, int), \
            "operation must be an integer but %s was found" % type(operation)

        assert isinstance(path, tuple) or isinstance(path, list), \
            "path must be a tuple or a list but %s was found" % type(path)

        assert params is None or isinstance(params, dict), \
            "params must be a dict but %s was found" % type(params)

        if params is None:
            params = { }

        timeout = self._request_timeout
        expire  = time.time() + timeout
        path    = [six.text_type(x) for x in path]
        packet  = fmp.Packet(operation, 0, 0, path, params, payload)

        with self._lock:
            if not self._running:
                raise RuntimeError("submitting request to closed client")
            backend = self._backend
            worker  = self._worker
            packet.id, self._idseq = self._idseq, self._idseq + 1

        # No worker is available, the client has direct ownership of the backend, simply
        # sending the request in blocking mode.
        if worker is None:
            return backend.send(packet, timeout=timeout)

        # When a worker is available we schedule the request to be executed
        # asynchronously.
        promise = async.Promise(None)
        with self._lock:
            req = self._pending.store(packet, expire, promise.resolve, promise.reject)
            worker.schedule(None, lambda: req)

        # If the client is configured for asynchronous operations we simply
        # return the promise.
        if self.async:
            return promise

        # The client was configured for synchronous operations we simply wait
        # for the promise to be resolved.
        return promise.wait(timeout)

    def _upload(self, url, params=None, content=None, content_length=None, content_type=None, content_encoding=None, timeout=None, emitter=None):
        uploader = Uploader(
            url              = url,
            params           = params,
            content          = content,
            content_length   = content_length,
            content_type     = content_type,
            content_encoding = content_encoding,
            emitter          = emitter,
        )

        if timeout is None:
            timeout = max(self._request_timeout, content_length / 1000)

        with self._lock:
            if not self._running:
                raise RuntimeError("submitting upload to closed client")
            backend = self._backend
            worker  = self._worker

        if worker is None:
            uploader.headers = backend.headers
            uploader.timeout = timeout
            return uploader.upload()

        uploader.promise = async.Promise(None)
        worker.schedule(None, lambda: uploader)

        if self.async:
            return uploader.promise

        return uploader.promise.wait(timeout)

    def _pulse(self):
        now = time.time()
        exp = [ ]

        # Every second the pulse method gets called and the client checks for expired
        # requests.
        with self._lock:
            for req in self._pending:
                if req.expire <= now:
                    exp.append(req)
            for req in exp:
                log.debug("request with packet id %s timed out", req.packet.id)
                self._pending.load(req.packet)
                self._worker.schedule(None, req.timeout)

    def _run(self, jobs, authenticator, version):
        # This method is executed by the asynchronous worker when once is started,
        # here's a quick description of the different execution states it goes
        # through:
        #
        # 1. Authentication
        #
        # Before being able to perform any operation the client needs to authenticate
        # against the Frankly API.
        # If unsuccessful the worker will give up and retry later on, unless the client
        # is closed in between.
        #
        # 2. Connection
        #
        # Once authenticated the client establishes a connection to the Frankly API.
        # On WebSocket backends this is when the handshake is performed, for HTTP this
        # steps simply triggers the 'open' event.
        #
        # 3. Schedules pending requests
        #
        # There may be packets pending to be sent that will be pushed over the newly
        # available backend. This ensures automatic retries as long as the request
        # wasn't timed out.
        #
        # 4. Process new jobs
        #
        # When reaching this state the worker waits for new jobs to get schduled, this
        # state will be maintained until the backend loses connection or the client is
        # closed.
        #
        # 5. Closing
        #
        # When the client is closed the backend needs to be shutdown as well, this is
        # the final state. Note that the worker doesn't reach this state if it detects
        # a connection loss from the backend, in that case it goes back to step 1.
        backend = None
        session = None
        delay   = 0

        def incr_delay(delay):
            return min(15, max(1, 2 * delay))

        def on_open():
            jobs.push(self.emit, 'connect')

        def on_close(code, reason):
            jobs.push(self.emit, 'disconnect')

        def on_signal(packet):
            if packet.type == fmp.UPDATE:
                jobs.push(self.emit, 'update', model.build(packet.path, packet.payload))
                return
            if packet.type == fmp.DELETE:
                jobs.push(self.emit, 'delete', model.build(packet.path, packet.payload))
                return

        def on_response(packet):
            with self._lock:
                req = self._pending.load(packet)
            if req is not None:
                if packet.type == fmp.OK:
                    jobs.push(req.resolve, packet.payload)
                else:
                    status = packet.payload.status
                    reason = packet.payload.error
                    jobs.push(req.reject, errors.Error(packet.operation, packet.path, status, reason))
                    if status == 401:
                        jobs.push(lambda: 'break')

        def on_packet(packet):
            if packet.id == 0:
                on_signal(packet)
            else:
                on_response(packet)

        while self._version_match(version):
            # On the first pass delay is zero so this call returns immediately.
            # The delay gets increased if authenticating or connecting fails.
            for _ in range(delay):
                if not self._version_match(version):
                    return
                time.sleep(1)

            # 1. Authentication
            try:
                session = authenticator()
            except Exception as e:
                delay = incr_delay(delay)
                log.exception(e)
                self.emit('error', e)
                continue
            log.debug("authenticated with %s", session)

            # 2. Connection
            try:
                backend = self._BackendClass(self._address, session)
                backend.on('open', on_open)
                backend.on('close', on_close)
                backend.on('packet', on_packet)
                backend.open(timeout=self._connect_timeout, async=True)
            except Exception as e:
                delay = incr_delay(delay)
                log.exception(e)
                self.emit('error', e)
                continue
            delay = 0

            # 3. Schedule pending packets
            with self._lock:
                jobs.clear()

                if version != self._version:
                    backend.remove_event_listeners(None, on_open, on_close, on_packet)
                    backend.close(None, None)
                    return
                for req in self._pending:
                    packet = req.packet
                    jobs.push(lambda: req)

            # 4. Process new jobs
            for job in jobs:
                todo = job()

                if todo is None:
                    continue

                if isinstance(todo, fmp.Request):
                    req = todo
                    try:
                        packet = copy(req.packet)

                        if packet.seed == 0:
                            req.packet.seed = session.info.seed

                        elif packet.seed == session.info.seed:
                            packet = copy(packet)
                            packet.seed = 0

                        log.debug("sending pending %s", packet)
                        backend.send(packet, timeout=self._request_timeout)
                    except Exception as e:
                        delay = incr_delay(delay)
                        log.exception(e)

                        # Something went wrong while submitting the request, we must reject
                        # the associated request.
                        with self._lock:
                            req = self._pending.load(packet)
                        if req is not None:
                            req.reject(e)

                        self.emit('error', e)
                        break

                elif isinstance(todo, Uploader):
                    uploader = todo
                    uploader.headers = backend.headers
                    async.workers.schedule(None, uploader.upload)

                elif isinstance(todo, six.text_type):
                    if todo == 'break':
                        # We got a 401, the current session expired, we'll go ahead and
                        # re-authenticate.
                        break

                if not backend.opened:
                    backend = None
                    delay = incr_delay(delay)
                    break

            # If the backend is still available then we existed the job processing
            # loop because the client got closed, in that case we need to close the
            # backend ourselves.
            if backend is not None:
                backend.remove_event_listeners(None, on_open, on_close, on_packet)
                backend.close(None, None)
                self.emit('disconnect')

            # We don't want to carry jobs from the current session to the next,
            # in case the job processing loop existed because the backend connection
            # was lost there may be pending jobs that we have to drop.
            jobs.clear()
            session = None
            backend = None

        # 5. Closing
        with self._lock:
            if self._version != version:
                return
            exp = [req for req in self._pending]
            self._pending.clear()

        for req in exp:
            req.cancel()

        self.emit('close')

    def _version_match(self, version):
        with self._lock:
            return version == self._version

class EventIterator(events.Iterator):

    def __init__(self, client):
        events.Iterator.__init__(self, client, 'open', 'close', 'connect', 'disconnect', 'authenticate', 'update', 'delete')

    def __iter__(self):
        for name, args, kwargs in events.Iterator.__iter__(self):
            yield name, args, kwargs
            if name == 'close':
                self.stop()
                break

        for _ in events.Iterator.__iter__(self):
            pass

class Uploader(object):

    def __init__(self, url=None, params=None, content=None, content_length=None, content_type=None, content_encoding=None, emitter=None, headers=None, timeout=None, promise=None):
        self.url              = urlparse(url)
        self.params           = params
        self.content          = content
        self.content_length   = content_length
        self.content_type     = content_type
        self.content_encoding = content_encoding
        self.emitter          = emitter
        self.headers          = headers
        self.timeout          = timeout
        self.promise          = promise

    def upload(self):
        headers = copy(self.headers)

        if self.content_length is not None:
            headers['Content-Length'] = self.content_length

        if self.content_type is not None:
            headers['Content-Type'] = self.content_type

        if self.content_encoding is not None:
            headers['Content-Encoding'] = self.content_encoding

        try:
            response = requests.put(
                url     = urlunparse(self.url),
                params  = self.params,
                headers = headers,
                data    = FileProgressUpload(self.content, self.content_length, self.emitter),
                timeout = self.timeout
            )
        except Exception as e:
            self.promise.reject(errors.Error('upload', self.url.path, 500, str(e)))
            return

        status = response.status_code
        result = http.decode_response_payload(response.text)

        if status != 200:
            self.promise.reject(errors.Error('upload', self.url.path, status, result))
            return

        self.promise.resolve(result)

class FileProgressUpload(object):

    def __init__(self, content_object, content_length=None, emitter=None):
        if isinstance(content_object, bytes):
            content_object = six.BytesIO(content_object)

        elif isinstance(content_object, str):
            content_object = six.StringIO(content_object)

        assert hasattr(content_object, 'read'), \
            "file uploads require a file-like object with a read method but %s was found" % type(content_object)

        self.fileobj = content_object
        self.length  = content_length
        self.upload  = 0
        self.emitter = emitter

    def read(self, size):
        data = self.fileobj.read(size)

        if self.emitter is not None:
            if len(data) == 0:
                if self.upload == 0:
                    self.emitter.emit('progress', 0, self.length)
                self.emitter.emit('end', self.upload)
            else:
                self.upload += len(data)
                self.emitter.emit('progress', self.upload, self.length)

        return data

    def close(self):
        if hasattr(self.fileobj, 'close'):
            self.fileobj.close()
