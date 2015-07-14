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

from . import util

__all__ = [
    'build'
]

def build(path, payload):
    for key, builder in MATCH_BUILD:
        if match(path, key):
            return builder(path, payload)

def match(path, key):
    if len(path) != len(key):
        return False

    for p, k in zip(path, key):
        if k is None:
            continue
        if k == p:
            continue
        return False

    return True

def build_room_message(path, payload):
    return util.Object(
        type    = 'room-message',
        room    = util.Object(id=int(path[1])),
        message = payload,
    )

def build_room_participant(path, payload):
    return util.Object(
        type = 'room-participant',
        room = util.Object(id=int(path[1])),
        user = payload,
    )

def build_room_subscriber(path, payload):
    return util.Object(
        type = 'room-subscriber',
        room = util.Object(id=int(path[1])),
        user = payload,
    )

def build_room_owner(path, payload):
    return util.Object(
        type = 'room-owner',
        room = util.Object(id=int(path[1])),
        user = payload,
    )

def build_room_moderator(path, payload):
    return util.Object(
        type = 'room-moderator',
        room = util.Object(id=int(path[1])),
        user = payload,
    )

def build_room_member(path, payload):
    return util.Object(
        type = 'room-member',
        room = util.Object(id=int(path[1])),
        user = payload,
    )

def build_room_announcer(path, payload):
    return util.Object(
        type = 'room-announcer',
        room = util.Object(id=int(path[1])),
        user = payload,
    )

def build_room_count(path, payload):
    return util.Object(
        type  = 'room-count',
        room  = util.Object(id=int(path[1])),
        count = payload,
    )

def build_room(path, payload):
    return util.Object(
        type = 'room',
        room = payload,
    )

def build_user_ban(path, payload):
    return util.Object(
        type = 'user-ban',
        user = util.Object(id=int(path[1])),
        ban  = payload,
    )

def build_user(path, payload):
    return util.Object(
        type = 'user',
        user = payload,
    )

def build_app(path, payload):
    return util.Object(
        type = 'app',
        app  = payload,
    )

def build_session(path, payload):
    return util.Object(
        type    = 'session',
        session = payload,
    )

MATCH_BUILD = (
    (('rooms', None, 'messages', None), build_room_message),

    (('rooms', None, 'participants', None), build_room_participant),

    (('rooms', None, 'subscribers', None), build_room_subscriber),

    (('rooms', None, 'owners', None), build_room_owner),

    (('rooms', None, 'moderators', None), build_room_moderator),

    (('rooms', None, 'members', None), build_room_member),

    (('rooms', None, 'announcers', None), build_room_announcer),

    (('rooms', None, 'count'), build_room_count),

    (('rooms', None), build_room),

    (('users', None, 'ban'), build_user_ban),

    (('users', None), build_user),

    (('apps', None), build_app),

    (('session',), build_session),
)
