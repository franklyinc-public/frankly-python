from __future__ import division
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

from functools import wraps
from frankly import FranklyClient
from frankly import FranklyError
from unittest import TestCase

import os

HOST       = os.getenv('FRANKLY_HOST', 'https://app.franklychat.com')
APP_KEY    = os.getenv('FRANKLY_APP_KEY')
APP_SECRET = os.getenv('FRANKLY_APP_SECRET')

def with_client(f):
    @wraps(f)
    def _(self, *args, **kwargs):
        client, _ = self.auth()
        with client:
            return f(self, client, *args, **kwargs)
    return _

class TestFranklyClient(TestCase):

    def auth(self):
        client = FranklyClient(HOST)
        session = client.open(APP_KEY, APP_SECRET)
        return client, session

    def test_01_authenticate_sucess(self):
        client, session = self.auth()
        try:
            self.assertEqual(session.platform, 'python')
            self.assertEqual(session.role, 'admin')
            self.assertEqual(session.version, 1)
            self.assertNotEqual(session.app_id, None)
            self.assertNotEqual(session.app_user_id, None)
            self.assertNotEqual(session.created_on, None)
            self.assertNotEqual(session.updated_on, None)
            self.assertNotEqual(session.expires_on, None)
        finally:
            client.close()

    def test_02_authenticate_failure(self):
        with FranklyClient(HOST) as client:
            self.assertRaises(FranklyError, client.open, 'key', 'secret')

    @with_client
    def test_03_rooms(self, client):
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
                description = 'Actually not the best room ever.',
            )
            self.assertEqual(room.title, 'Not the best room ever')
            self.assertEqual(room.description, 'Actually not the best room ever.')

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

        self.assertRaises(FranklyError, client.read_room, room.id)

    @with_client
    def test_03_room_images(self, client):
        room = client.create_room(
            status = 'active',
            title  = 'Room with an image',
        )

        try:
            file = client.upload_file_from_path('images/094b468.png', category='roomavatar')

            room = client.update_room(
                room.id,
                avatar_image_url = file.url,
            )
            self.assertEqual(room.avatar_image_url, file.url)

            room = client.update_room(
                room.id,
                featured_image_url = file.url,
                featured           = True,
            )
            self.assertEqual(room.featured_image_url, file.url)
            self.assertEqual(room.featured, True)

        finally:
            client.delete_room(room.id)

    @with_client
    def test_04_messages(self, client):
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

    @with_client
    def test_05_announcements(self, client):
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

            c1 = { 'type': 'text/plain', 'value': 'Hello World!' }
            a1 = client.create_announcement(contents=[c1], contextual=True)
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

        self.assertRaises(FranklyError, client.read_announcement, a1.id)
