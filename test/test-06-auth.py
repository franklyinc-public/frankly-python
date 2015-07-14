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

import frankly.auth as auth
import frankly.errors as errors
import os
import unittest

APP_HOST   = os.environ['FRANKLY_APP_HOST']
APP_KEY    = os.environ['FRANKLY_APP_KEY']
APP_SECRET = os.environ['FRANKLY_APP_SECRET']

class TestAuth(unittest.TestCase):

    def test_auth_01_anonymous(self):
        session = auth.authenticate(
            APP_HOST,
            auth.identity_token_generator(APP_KEY, APP_SECRET, uid=1, role='anonymous'),
        )
        self.assertIn('app-token', session.cookies)
        self.assertEqual('anonymous', session.info.role)

    def test_auth_02_guest(self):
        session = auth.authenticate(
            APP_HOST,
            auth.identity_token_generator(APP_KEY, APP_SECRET, uid=1, role='guest'),
        )
        self.assertIn('app-token', session.cookies)
        self.assertEqual('guest', session.info.role)

    def test_auth_03_regular(self):
        session = auth.authenticate(
            APP_HOST,
            auth.identity_token_generator(APP_KEY, APP_SECRET, uid=1, role='regular'),
        )
        self.assertIn('app-token', session.cookies)
        self.assertEqual('regular', session.info.role)

    def test_auth_04_admin(self):
        session = auth.authenticate(
            APP_HOST,
            auth.identity_token_generator(APP_KEY, APP_SECRET, uid=1, role='admin'),
        )
        self.assertIn('app-token', session.cookies)
        self.assertEqual('admin', session.info.role)

    def test_auth_05_failure(self):
        self.assertRaises(
            errors.Error,
            auth.authenticate,
            APP_HOST,
            auth.identity_token_generator(APP_KEY, 'not my secret', uid=1, role='admin'),
        )
