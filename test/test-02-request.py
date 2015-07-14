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

import frankly.errors as errors
import frankly.fmp as fmp
import time
import unittest

class TestRequest(unittest.TestCase):

    def test_request_01_resolve(self):
        x = { 'res': None }

        def success():
            x['res'] = True

        def failure():
            x['res'] = False

        req = make_request(success, failure)
        req.resolve()
        self.assertTrue(x['res'])

    def test_request_02_reject(self):
        x = { 'res': None }

        def success():
            x['res'] = True

        def failure():
            x['res'] = False

        req = make_request(success, failure)
        req.reject()
        self.assertFalse(x['res'])

    def test_request_03_timeout(self):
        x = { 'res': None }

        def success():
            x['res'] = True

        def failure(e):
            x['res'] = e

        req = make_request(success, failure)
        req.timeout()

        e = x['res']
        self.assertTrue(isinstance(e, errors.Error))
        self.assertEqual(e.status, 408)

    def test_request_04_cancel(self):
        x = { 'res': None }

        def success():
            x['res'] = True

        def failure(e):
            x['res'] = e

        req = make_request(success, failure)
        req.cancel()

        e = x['res']
        self.assertTrue(isinstance(e, errors.Error))
        self.assertEqual(e.status, 500)

class TestRequestStore(unittest.TestCase):

    def test_request_store_01_store_load(self):
        x = { 'res': None }

        def success(r):
            x['res'] = r

        def failure(r):
            x['res'] = r

        rs = fmp.RequestStore()
        self.assertEqual(len(rs), 0)

        r1 = rs.store(make_packet(1, 1), time.time() + 1000, success, failure)
        r2 = rs.store(make_packet(1, 2), time.time() + 2000, success, failure)
        r3 = rs.store(make_packet(1, 3), time.time() + 3000, success, failure)
        self.assertEqual(len(rs), 3)
        self.assertIs(rs.load(make_packet(1, 4)), None)

        self.assertEqual(rs.load(make_packet(1, 3)), r3)
        self.assertEqual(len(rs), 2)

        self.assertEqual(rs.load(make_packet(1, 2)), r2)
        self.assertEqual(len(rs), 1)

        self.assertEqual(rs.load(make_packet(1, 1)), r1)
        self.assertEqual(len(rs), 0)
        self.assertIs(rs.load(make_packet(1, 1)), None)

    def test_request_store_02_timeout(self):
        x = { 'res': None, 'cnt': 0 }

        def success(r):
            x['res'] = r
            x['cnt'] += 1

        def failure(r):
            x['res'] = r
            x['cnt'] += 1

        rs = fmp.RequestStore()
        t0 = time.time()

        r1 = rs.store(make_packet(1, 1), t0 + 1000, success, failure)
        r2 = rs.store(make_packet(1, 2), t0 + 2000, success, failure)
        r3 = rs.store(make_packet(1, 3), t0 + 3000, success, failure)

        rs.timeout(t0)
        self.assertEqual(len(rs), 3)
        self.assertIs(x['res'], None)

        rs.timeout(t0 + 1500)
        self.assertEqual(len(rs), 2)
        self.assertTrue(isinstance(x['res'], errors.Error))
        self.assertEqual(x['res'].status, 408)
        self.assertEqual(x['cnt'], 1)

        rs.timeout(t0 + 4000)
        self.assertEqual(len(rs), 0)
        self.assertTrue(isinstance(x['res'], errors.Error))
        self.assertEqual(x['res'].status, 408)
        self.assertEqual(x['cnt'], 3)

    def test_request_store_02_cancel(self):
        x = { 'res': None, 'cnt': 0 }

        def success(r):
            x['res'] = r
            x['cnt'] += 1

        def failure(r):
            x['res'] = r
            x['cnt'] += 1

        rs = fmp.RequestStore()
        t0 = time.time()

        r1 = rs.store(make_packet(1, 1), t0 + 1000, success, failure)
        r2 = rs.store(make_packet(1, 2), t0 + 2000, success, failure)
        r3 = rs.store(make_packet(1, 3), t0 + 3000, success, failure)

        rs.cancel()
        self.assertEqual(len(rs), 0)
        self.assertTrue(isinstance(x['res'], errors.Error))
        self.assertEqual(x['res'].status, 500)
        self.assertEqual(x['cnt'], 3)

def make_packet(seed, id):
    return fmp.Packet(0, seed, id, ['path'], { }, None)

def make_request(success, failure):
    return fmp.Request(
        make_packet(1, 42),
        time.time() + 1000,
        success,
        failure,
    )
