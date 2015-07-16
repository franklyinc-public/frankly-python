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
import frankly.async
import logging
import os
import time
import unittest

frankly.async.workers.start_once()
parallel_do = frankly.async.workers.do

logging.getLogger('frankly').setLevel(logging.DEBUG)

APP_HOST   = os.getenv('FRANKLY_APP_HOST', 'https://app.franklychat.com')
APP_KEY    = os.getenv('FRANKLY_APP_KEY')
APP_SECRET = os.getenv('FRANKLY_APP_SECRET')
APP_URL    = urlparse(APP_HOST)

if APP_URL.scheme == 'ws':
    APP_HOST = 'http://' + APP_URL.netloc
if APP_URL.scheme == 'wss':
    APP_HOST = 'https://' + APP_URL.netloc

def make_client(role='admin'):
    client = frankly.Client(APP_HOST)
    client.open(APP_KEY, APP_SECRET, role=role)
    return client

class TestHttpClient(unittest.TestCase):

    def test_01_read_session(self):
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

    def test_02_read_app(self):
        with make_client() as client:
            session = client.read_session()
            app = client.read_app(session.app.id)
            self.assertEqual(session.app, app)

    def test_03_read_self(self):
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

    def test_05_user_ban(self):
        with make_client() as client:
            clients = [ ]
            users = [ ]
            room = None

            try:
                for i in range(12):
                    uid = 'c3po-%s' % i
                    usr = client.create_user(display_name='C3PO', partner_user_id=uid, role='regular')
                    usr.partner_user_id = uid
                    users.append(usr)

                room = client.create_room(
                    status      = 'active',
                    title       = 'spaceship',
                    description = 'the spaceship from starwars!',
                )

                try:
                    for u in users:
                        clients.append(frankly.Client(APP_HOST))

                    for c, u in zip(clients, users):
                        c.open(frankly.identity_token_generator(APP_KEY, APP_SECRET, uid=u.partner_user_id))

                    message = clients[0].create_room_message(
                        room.id,
                        contents = [{'type': 'text/plain', 'value': 'Hello World!'}],
                    )

                    parallel_do(lambda c: c.create_room_message_flag(room.id, message.id), clients[1:])
                    time.sleep(1)

                    # This will only work if the auto-ban threshold is set to 10 on the app.
                    ban_status = clients[0].read_user_ban(users[0].id)
                    self.assertTrue(ban_status.banned)
                finally:
                    parallel_do(frankly.Client.close, clients)

            finally:
                if room is not None:
                    client.delete_room(room.id)

                parallel_do(lambda id: client.delete_user(id), [u.id for u in users])

    def test_06_rooms(self):
        with make_client() as client:
            room = client.create_room(
                status      = 'unpublished',
                title       = 'Best Room Ever',
                description = 'This is the best room ever!!!',
            )

            try:
                self.assertEqual(room.status, 'unpublished')
                self.assertEqual(room.title, 'Best Room Ever')
                self.assertEqual(room.description, 'This is the best room ever!!!')
                self.assertEqual(room.avatar_image_url, None)
                self.assertEqual(room.featured_image_url, None)
                self.assertEqual(room.featured, False)
                self.assertEqual(room.version, 1)
                self.assertNotEqual(room.created_on, None)
                self.assertNotEqual(room.updated_on, None)

                room = client.update_room(
                    room.id,
                    title       = 'Not the best room ever',
                    description = 'Not the best room ever...',
                )
                self.assertEqual(room.title, 'Not the best room ever')
                self.assertEqual(room.description, 'Not the best room ever...')

                room = client.update_room(room.id, status='active')
                self.assertEqual(room.status, 'active')

                room = client.update_room(room.id, status='inactive')
                self.assertEqual(room.status, 'inactive')

                rooms = client.read_room_list()
                self.assertEqual(len(rooms), 1)
                self.assertEqual(rooms[0], room)

                room1 = client.read_room(room.id)
                self.assertEqual(room1, room)
            finally:
                client.delete_room(room.id)

            self.assertRaises(frankly.Error, client.read_room, room.id)

    def test_07_room_owner(self):
        with make_client() as client:
            session = client.read_session()

            room = client.create_room(
                availability = 'private',
                status       = 'active',
                title        = 'Room with owner',
            )

            try:
                owners = client.read_room_owner_list(room.id)
                self.assertEqual(len(owners), 1)
                self.assertEqual(owners[0], session.user)

                try:
                    user = client.create_user(
                        partner_user_id = 'whatever',
                    )

                    client.create_room_owner(room.id, user.id)
                    owners = client.read_room_owner_list(room.id)
                    self.assertEqual(len(owners), 2)
                    self.assertEqual(owners[0], session.user)
                    self.assertEqual(owners[1], user)

                    client.delete_room_owner(room.id, user.id)
                    owners = client.read_room_owner_list(room.id)
                    self.assertEqual(len(owners), 1)
                    self.assertEqual(owners[0], session.user)
                finally:
                    client.delete_user(user.id)
            finally:
                client.delete_room(room.id)

            self.assertRaises(frankly.Error, client.read_room_owner_list, room.id)

    def test_08_room_member(self):
        with make_client() as client:
            session = client.read_session()

            room = client.create_room(
                availability = 'private',
                status       = 'active',
                title        = 'Room with owner',
            )

            try:
                client.create_room_moderator(room.id, session.user.id)

                members = client.read_room_member_list(room.id)
                self.assertEqual(len(members), 0)

                user1 = None
                user2 = None
                try:
                    user1 = client.create_user(
                        partner_user_id = '42',
                        display_name    = 'User 1',
                    )

                    user2 = client.create_user(
                        partner_user_id = '24',
                        display_name    = 'User 2',
                    )

                    client.create_room_member(room.id, user1.id)
                    client.create_room_member(room.id, user2.id)
                    members = client.read_room_member_list(room.id)
                    self.assertEqual(len(members), 2)
                    self.assertEqual(members[0], user1)
                    self.assertEqual(members[1], user2)

                    client.delete_room_member(room.id, user1.id)
                    members = client.read_room_member_list(room.id)
                    self.assertEqual(len(members), 1)
                    self.assertEqual(members[0], user2)
                finally:
                    if user1 is not None: client.delete_user(user1.id)
                    if user2 is not None: client.delete_user(user2.id)
            finally:
                client.delete_room(room.id)

            self.assertRaises(frankly.Error, client.read_room_owner_list, room.id)

    def test_09_room_announcer(self):
        with make_client() as client:
            session = client.read_session()

            room = client.create_room(
                availability = 'private',
                status       = 'active',
                title        = 'Room with owner',
            )

            try:
                client.create_room_moderator(room.id, session.user.id)

                announcers = client.read_room_announcer_list(room.id)
                self.assertEqual(len(announcers), 0)

                user1 = None
                user2 = None
                try:
                    user1 = client.create_user(
                        partner_user_id = '42',
                        display_name    = 'User 1',
                    )

                    user2 = client.create_user(
                        partner_user_id = '24',
                        display_name    = 'User 2',
                    )

                    client.create_room_announcer(room.id, user1.id)
                    client.create_room_announcer(room.id, user2.id)
                    announcers = client.read_room_announcer_list(room.id)
                    self.assertEqual(len(announcers), 2)
                    self.assertEqual(announcers[0], user1)
                    self.assertEqual(announcers[1], user2)

                    client.delete_room_announcer(room.id, user1.id)
                    announcers = client.read_room_announcer_list(room.id)
                    self.assertEqual(len(announcers), 1)
                    self.assertEqual(announcers[0], user2)
                finally:
                    if user1 is not None: client.delete_user(user1.id)
                    if user2 is not None: client.delete_user(user2.id)
            finally:
                client.delete_room(room.id)

            self.assertRaises(frankly.Error, client.read_room_owner_list, room.id)

    def test_10_messages(self):
        with make_client() as client:
            room = client.create_room(
                status = 'active',
                title  = 'Room A',
            )

            try:
                messages_created = [ ]

                for i in range(3):
                    c = { 'type': 'text/plain', 'value': 'message %s' % i }
                    m = client.create_room_message(
                        room.id,
                        contents = [c],
                    )
                    self.assertEqual(m.contents, [c])
                    self.assertNotEqual(m.created_on, None)
                    self.assertNotEqual(m.updated_on, None)
                    self.assertNotEqual(m.sent_on, None)
                    messages_created.append(m)

                messages_fetched = client.read_room_message_list(room.id)
                self.assertEqual(len(messages_created), len(messages_fetched))

                for m1, m2 in zip(messages_created, messages_fetched):
                    self.assertEqual(m1, m2)

            finally:
                client.delete_room(room.id)

    def test_11_announcements(self):
        with make_client() as client:
            r1 = None
            r2 = None
            a1 = None
            a2 = None

            try:
                r1 = client.create_room(
                    status = 'active',
                    title  = 'Room A',
                )

                r2 = client.create_room(
                    status = 'active',
                    title  = 'Room B',
                )

                a1 = client.create_announcement(
                    contents = [{ 'type': 'text/plain', 'value': 'Hello World!' }],
                    sticky   = True,
                )
                self.assertEqual([a1], client.read_announcement_list())

                a2 = client.read_announcement(a1.id)
                self.assertEqual(a1, a2)

                client.create_room_message(r1.id, announcement=a1.id)
                client.create_room_message(r2.id, announcement=a2.id)

                rooms = client.read_announcement_room_list(a1.id)
                self.assertEqual(rooms, [r1, r2])

            finally:
                if r1 is not None:
                    client.delete_room(r1.id)

                if r2 is not None:
                    client.delete_room(r2.id)

                if a1 is not None:
                    client.delete_announcement(a1.id)

            self.assertRaises(frankly.Error, client.read_announcement, a1.id)
