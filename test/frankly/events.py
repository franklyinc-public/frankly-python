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

from six.moves import queue

import six
import threading

from . import logger as log

__all__ = [
    'Iterator',
    'Emitter',
    'Listener',
]

class Emitter(object):

    def __init__(self, logger=None):
        self._events_cblist = { }
        self._events_lock   = threading.Lock()

    def on(self, name, *callbacks):
        return self.add_event_listeners(name, *callbacks, once=False)

    def once(self, name, *callbacks):
        return self.add_event_listeners(name, *callbacks, once=True)

    def emit(self, name, *args, **kwargs):
        cblist = None
        log.debug("emitting %s event from %s", name, self)

        with self._events_lock:
            try:
                cblist = self._events_cblist[name]
            except KeyError:
                return
            self._events_cblist[name] = [x for x in cblist if not x.once]

        for cb in cblist:
            try:
                cb(*args, **kwargs)
            except Exception as e:
                log.exception(e)

    def add_event_listeners(self, name, *callbacks, **kwargs):
        once = bool(kwargs.get('once'))
        listeners = [Listener(cb, once) for cb in callbacks]

        with self._events_lock:
            for listener in listeners:
                try:
                    self._events_cblist[name].append(listener)
                except KeyError:
                    self._events_cblist[name] = [listener]

    def remove_event_listeners(self, name, *callbacks):
        def remove(name, listeners):
            try:
                cblist = self._events_cblist[name]
                self._events_cblist[name] = [x for x in cblist if x not in listeners]
            except KeyError:
                pass

        listeners = [Listener(cb) for cb in callbacks]

        with self._events_lock:
            if name is not None:
                remove(name, listeners)
            else:
                for name in list(six.iterkeys(self._events_cblist)):
                    remove(name, listeners)

class Listener(object):

    def __init__(self, callback, once=False):
        self.callback = callback
        self.once     = once

    def __call__(self, *args, **kwargs):
        return self.callback(*args, **kwargs)

    def __eq__(self, other):
        return self.callback == other.callback

    def __ne__(self, other):
        return not self.__eq__(other)

class Iterator(object):

    def __init__(self, emitter, *events):
        self._iter_emitter   = emitter
        self._iter_running   = False
        self._iter_queue     = queue.Queue()
        self._iter_lock      = threading.Lock()
        self._iter_callbacks = [ ]

        def callback(name):
            return lambda *args, **kwargs: self._iter_queue.put((name, args, kwargs))

        for event in events:
            self._iter_callbacks.append((event, callback(event)))

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()

    def __iter__(self):
        while True:
            event = self._iter_queue.get()
            if event is None:
                break
            yield event

        try:
            while True:
                event = self._iter_queue.get_nowait()
                if event is not None:
                    yield event
        except queue.Empty:
            pass

    def start(self):
        with self._iter_lock:
            if self._iter_running:
                return
            for event, callback in self._iter_callbacks:
                self._iter_emitter.on(event, callback)
            self._iter_running = True

    def stop(self):
        with self._iter_lock:
            if not self._iter_running:
                return
            for event, callback in self._iter_callbacks:
                self._iter_emitter.remove_event_listeners(event, callback)
            self._iter_running = False
        self._iter_queue.put(None)

    def get(self, block=True, timeout=None):
        return self._iter_queue.get(block=block, timeout=timeout)
