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

import frankly.model as model
import frankly.util as util
import unittest

class TestModels(unittest.TestCase):

    def test_room_message(self):
        object1 = util.Object(
            id       = 1234,
            contents = [{ 'type': 'text/plain', 'value': 'Hello World!' }],
        )
        object2 = model.build(('rooms', '42', 'messages', '1234'), object1)
        self.assertEqual(object2.type, 'room-message')
        self.assertEqual(object2.room, util.Object(id=42))
        self.assertEqual(object2.message, object1)

    def test_room_participant(self):
        object1 = util.Object(
            id           = 1234,
            display_name = 'Luke Skywalker',
        )
        object2 = model.build(('rooms', '42', 'participants', '1234'), object1)
        self.assertEqual(object2.type, 'room-participant')
        self.assertEqual(object2.room, util.Object(id=42))
        self.assertEqual(object2.user, object1)

    def test_room_subscriber(self):
        object1 = util.Object(
            id           = 1234,
            display_name = 'Luke Skywalker',
        )
        object2 = model.build(('rooms', '42', 'subscribers', '1234'), object1)
        self.assertEqual(object2.type, 'room-subscriber')
        self.assertEqual(object2.room, util.Object(id=42))
        self.assertEqual(object2.user, object1)

    def test_room_owner(self):
        object1 = util.Object(
            id           = 1234,
            display_name = 'Luke Skywalker',
        )
        object2 = model.build(('rooms', '42', 'owners', '1234'), object1)
        self.assertEqual(object2.type, 'room-owner')
        self.assertEqual(object2.room, util.Object(id=42))
        self.assertEqual(object2.user, object1)

    def test_room_moderator(self):
        object1 = util.Object(
            id           = 1234,
            display_name = 'Luke Skywalker',
        )
        object2 = model.build(('rooms', '42', 'moderators', '1234'), object1)
        self.assertEqual(object2.type, 'room-moderator')
        self.assertEqual(object2.room, util.Object(id=42))
        self.assertEqual(object2.user, object1)

    def test_room_announcer(self):
        object1 = util.Object(
            id           = 1234,
            display_name = 'Luke Skywalker',
        )
        object2 = model.build(('rooms', '42', 'announcers', '1234'), object1)
        self.assertEqual(object2.type, 'room-announcer')
        self.assertEqual(object2.room, util.Object(id=42))
        self.assertEqual(object2.user, object1)

    def test_room_count(self):
        object1 = util.Object(
            active     = 20,
            online     = 10,
            subscribed = 30,
        )
        object2 = model.build(('rooms', '42', 'count'), object1)
        self.assertEqual(object2.type, 'room-count')
        self.assertEqual(object2.room, util.Object(id=42))
        self.assertEqual(object2.count, object1)

    def test_room(self):
        object1 = util.Object(
            id    = 1234,
            title = 'Hoth',
        )
        object2 = model.build(('rooms', '42'), object1)
        self.assertEqual(object2.type, 'room')
        self.assertEqual(object2.room, object1)

    def test_user_ban(self):
        object1 = util.Object(
            banned = True,
        )
        object2 = model.build(('users', '42', 'ban'), object1)
        self.assertEqual(object2.type, 'user-ban')
        self.assertEqual(object2.user, util.Object(id=42))
        self.assertEqual(object2.ban, object1)

    def test_user(self):
        object1 = util.Object(
            id           = 1234,
            display_name = 'Luke Skywalker',
        )
        object2 = model.build(('users', '42'), object1)
        self.assertEqual(object2.type, 'user')
        self.assertEqual(object2.user, object1)

    def test_app(self):
        object1 = util.Object(
            id   = 1234,
            name = 'Star Wars',
        )
        object2 = model.build(('apps', '42'), object1)
        self.assertEqual(object2.type, 'app')
        self.assertEqual(object2.app, object1)

    def test_session(self):
        object1 = util.Object(
            seed = 42,
        )
        object2 = model.build(('session',), object1)
        self.assertEqual(object2.type, 'session')
        self.assertEqual(object2.session, object1)
