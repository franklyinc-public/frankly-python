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

import frankly
import logging
import os
import time
import unittest

APP_HOST   = os.getenv('FRANKLY_APP_HOST', 'https://app.franklychat.com')
APP_KEY    = os.getenv('FRANKLY_APP_KEY')
APP_SECRET = os.getenv('FRANKLY_APP_SECRET')
APP_URL    = urlparse(APP_HOST)

if APP_URL.scheme == 'http':
    APP_HOST = 'ws://' + APP_URL.netloc
if APP_URL.scheme == 'https':
    APP_HOST = 'wss://' + APP_URL.netloc

def make_client(role='admin'):
    client = frankly.Client(APP_HOST)
    client.open(APP_KEY, APP_SECRET, role=role)
    return client

class TestWebSocketClient(unittest.TestCase):

    def test_01_session(self):
        with make_client() as client:
            session = client.read_session()
            self.assertEqual(session.platform, 'python')
            self.assertEqual(session.role, 'admin')
            self.assertEqual(session.version, 1)
            self.assertNotEqual(session.app.id, 0)
            self.assertNotEqual(session.user.id, 0)
            self.assertNotEqual(session.app.id, None)
            self.assertNotEqual(session.user.id, None)
            self.assertNotEqual(session.created_on, None)
            self.assertNotEqual(session.updated_on, None)
            self.assertNotEqual(session.expires_on, None)

    def test_02_app(self):
        with make_client() as client:
            session = client.read_session()
            app = client.read_app(session.app.id)
            self.assertEqual(session.app, app)

    def test_03_self(self):
        with make_client() as client:
            session = client.read_session()
            user = client.read_user(session.user.id)
            self.assertEqual(session.user, user)

    def test_04_user(self):
       with make_client() as client:
            user = client.create_user(
                display_name    = 'R2D2',
                partner_user_id = 'r2d2',
            )

            try:
                view = client.read_user(user.id)
                self.assertEqual(user, view)

                view = client.update_user(
                    user.id,
                    display_name = 'beepbeep',
                )
                self.assertEqual(view.display_name, 'beepbeep')
            finally:
                client.delete_user(user.id)

            self.assertRaises(frankly.Error, client.read_user, user.id)

    def test_05_messages(self):
        with make_client() as client:
            r2d2 = None
            c3po = None
            hoth = client.create_room(
                status       = 'active',
                title        = 'Hoth',
                description  = 'A cold planet',
            )

            try:
                r2d2 = client.create_user(
                    display_name    = 'R2D2',
                    partner_user_id = 'r2d2',
                )

                c3po = client.create_user(
                    display_name    = 'C3PO',
                    partner_user_id = 'c3po',
                )

                with frankly.Client(APP_HOST) as c1, frankly.Client(APP_HOST) as c2:
                    c1.open(frankly.identity_token_generator(APP_KEY, APP_SECRET, uid='r2d2'))
                    c2.open(frankly.identity_token_generator(APP_KEY, APP_SECRET, uid='c3po'))

                    c1.create_room_participant(hoth.id, r2d2.id)
                    c2.create_room_participant(hoth.id, c3po.id)

                    with frankly.EventIterator(c2) as events:
                        msg = c1.create_room_message(
                            hoth.id,
                            contents = [{ 'type': 'text/plain', 'value': 'beepbeep' }],
                        )

                        for name, args, kwargs in events:
                            if name == 'update':
                                signal = args[0]
                                self.assertEqual(signal.type, 'room-message')
                                self.assertEqual(signal.room.id, hoth.id)
                                self.assertEqual(signal.message.id, msg.id)
                                break
            finally:
                if r2d2 is not None: client.delete_user(r2d2.id)
                if c3po is not None: client.delete_user(c3po.id)
                client.delete_room(hoth.id)

    def test_06_upload(self):
        with make_client() as client:
            events = {
                'progress' : False,
                'end'      : False,
            }

            def on_progress(sent, total):
                events['progress'] = True

            def on_end(total):
                events['end'] = True

            emitter = frankly.EventEmitter()
            emitter.on('progress', on_progress)
            emitter.on('end', on_end)

            file_info = client.upload_file_from_path('test/images/094b468.png', timeout=5, emitter=emitter)
            self.assertNotEqual(file_info.url, None)
            self.assertTrue(events['progress'])
            self.assertTrue(events['end'])
