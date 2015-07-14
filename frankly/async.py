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

import copy
import functools
import multiprocessing
import six
import sys
import threading

from . import logger as log

__all__ = [
    'Promise',
    'Timer',
    'Worker',
    'WorkerPool',
    'WorkerQueue',
    'workers',
    'once',
]

class OnceState(object):

    def __init__(self):
        self.lock   = threading.Lock()
        self.done   = False
        self.result = None
        self.error  = None

def once(f):
    state = OnceState()
    @functools.wraps(f)
    def _(*args, **kwargs):
        with state.lock:
            if state.done:
                if state.error is not None:
                    raise copy.deepcopy(state.error)
                return state.result
            state.done = True
            try:
                state.result = f(*args, **kwargs)
            except:
                state.error = sys.exc_info()[1]
                raise
            return state.result
    return _

class Promise(object):

    def __init__(self, callback, *args, **kwargs):
        self._lock    = threading.Lock()
        self._event   = threading.Event()
        self._result  = None
        self._resolve = None
        self._reject  = None

        if callback is None:
            return

        workers.pick().schedule(None, self._run, callback, *args, **kwargs)

    def wait(self, timeout=None):
        if not self._event.wait(timeout):
            raise RuntimeError("Promise.wait timed out")
        ok, ex = self._result
        if ex is None:
            return ok
        raise ex

    def then(self, resolve, reject):
        assert resolve is not None, "Promise.then: the resolve callback cannot be None"
        assert reject is not None, "Promise.then: the reject callback cannot be None"

        with self._lock:
            self._resolve = resolve
            self._reject  = reject

            if self._result is not None:
                self._notify()

    def resolve(self, value):
        with self._lock:
            if self._result is not None:
                raise RuntimeError("the promise was already resolved")
            self._result = (value, None)
            resolve = self._resolve
        self._event.set()
        if resolve is not None:
            self._notify()

    def reject(self, value):
        with self._lock:
            if self._result is not None:
                raise RuntimeError("the promise was already resolved")
            self._result = (None, value)
            reject = self._reject
        self._event.set()
        if reject is not None:
            self._notify()

    def _run(self, callback, *args, **kwargs):
        result = None
        raised = None

        try:
            result = callback(*args, **kwargs)
        except:
            raised = sys.exc_info()[1]
        self._result = (result, raised)
        self._event.set()

        with self._lock:
            if self._resolve is not None:
                self._notify()

    def _notify(self):
        ok, ex = self._result
        if ex is None:
            self._resolve(ok)
        else:
            self._reject(ex)

class Timer(threading.Thread):

    def __init__(self, interval, target=None):
        threading.Thread.__init__(self, target=self._run)
        self.event    = threading.Event()
        self.target   = self.run if target is None else target
        self.interval = interval

    def __iter__(self):
        interval = self.interval
        while not self.event.wait(timeout=interval):
            t0 = time.now()
            yield t0
            t1 = time.now()
            interval = self.interval - ((t1 - t0) % self.interval)

    def _run(self):
        for _ in self:
            self.run()

    def run(self):
        self.target()

    def stop(self):
        self.event.set()

class WorkerQueue(queue.Queue):

    def __iter__(self):
        # Generator that flushes jobs from the queue and yield them to the caller.
        while True:
            job = self.get()
            if job is None:
                break
            yield job

        # If we reach this point then stop has been called, we make sure to flush
        # the queue to prevent any race condition.
        try:
            while True:
                job = self.get_nowait()
                if job is None:
                    continue
                yield job
        except queue.Empty:
            pass

    def push(self, job, *args, **kwargs):
        self.put(lambda: job(*args, **kwargs), block=False)

    def clear(self):
        try:
            while True:
                self.get_nowait()
        except queue.Empty:
            pass

class Worker(threading.Thread):

    def __init__(self, target=None):
        threading.Thread.__init__(self)
        self.daemon = True
        self.target = self._run if target is None else target
        self.queue  = WorkerQueue()
        self.event  = threading.Event()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()
        self.join()

    def schedule(self, promise, callback, *args, **kwargs):
        if promise is None:
            return self._schedule(callback, *args, **kwargs)
        self._schedule(promise._run, callback, *args, **kwargs)
        return promise

    def _schedule(self, callback, *args, **kwargs):
        if self.event.is_set():
            raise RuntimeError("attempt to push a callback to a worker that was already stopped")
        self.queue.push(callback, *args, **kwargs)

    def stop(self):
        self.event.set()
        self.queue.put(None)

    def run(self):
        self.target(self.queue)

    def _run(self, queue):
        for job in queue:
            try:
                job()
            except Exception as e:
                log.exception(e)

class WorkerPool(object):

    def __init__(self, worker_count=0):
        if worker_count <= 0:
            worker_count = multiprocessing.cpu_count()

        self.lock    = threading.Lock()
        self.index   = 0
        self.workers = [ ]

        for _ in range(worker_count):
            self.workers.append(Worker())

    def __iter__(self):
        return iter(self.workers)

    def __len__(self):
        return len(self.workers)

    def __getitem__(self, index):
        return self.workers[index]

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()
        self.join()

    @once
    def start_once(self):
        self.start()

    def start(self):
        for worker in self:
            worker.start()

    def stop(self):
        for worker in self:
            worker.stop()

    def join(self):
        for worker in self:
            worker.join()

    def schedule(self, promise, callback, *args, **kwargs):
        return self.pick().schedule(promise, callback, *args, **kwargs)

    def pick(self):
        with self.lock:
            index, self.index = self.index, self.index + 1
        return self[index % len(self)]

    def do(self, callback, args):
        return list(self.do_iter(callback, args))

    def do_iter(self, callback, args):
        q = queue.Queue(maxsize=len(args))

        def res_generator():
            for _ in range(len(args)):
                yield q.get()

        def res_callback(res):
            q.put((res, None))

        def err_callback(err):
            q.put((None, err))

        for a in args:
            p = Promise(None)
            p.then(res_callback, err_callback)
            self.schedule(p, callback, a)

        for _ in range(len(args)):
            yield q.get()

workers = WorkerPool()
