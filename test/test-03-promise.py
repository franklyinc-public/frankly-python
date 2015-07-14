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

import frankly.async as async
import unittest

async.workers.start_once()

class TestPromise(unittest.TestCase):

    def test_01_success(self):
        # If the promise gets properly resolved then the test will not block.
        promise = async.Promise(lambda x: x, True)
        self.assertTrue(promise.wait(timeout=1))

    def test_02_failure(self):
        # If the promise gets properly rejected then the test will not block.
        def callback():
            raise AssertionError
        promise = async.Promise(callback)
        self.assertRaises(AssertionError, promise.wait, timeout=1)

    def test_03_resolve(self):
        promise = async.Promise(None)
        promise.resolve(True)
        self.assertTrue(promise.wait(timeout=1))

    def test_04_reject(self):
        promise = async.Promise(None)
        promise.reject(AssertionError())
        self.assertRaises(AssertionError, promise.wait, timeout=1)
