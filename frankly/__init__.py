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

import mimetypes
import os
import six
from six.moves import urllib
urlparse = urllib.parse.urlparse

from . import async
from . import logger
from . import version
from . import errors
from . import events
from . import fmp
from . import util
from . import auth
from . import http
from . import ws
from . import core

from .errors import Error
from .events import Emitter as EventEmitter
from .core import BaseClient
from .core import EventIterator
from .util import Object
from .auth import Session
from .auth import generate_identity_token
from .auth import identity_token_generator
from .version import __version__

__all__ = [
    'Client',
    'BaseClient',
    'EventIterator',
    'EventEmitter',
    'Error',
    'Object',
    'Session'
    'generate_identity_token',
    'identity_token_generator',
    '__version__',
]

class Client(BaseClient):
    """
    This class implementations a network client that exposes
    operations in the Frankly API to a python application.

    The typical work flow is to create an instance of Client, use it
    to authenticate, then make method calls to interact with the API.  
    Reusing the same client instance multiple times allows the application to
    avoid wasting time re-authenticating before every operation.

    An application can create multiple instances of this class and authenticate
    with the same or different pairs of `app_key` and `app_secret`, each instance
    is independant from the other ones.

    Each instance of Client maintains its own connection pool to Frankly
    servers, if client is not required anymore the application should call the
    `close` method to release system resources.  
    A client should not be used anymore after being closed.  
    Note that instances of Client can be used as context managers to
    automatically be closed when exiting the `with` statement.

    **[thread safety]**  
    Python application using threads or libraries like [gevent](http://www.gevent.org/)
    can share instances of Client between multiple threads/coroutines
    only after sucessfuly authenticating.
    """

    def __init__(self, address='https', connect_timeout=5, request_timeout=5, async=False):
        """
        Creates a new instance of this class.

        **Arguments**

        - `address (str)`  
        The URL at which Frankly servers can be reached, it's very unlikely that
        an application would need to change this value.

        - `connect_timeout (int or float)`  
        The maximum amount of time that connecting to the API can take (in seconds).

        - `request_timeout (int or float)`  
        The maximum amount of time that submitting a request and receiving a response
        from the API can take (in seconds).

        - `async` (bool)
        When set to True, every method call that access the Frankly API will return
        immediately with a `frankly.Promise` that resolves with the result of the
        operation or is rejected with the error that got generated.  
        If callbacks are set on the promise through `frankly.Promise.then` they will
        be called from a different thread.
        """
        if not (isinstance(address, str) or isinstance(address, six.text_type)):
            raise TypeError("address must be a string")

        if not (isinstance(connect_timeout, int) or isinstance(connect_timeout, float)):
            raise TypeError("connect timeout must be a int or float")

        if not (isinstance(request_timeout, int) or isinstance(request_timeout, float)):
            raise TypeError("request timeout must be a int or float")

        if connect_timeout < 0:
            raise ValueError("connect timeout must be a positive value")

        if request_timeout < 0:
            raise ValueError("request timeout must be a positive value")

        if address == 'https':
            address = 'https://app.franklychat.com'
        elif address == 'wss':
            address = 'wss://app.franklychat.com'

        url = urlparse(address)

        if url.scheme not in ('http', 'https', 'ws', 'wss'):
            raise ValueError("unsupported protocol: " + address)

        BaseClient.__init__(self, url, connect_timeout, request_timeout, async)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    @property
    def address(self):
        """
        This property exposes the address at which this client connects to the
        Frankly API.
        """
        # declared in core.BaseClient
        return self._address

    @property
    def async(self):
        """
        This property is True if the client is configure to submit asynchronous
        requests to the Frankly API (method calls return promises instead of the
        actual result).
        """
        # declared in core.BaseClient
        return self._async

    def open(self, *args, **kwargs):
        """
        This should be the first method called on an instance of Client,
        after succesfully returning the client can be used to interact with the
        Frankly API.

        **Arguments**

        *(one argument)*

        - `args[0]: identity_token_generator (function)`
        If a single argument is given it is expected to be a function that receives
        a nonce value and returns an identity token that carries user credentials.

        *(two arguments)*

        - `args[0]: app_key (str)`  
        The key that specifies which app this client is authenticating for, this
        value is provided by the Frankly Console.

        - `args[1]: app_secret (str)`  
        The secret value associated with the key that allows the client to securely
        authenticate against the Frankly API.

        **Return**

        On success the method returns a session object which contains two fields,
        `app_id` with the identifier of the application this client has
        authenticated for, and `app_user_id` with the identifier of the actual
        user this client will run as.
        """
        argc = len(args)

        if argc == 1:
            return self._open_with_identity_token_generator(args[0], **kwargs)

        elif argc == 2:
            return self._open_with_key_and_secret(args[0], args[1], **kwargs)

        raise TypeError("frankly.Cient.open takes either 1 or 2 arguments but %s were found" % argc)

    def close(self, code=None, reason=None, async=False):
        """
        Shuts down all connections and releases system resources held by this
        client object.  
        The instance should not be used anymore after calling this method.

        **Arguments**

        - `code` (int)
        An integer code representing why the client is being closed, on
        websocket connections this gets sent to the server in the closing
        frame.

        - `reason` (str)
        A human-readable string that describes why the client is being closed,
        on websocket connections this gets sent to the server in the closing
        frame.

        - `async` (bool)
        If set to *True* the method call will return immediately after
        initiating the client termination, otherwise the method will block
        until connections have been shutdown and the internal client state
        had been cleared.
        """
        return self._close(code, reason, async)

    def create(self, path, params=None, payload=None):
        """
        This method exposes a generic interface for creating objects through
        the Frankly API.  
        Every `create_*` method is implemented on top of this one.

        **Arguments**

        - `path (list)`  
        A list of values representing the collection to create an object in.

        - `params (dict)`  
        Parameters passed as part of the request.

        - `payload (dict)`  
        Dict-like object representing the object to create.

        **Return**

        The method returns an object representing the newly created object.
        """
        return self._request(fmp.CREATE, path, params, payload)

    def create_announcement(self, **payload):
        """
        Creates a new announcement object in the app.  
        The properties of that new announcement are given as keyword arguments
        to the method.

        **Arguments**

        - `contents (list)`  
        A list of content objects representing what will be embedded into the
        messages once the announcement is published to one or more rooms.  
        Refer to the *Announcement* and *Message* sections of the docuementation
        for more details about the content objects.

        - `sticky (bool)`  
        True if the announcement should be published as a Sticky Message, false if
        it should be published as a regular message

        **Return**

        The method returns an object representing the newly created announcement.
        """
        return self.create(('announcements',), payload=payload)

    def create_file(self, **payload):
        """
        Creates a new file object on Frankly servers and returns that object.  
        The properties of that new file are given as keyword argumenst to the
        method.

        **Arguments**

        - `category (str)`  
        One of the file categories supported by the API (see the *File* section
        of the documentation).

        - `type (str)`  
        One of the file types supported by the API (see the *File* section of
        the documentation).

        **Return**

        The method returns an object representing the newly created file.
        """
        return self.create(('files',), payload=payload)

    def create_room(self, **payload):
        """
        Creates a new room object in the app and return that object.  
        The properties of that new room are given as keyword arguments to the
        method.

        **Arguments**

        - `title (str)`  
        The title associated with this room.

        - `status (str)`  
        One of `'unpublished'`, `'active'` or `'inactive'`. See the *ROOMS* section
        above for more information about each status.

        - `description (str)`  
        A description of what this chat room is intended for. It is usually a
        short description of the room's discussion topics.

        - `avatar_image_url (str)`  
        The URL of an image to use when the room is displayed in a mobile or web app.

        - `featured_image_url (str)`  
        The URL of an image to use when the room is featured in a mobile or web app.

        - `featured (bool)`  
        True if this room should be featured in the mobile or web app, false otherwise.

        **Return**

        The method returns an object representing the newly created room.
        """
        return self.create(('rooms',), payload=payload)

    def create_room_message(self, room_id, **payload):
        """
        Creates a new message object in the room with id specified as first
        argument.  
        The properties of that new message are given as keyword arguments to the
        method.

        **Arguments**

        - `contents (list)`  
        A list of content objects representing what will be embedded into the
        messages once the announcement is published to one or more rooms.  
        Refer to the *Announcement* and *Message* sections of the docuementation
        for more details about content objects.

        **Return**

        The method returns an object representing the newly created message.
        """
        params = {  }

        for key in ('announcement',):
            if key in payload:
                params[key] = payload[key]
                del payload[key]

        return self.create(('rooms', room_id, 'messages'), params=params, payload=payload)

    def create_room_message_flag(self, room_id, message_id):
        return self.create(('rooms', room_id, 'messages', message_id, 'flag'))

    def create_room_owner(self, room_id, user_id):
        return self.create(('rooms', room_id, 'owners', user_id))

    def create_room_moderator(self, room_id, user_id):
        return self.create(('rooms', room_id, 'moderators', user_id))

    def create_room_member(self, room_id, user_id):
        return self.create(('rooms', room_id, 'members', user_id))

    def create_room_announcer(self, room_id, user_id):
        return self.create(('rooms', room_id, 'announcers', user_id))

    def create_room_subscriber(self, room_id, user_id):
        return self.create(('rooms', room_id, 'subscribers', user_id))

    def create_room_participant(self, room_id, user_id):
        return self.create(('rooms', room_id, 'participants', user_id))

    def create_user(self, **payload):
        return self.create(('users',), payload=payload)

    def delete(self, path, params=None, payload=None):
        """
        This method exposes a generic interface for deleting objects through
        the Frankly API.  
        Every `delete_*` method is implemented on top of this one.

        **Arguments**

        - `path (list)`  
        A list of values representing the collection to create an object in.

        - `params (dict)`  
        Parameters passed as part of the request.

        - `payload (dict)`  
        Dict-like object representing the object to create.
        """
        return self._request(fmp.DELETE, path, params, payload)

    def delete_announcement(self, announcement_id):
        """
        Deletes the announcement object with the id sepecified in the first argument.

        Note that deleting an announcement does not remove the announcement from the
        rooms that it has already been published to.

        This operation cannot be undone!

        **Arguments**

        - `announcement_id (int)`  
        The identifier of the announcement to delete.
        """
        return self.delete(('announcements', announcement_id))

    def delete_room(self, room_id):
        """
        Deletes the room object with the id specified in the first argument.

        Note that this will cause all messages sent to this room to be deleted
        as well, a safer approach could be to change the room status to
        `'unpublished'` to hide it without erasing data.

        This operation cannot be undone!

        **Arguments**

        - `room_id (int)`  
        The identifier of the room to delete.

        """
        return self.delete(('rooms', room_id))

    def delete_room_owner(self, room_id, user_id):
        return self.delete(('rooms', room_id, 'owners', user_id))

    def delete_room_moderator(self, room_id, user_id):
        return self.delete(('rooms', room_id, 'moderators', user_id))

    def delete_room_member(self, room_id, user_id):
        return self.delete(('rooms', room_id, 'members', user_id))

    def delete_room_announcer(self, room_id, user_id):
        return self.delete(('rooms', room_id, 'announcers', user_id))

    def delete_room_subscriber(self, room_id, user_id):
        return self.delete(('rooms', room_id, 'subscribers', user_id))

    def delete_room_participant(self, room_id, user_id):
        return self.delete(('rooms', room_id, 'participants', user_id))

    def delete_session(self):
        return self.delete(('session',))

    def delete_user(self, user_id):
        return self.delete(('users', user_id))

    def read(self, path, params=None, payload=None):
        """
        This method exposes a generic interface for reading objects from the
        Frankly API.  
        Every `read_*` method is implemented on top of this one.

        **Arguments**

        - `path (list)`  
        A list of values representing the collection to create an object in.

        - `params (dict)`  
        Parameters passed as part of the request.

        - `payload (dict)`  
        Dict-like object representing the object to create.

        **Return**

        The method returns the object read from the API at the specified path.
        """
        return self._request(fmp.READ, path, params, payload)

    def read_announcement(self, announcement_id):
        """
        Retrieves an announcement object with the id sepecified in first argument.

        **Arguments**

        - `announcement_id (int)`  
        The identifier of the announcement to fetch.

        **Return**

        The method returns an object representing the announcement with the
        specified id.
        """
        return self.read(('announcements', announcement_id))

    def read_announcement_list(self):
        """
        Retrieves the list of announcements that are available in the app.

        **Return**

        The method returns a list of annoucement objects ordered by id, which
        may be empty if there are no announcements in the app.
        """
        return self.read(('announcements',))

    def read_announcement_room_list(self, announcement_id):
        """
        Retrieves the list of rooms that an annoucement has been published to.

        **Arguments**

        - `announcement_id (int)`  
        The identifier of the announcement used to generate the room list.

        **Return**

        The method returns a list of annoucement objects ordered by id, which
        may be empty if there are no announcements in the app or if none have been
        published yet.
        """
        return self.read(('announcements', announcement_id, 'rooms'))

    def read_room(self, room_id):
        """
        Retrieves the room object with the id specified in the first argument.

        **Arguments**

        - `room_id (int)`  
        The identifier of the room to fetch.

        **Return**

        The method returns an object representing the room with the specified id.
        """
        return self.read(('rooms', room_id))

    def read_room_list(self):
        """
        Retrieves the list of all available rooms from the app.

        **Return**

        The method returns a list of room objects ordered by id, which may be
        empty if there are no rooms in the app.
        """
        return self.read(('rooms',))

    def read_room_message(self, room_id, message_id):
        return self.read(('rooms', room_id, 'messages', message_id))

    def read_room_message_list(self, room_id, **params):
        """
        Retrieves messages in a room.  
        The keyword arguments are used to specify which message range the client
        wish to receive.

        **Arguments**

        - `offset (int)`  
        The id of the message to consider as starting offset for the query.  
        If the offset is not specified the server will use the id of the most
        recent message.

        - `limit (int)`  
        How many messages at most will be received by the call. The server may
        choose to send a lower count if that value exceeds the maximum allowed
        or if there are less than the requested number of messages available.  
        If the limit is not set the server will use a default limit instead,
        which means there are no way to retrieve the entire list of messages in
        a room (because that could potentially be few million entries).

        - `sticky (bool)`  
        When set to true, only Sticky Messages will be returned in the result
        list.  
        When set to false, only non Sticky Messages will be returned in the
        result list.
        This argument may be omitted or set to `None`. In that case all
        messages will be returned in the result list.

        **Return**

        The method returns a list of message objects, which may be empty if no
        messages were satisfying the query.
        """
        return self.read(('rooms', room_id, 'messages'), params=params)

    def read_room_owner_list(self, room_id):
        return self.read(('rooms', room_id, 'owners'))

    def read_room_moderator_list(self, room_id):
        return self.read(('rooms', room_id, 'moderators'))

    def read_room_member_list(self, room_id):
        return self.read(('rooms', room_id, 'members'))

    def read_room_announcer_list(self, room_id):
        return self.read(('rooms', room_id, 'announcers'))

    def read_room_subscriber_list(self, room_id):
        return self.read(('rooms', room_id, 'subscribers'))

    def read_room_participant_list(self, room_id):
        return self.read(('rooms', room_id, 'participants'))

    def read_room_count(self, room_id):
        return self.read(('rooms', room_id, 'count'))

    def read_session(self):
        return self.read(('session',))

    def read_user(self, user_id):
        return self.read(('users', user_id))

    def read_user_ban(self, user_id):
        return self.read(('users', user_id, 'ban'))

    def read_app(self, app_id):
        return self.read(('apps', app_id))

    def update(self, path, params=None, payload=None):
        """
        This method exposes a generic interface for updating objects of the
        Frankly API.  
        Every `update_*` method is implemented on top of this one.

        **Arguments**

        - `path (list)`  
        A list of values representing the collection to create an object in.

        - `params (dict)`  
        Parameters passed as part of the request.

        - `payload (dict)`  
        Dict-like object representing the object to create.

        **Return**

        The method returns the object updated on the API at the specified path.
        """
        return self._request(fmp.UPDATE, path, params, payload)

    def update_room(self, room_id, **payload):
        """
        Updates an existing room object in the app and returns that object.  
        The room properties to update are given as keyword arguments to the
        method.

        **Arguments**

        - `room_id (int)`  
        The identifier of the room to update.

        - `title (str)`  
        The title associated to this room.

        - `status (str)`  
        One of `'unpublished'`, `'active'` or `'inactive'`. See the *Rooms* section
        above for more information about each status.

        - `description (str)`  
        A description of what this chat room is intended for. It is usually a
        short description of the discussion topics.

        - `avatar_image_url (str)`  
        The URL of an image to use when the room is displayed in a mobile or web app.

        - `featured_image_url (str)`  
        The URL of an image to use when the room is featured in one a mobile or web app.

        - `featured (bool)`  
        True if this room should be featured in a mobile or web app, false otherwise

        **Return**

        The method returns an object representing the newly updated room.
        """
        return self.update(('rooms', room_id), payload=payload)

    def update_user(self, user_id, **payload):
        return self.update(('users', user_id), payload=payload)

    def update_file(self, url, file_obj, file_size, mime_type=None, encoding=None, timeout=None, emitter=None):
        """
        Updates the content of a file object hosted on Frankly servers.

        **Arguments**

        - `url (str)`  
        The URL at which the file is hosted on Frankly servers. This can be
        obtained from the `url` field of an object returned by
        `frankly.FranklyClient.create_file` for example.

        - `file_obj (object)`  
        A file-like object (as returned by `open` for example) providing the new
        content of the file.

        - `file_size (int)`  
        The size of the new file content (in bytes).

        - `mime_type (str)`  
        The mime type of the new file content.

        - `encoding (str)`  
        The encoding of the new file content (`'gzip'` for example).

        - `timeout` (int or float)  
        How long uploading the file can take at most, this parameter is optional
        and a default timeout based on bitrate limitation will be computed if
        none is given.

        - `emitter` (frankly.EventEmitter)  
        An instance of `frankly.EventEmitter` where the 'progress', 'cancel' or
        'end' events are triggered when changes are made during the file upload.
        """
        self.upload(
            url,
            content          = file_obj,
            content_length   = file_size,
            content_type     = mime_type,
            content_encoding = encoding,
            timeout          = timeout,
            emitter          = emitter,
        )

    def update_file_from_path(self, url, file_path, mime_type=None, encoding=None, timeout=None, emitter=None):
        """
        This method is a convenience wrapper for calling `frankly.FranklyClient.update_file`
        with content provided by a local file.

        **Arguments**

        - `url (str)`  
        The URL at which the file is hosted on Frankly servers. This can be
        obtained from the `url` field of an object returned by
        `frankly.FranklyClient.create_file` for example.

        - `file_path (str)`  
        A path to a local file providing the new file content.

        - `mime_type (str)`  
        The mime type of the new file content.

        - `encoding (str)`  
        The encoding of the new file content (`'gzip'` for example).

        - `timeout` (int or float)  
        How long uploading the file can take at most, this parameter is optional
        and a default timeout based on bitrate limitation will be computed if
        none is given.

        - `emitter` (frankly.EventEmitter)  
        An instance of `frankly.EventEmitter` where the 'progress', 'cancel' or
        'end' events are triggered when changes are made during the file upload.
        """
        file_size = os.path.getsize(file_path)
        guess_type, guess_encoding = mimetypes.guess_type(file_path)

        if mime_type is None:
            mime_type = guess_type

        if encoding is None:
            encoding = guess_encoding

        file_obj = open(file_path, 'rb')
        file_res = self.update_file(
            url,
            file_obj  = file_obj,
            file_size = file_size,
            mime_type = mime_type,
            encoding  = encoding,
            timeout   = timeout,
            emitter   = emitter,
        )

        if self.async:
            promise = async.Promise(None)

            def success(file_info):
                file_obj.close()
                promise.resolve(file_info)

            def failure(error):
                file_obj.close()
                promise.reject(error)

            file_res.then(success, failure)
            return promise

        return file_res

    def upload(self, url, params=None, content=None, content_length=None, content_type=None, content_encoding=None, timeout=None, emitter=None):
        """
        This method exposes a generic interface for uploading file contents to
        the Frankly API.  
        Every `upload_*` method is implemented on top of this one.

        **Arguments**

        - `url (str)`  
        The URL at which the file is hosted on Frankly servers. This can be
        obtained from the `url` field of an object returned by
        `frankly.Client.create_file` for example.

        - `params (dict)`  
        Parameters passed as part of the request.

        - `content (dict)`  
        A file-like object or a memory buffer providing the new content of the
        file.

        - `content_length (str)`  
        The size of the new file content (in bytes).

        - `content_type (str)`  
        The mime type of the new file content.

        - `content_encoding (str)`  
        The encoding of the new file content (`'gzip'` for example).

        - `timeout` (int or float)  
        How long uploading the file can take at most, this parameter is optional
        and a default timeout based on bitrate limitation will be computed if
        none is given.

        - `emitter` (frankly.EventEmitter)  
        An instance of `frankly.EventEmitter` where the 'progress', 'cancel' or
        'end' events are triggered when changes are made during the file upload.

        **Return**

        The method returns the object uploaded by the API at the specified path.
        """
        return self._upload(
            url,
            params           = params,
            content          = content,
            content_length   = content_length,
            content_type     = content_type,
            content_encoding = content_encoding,
            timeout          = timeout,
            emitter          = emitter,
        )

    def upload_file(self, file_obj, file_size, mime_type, category=None, type=None, encoding=None, timeout=None, emitter=None):
        """
        This method is convenience wrapper for creating a new file object on the
        Frankly API and setting its content.

        **Arguments**

        - `url (str)`  
        The URL at which the file is hosted on Frankly servers. This can be
        obtained from the `url` field of an object returned by
        `frankly.Client.create_file` for example.

        - `file_obj (object)`  
        A file-like object (as returned by `open` for example) providing the new
        content of the file.

        - `file_size (int)`  
        The size of the new file content (in bytes).

        - `category (str)`  
        One of the file categories supported by the API (see the *File* section
        of the documentation).

        - `type (str)`  
        One of the file types supported by the API (see the *File* section of
        the documentation).

        - `mime_type (str)`  
        The mime type of the new file content.

        - `encoding (str)`  
        The encoding of the new file content (`'gzip'` for example).

        - `timeout` (int or float)  
        How long uploading the file can take at most, this parameter is optional
        and a default timeout based on bitrate limitation will be computed if
        none is given.

        - `emitter` (frankly.EventEmitter)  
        An instance of `frankly.EventEmitter` where the 'progress', 'cancel' or
        'end' events are triggered when changes are made during the file upload.

        **Return**

        The method returns an object representing the newly uploaded file.
        """
        if category is None:
            category = 'chat'

        file_ = self.create_file(category=category, type=type)
        maybe = self.update_file(
            file_.url,
            file_obj  = file_obj,
            file_size = file_size,
            mime_type = mime_type,
            encoding  = encoding,
            timeout   = timeout,
            emitter   = emitter,
        )

        if self.async:
            promise = async.Promise(None)
            maybe.then(lambda whatever: promise.resolve(file_), promise.reject)
            return promise

        return file_

    def upload_file_from_path(self, file_path, category=None, type=None, mime_type=None, encoding=None, timeout=None, emitter=None):
        """
        This method is convenience wrapper for creating a new file object on the
        Frankly API and uploading the content from a local file.

        **Arguments**

        - `file_path (str)`  
        A path to a local file providing the new file content.

        - `category (str)`  
        One of the file categories supported by the API (see the *File* section
        of the documentation).

        - `type (str)`  
        One of the file types supported by the API (see the *File* section of
        the documentation).

        - `mime_type (str)`  
        The mime type of the new file content.

        - `encoding (str)`  
        The encoding of the new file content (`'gzip'` for example).

        - `timeout` (int or float)  
        How long uploading the file can take at most, this parameter is optional
        and a default timeout based on bitrate limitation will be computed if
        none is given.

        - `emitter` (frankly.EventEmitter)  
        An instance of `frankly.EventEmitter` where the 'progress', 'cancel' or
        'end' events are triggered when changes are made during the file upload.

        **Return**

        The method returns an object representing the newly uploaded file.
        """
        file_size = os.path.getsize(file_path)
        guess_type, guess_encoding = mimetypes.guess_type(file_path)

        if mime_type is None:
            mime_type = guess_type

        if encoding is None:
            encoding = guess_encoding

        if type is None:
            type = mime_type.split('/')[0]

        file_obj = open(file_path, 'rb')

        result = self.upload_file(
            category  = category,
            type      = type,
            file_obj  = file_obj,
            file_size = file_size,
            mime_type = mime_type,
            encoding  = encoding,
            timeout   = timeout,
            emitter   = emitter,
        )

        if self.async:
            promise = async.Promise(None)

            def success(file_info):
                file_obj.close()
                promise.resolve(file_info)

            def failure(error):
                file_obj.close()
                promise.reject(error)

            result.then(success, failure)
            return promise

        return result
