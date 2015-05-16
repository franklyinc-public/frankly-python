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
"""
The module provides types and functions for interacting with the **Frankly API**.

Goal
====

Frankly exposes a REST API to give a higer control to customers over the way
they want to use the platform.
Most operations available through the **Frankly Console** can be automated by
querying the **Frankly API** directly.

But the API needing to be secure and flexible a developer needs to master a
couple of concepts about how it works to take most advantage of it.
To make the learning curve smoother and development faster the frankly module
exposes operations available on the API through python methods of a client
object.

Things like authentication which are redundant and unproductive tasks are
nicely abstracted by the module to help developers focus on the core of what
they need to get done with the **Frankly API**.

Installation
============

The frankly module can be installed like most python modules using pip:

```
$ pip install git+https://github.com/franklyinc/frankly-python.git#egg=frankly
```

Usage
=====

The sections bellow explain how to use the module to authenticate and query
the **Frankly API**.

All operations to the API are made from instances of the `FranklyClient` class.
Those objects expose methods to the application which map to remote procedure
calls (RPC) on the **Frankly** servers, they also negotiate and maintain the
state required by the API's security policies.

Here's how `FranklyClient` instances are created:

    from frankly import FranklyClient

    client = FranklyClient()

Authentication
--------------

Before performing any operation (calling any method) the client instance needs
to authenticate against Frankly API.
The API supports different level of permissions but this module is design to
only allow *admin* authentication.

When authenticating as an *admin* user the client needs to be given the `app_key`
and `app_secret` values obtained from the [**Frankly Console**](https://console.franklychat.com/).

Here's how to perform authentication:

    from frankly import FranklyClient

    app_key    = 'app_key from Frankly Console'
    app_secret = 'app_secret from Frankly Console'

    client = FranklyClient()
    client.open(app_key, app_secret)

If the call to `open` returns then authentication was successful and the
application can move on and use this instance of `FranklyClient` to perform
other operations.

*Publishing the `app_secret` value to the public can have security implications
and could be used by an attacker to alter the content of an application.*

Rooms
-----

One of the central concepts in the **Frankly API** is the chat room.
An application can create, update and delete chat rooms. A chat room can be
seen as a collection of messages, with some associated meta-data like the title,
description or avatar image to be displayed when the end users access the mobile
or web app embedding a **Frankly SDK**.

This code snippet shows how to create chat rooms:

    from frankly import FranklyClient

    ...

    room = client.create_room(
        title       = 'Hi',
        description = 'My First Chat Room',
        status      = 'active',
    )

As we can see here, when creating a room the application must specify a *status*
property which can be one of the following:

- `unpublished` in this state the room will not be shown to clients fetching the
list of available rooms in the app, this is useful if the application needs to
create rooms that shouldn't be available yet because they still need to be modified.

- `active` in this state the room will be displayed in all clients fetching the
list of available rooms that end users can join to start chatting with each other.

- `inactive` this last state is an intermediary state between the first two, the
room will be part of fetching operations but they will not be displayed in the
mobile or web app UI, it is useful for testing purposes.

Messages
--------

Frankly being a chat platform it allows applications to send and receive messages.
Naturally `FranklyClient` instances can publish and fetch messages to chat rooms.

This code snippet shows hot to create messages:

    from frankly import FranklyClient

    ...

    message1 = client.create_message(
        room.id,
        contents = [{
          'type' : 'text/plain',
          'value': 'Hello World!',
        }],
    )

    message2 = client.create_message(
        room.id,
        contents = [{
          'type': 'image/*',
          'url' : 'https://app.franklychat.com/files/...',
        }]
    )

Let's explain quickly what's happening here: messages published to chat rooms
actually support multiple parts, they may contain few text entries, or a text
and an image, etc... So the *contents* property is actually a list of objects.
Fields of the content objects are:

- `type` which is the mime type of the actual content it represent and gives
the application informations about how to render the content. This is mandatory.

- `value` which is used for inline resources directly embedded into the message.

- `url` which is used for remote resources that the application can upload and
download in parallel of sending or receiving messages. On of *value* or *url*
must be specified.

Typically, text messages are inlined because they are small enough resources
that they can be embedded into the message without impact user experience.
Images on the other end may take a while to download and rendering can be
optimized using caching mechanisms to avoid downloading large resources too
often, that's why they should provided as a remote resource (we'll see later
in the *Files* section how to generate remote resource URLs).

*Keep in mind that messages will be broadcasted to every client application
currently listening for messages on the same chat room when they are created.*

Announcements
-------------

Announcements are a different type of messages which are only available to
admin users.  
A client authenticated with admin priviledges can create announcements in the
app, which can then be published to one or more rooms at a later time.

In mobile and web apps embedding a **Frankly SDK**, announcements are rendered
differently from regular messages, they are highlighted and can be forced to
stick at the top of the chat room UI to give some context to end users about
what is currently ongoing.

Here's how an app using the frankly module would create and then publish
announcements:

    from frankly import FranklyClient

    ...

    anno = client.create_announcement(
        contents = [{
          'type' : 'text/plain',
          'value': 'Welcome!',
        }],
    )

    client.publish_announcement(
        anno.id,
        room.id,
    )

As we can see here, the announcement is created with the same structure than
a regular message.  
The content of the announcement is actually what is going to be set as the
message content when published to a room and obeys the same rules that were
described in the *Messages* section regarding inline and remote content.

Files
-----

Objects of the **Frankly API** can have URL properties set to reference
remote resources like images. All these URLs must be within the
```https://app.franklychat.com``` domain, which means an application must
upload these resources to Frankly servers.  

Uploading a file happens in two steps, first the application needs to
request a new file URL to the **Frankly API**, then it can use that URL to
upload a resource to Frankly servers.  
Lukily the frankly module abstracts this nicely in a single operation, here's
an example of how to set an image for a chat room:

    from frankly import FranklyClient

    ...

    file = client.upload_file_from_path(
        './path/to/image.png',
        category = 'roomavatar',
    )

    room = client.update_room(
        room.id,
        avatar_image_url = file.url,
    )

The object returned by a call to `upload_file_from_path` and other upload
methods is created in the first step described above.  
The `category` parameter shown here is a hint given the the **Frankly API**
to know what formatting rules should be applied to the resource. This is
useful to provide a better integration with Frankly and better user experience
as files will be optimized for different situations based on their category.

Here are the file categories currently available:

- `chat`  
The default category which is usually applied to images sent by end users.

- `useravatar`  
This category optimizes files intended to be displayed as part of a user
profile.

- `roomavatar`  
This category optimizes files intended to be displayed on room lists.

- `featuredavatar`  
Used for files intended to be displayed to represent featued rooms.

- `sticker`  
This category optimizes files that are used for sticker messages.

- `stickerpack`  
for being used as an avatar of a sticker pack.

Errors
------

When the application is misusing the **Frankly API** or when things go wrong
at a different level (network going down, ...), calls to methods of a
`FranklyClient` instance may not return and instead would raise an exception.

All exceptions raised by calls to the methods will be instances of `FranklyError`.

The errors give some context about what went wrong, here's a quick example
showing how to handle those situations:

    from frankly import FranklyClient
    from frankly import FranklyError

    ...

    try:
        client = FranklyClient()
        client.open(app_key, app_secret)

        ...

    except FranklyError as e:
        print(e)

"""
from __future__ import division
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

from copy import deepcopy
from datetime import datetime
from dateutil.parser import parse as parse_date
from functools import wraps
from json import JSONDecoder as BaseJsonDecoder
from json import JSONEncoder as BaseJsonEncoder
from requests.exceptions import RequestException
from requests.exceptions import ConnectionError
from requests.exceptions import HTTPError
from requests.exceptions import URLRequired
from requests.exceptions import TooManyRedirects
from requests.exceptions import ConnectTimeout
from requests.exceptions import ReadTimeout
from requests.exceptions import Timeout
from six.moves.urllib.parse import urlparse

import json
import jwt
import mimetypes
import os
import requests
import six
import time

__all__ = [
    'generate_identity_token',
    'FranklyClient',
    'FranklyError',
    'FranklyObject',
]

def generate_identity_token(app_key, app_secret, nonce, user_id=None, role=None):
    """
    This function generates an identity token suitable for a signle
    authentication attempt of a client against the Frankly API or SDK.

    **Arguments**

    - `app_key (str)`  
    The key that specifies which app this client is authenticating for, this
    value is provided by the Frankly Console.

    - `app_secret (str)`  
    The secret value associated the the key allowing the client to securely
    authenticate against the Frankly API.

    - `nonce (str)`  
    The nonce value got from Frankly SDK or API whether the identity generation
    comes from an client device or app backend.

    - `user_id (str)`  
    This argument must be set to make the SDK operate on behalf of a specific
    user of the app.  
    For backend services willing to interact with the API directly this may be
    omitted.

    - `role (str)`  
    For backend services using the Frankly API this can be set to `'admin'` to
    generate a token allowing the client to get admin priviledges and perform
    operations that regular users are forbidden to.

    **Return**

    The function returns the generated identity token as a string.
    """
    now = int(time.time())
    tok = {
        'aak': app_key,
        'iat': now,
        'exp': now + 864000,
        'nce': nonce,
    }

    if user_id is not None:
        tok['uid'] = user_id

    if role is not None:
        tok['role'] = role

    idt = jwt.encode(tok, app_secret, algorithm='HS256', headers={
        'typ': 'JWS',
        'cty': 'frankly-it;v1',
    })

    return six.text_type(idt, encoding='utf-8')

class FranklyClient(object):
    """
    This class provides the implementation of a network client that exposes
    operations available on the Frankly API to a python application.

    A typical work flow is to create an instance of FranklyClient, using it
    to authenticate and then make method calls to interact with the API.  
    Reusing the same client instance multiple times allow the application to
    avoid wasting time re-authenticating before every operation.

    An application can create multiple instances of this class and authenticate
    with the same or different pairs of `app_key` and `app_secret`, each instance
    is independant from the other ones.

    Each instance of FranklyClient maintains its own connection pool to Frankly
    servers, if client is not required anymore the application should call the
    `close` method to release system resources.  
    A client should not be used anymore after being closed.  
    Note that instances of FranklyClient can be used as context managers to
    automatically be closed when exiting the `with` statement.

    **[thread safety]**  
    Python application using threads or libraries like [gevent](http://www.gevent.org/)
    can share instances of FranklyClient between multiple threads/coroutines
    only after sucessfuly authenticating.
    """

    def __init__(self, address='https://app.franklychat.com', connect_timeout=5, request_timeout=5):
        """
        Creates a new instance of this class.

        **Arguments**

        - `address (str)`  
        The URL at which Frankly servers can be reached, it's very unlikely that
        an application would need to change this value.

        - `connect_timeout (int or float)`  
        The maximum amount of time connecting to the API can take (in seconds).

        - `request_timeout (int or float)`  
        The maximum amount of time submitting a request and receiving a response
        from the API can take (in seconds).
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

        url = urlparse(address)

        if url.scheme in ('http', 'https'):
            self.backend = HttpBackend(
                address,
                connect_timeout = connect_timeout,
                request_timeout = request_timeout,
            )
        else:
            raise ValueError(address + " is not accessible through a supported protocol")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def open(self, app_key, app_secret):
        """
        This should be the first method called on an instance of FranklyClient,
        after succesfully returning the client can be used to interact with the
        Frankly API.

        **Arguments**

        - `app_key (str)`  
        The key that specifies which app this client is authenticating for, this
        value is provided by the Frankly Console.

        - `app_secret (str)`  
        The secret value associated the the key allowing the client to securely
        authenticate against the Frankly API.

        **Return**

        On success the method returns a session object which contains two fields,
        `app_id` with the identifier of the application this client has
        authenticated for, and `app_user_id` with the identifier of the actual
        user this client will run as.
        """
        return self.backend.open(app_key, app_secret)

    def close(self):
        """
        Shuts down all connections and releases system resources held by this
        client object.  
        The instance should not be used anymore after calling this method.
        """
        self.backend.close()

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
        return self.backend.create(path, params, payload)

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
        for more details about content objects.

        - `contextual (bool)`  
        Whether the announcement should be published as a contextual or regular
        messages.

        **Return**

        The method returns an object representing the newly created announcement.
        """
        return self.create('/announcements', payload=payload)

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
        return self.create('/files', params=payload)

    def create_room(self, **payload):
        """
        Creates a new room object in the app and return that object.  
        The properties of that new room are given as keyword arguments to the
        method.

        **Arguments**

        - `title (str)`  
        The title associated to this room.

        - `status (str)`  
        One of `'unpublished'`, `'active'` or `'inactive'`.

        - `description (str)`  
        A description of what this chat room is intended for, it is usually a
        short description of topics that are discussed by participants.

        - `avatar_image_url (str)`  
        The URL of an image to use when the room is displayed in one of the
        mobile or web apps embedding a Frankly SDK.

        - `featured_image_url (str)`  
        The URL of an image to use when the room is featured in one of the
        mobile or web apps embedding a Frankly SDK.

        - `featured (bool)`  
        Whether the room should be featured in the mobile or web apps embedding
        a Frankly SDK.

        **Return**

        The method returns an object representing the newly created room.
        """
        return self.create('/rooms', payload=payload)

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
        return self.create('/rooms/{}/messages'.format(room_id), payload=payload)

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
        return self.backend.delete(path, params, payload)

    def delete_announcement(self, announcement_id):
        """
        Deletes an announcement object with id sepecified as first argument
        from the app.

        Note that deleting an announcement doesn't remove messages from rooms
        it has already been published to.

        This operation cannot be undone!

        **Arguments**

        - `announcement_id (int)`  
        The identifier of the announcement to fetch.

        **Return**

        The method returns an object representing the announcement wit the
        specified id in the app.
        """
        return self.delete('/announcements/{}'.format(announcement_id))

    def delete_room(self, room_id):
        """
        Deletes a room object with id specified as first argument from the app.

        Note that this will cause all messages sent to this room to be deleted
        as well, a safer approach could be to change the room status to
        `'unpublished'` to hide it without erasing data.

        This operation cannot be undone!

        **Arguments**

        - `room_id (int)`  
        The identifier of the room to fetch.

        **Return**

        The method returns an object representing the room with the specified id
        in the app.
        """
        return self.delete('/rooms/{}'.format(room_id))

    def publish_announcement(self, announcement_id, to_room_id):
        """
        Calling this method causes the announcement with id specified as first
        argument to the room with id specified as second argument.  
        A message will be created and sent in real-time to all mobile or web
        clients currently listening for incoming messages on that room.

        **Arguments**

        - `announcement_id (int)`  
        The identifier of the announcement to publish.

        - `room_id (int)`  
        The identifier of the room to publish the announcement to.
        """
        self.update('/announcements/{}/rooms/{}'.format(announcement_id, to_room_id))

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
        return self.backend.read(path, params, payload)

    def read_announcement(self, announcement_id):
        """
        Retrieves an announcement object with id sepecified as first argument
        from the app.

        **Arguments**

        - `announcement_id (int)`  
        The identifier of the announcement to fetch.

        **Return**

        The method returns an object representing the announcement wit the
        specified id in the app.
        """
        return self.read('/announcements/{}'.format(announcement_id))

    def read_announcement_list(self):
        """
        Retrieves a list of announcements available in the app.

        **Return**

        The method returns a list of annoucement objects ordered by id, which
        may be empty if there are no announcements in the app.
        """
        return self.read('/announcements')

    def read_announcement_room_list(self, announcement_id):
        """
        Retrieves the list of rooms that an annoucement has been published to.

        **Arguments**

        - `announcement_id (int)`  
        The identifier of the announcement to get the list of rooms for.

        **Return**

        The method returns a list of annoucement objects ordered by id, which
        may be empty if there are no announcements in the app or none have been
        published yet.
        """
        return self.read('/announcements/{}/rooms'.format(announcement_id))

    def read_room(self, room_id):
        """
        Retrieves a room object with id specified as first argument from the app.

        **Arguments**

        - `room_id (int)`  
        The identifier of the room to fetch.

        **Return**

        The method returns an object representing the room with the specified id
        in the app.
        """
        return self.read('/rooms/{}'.format(room_id))

    def read_room_list(self):
        """
        Retrieves the list of all available rooms from the app.

        **Return**

        The method returns a list of room objects ordered by id, which may be
        empty if there are no rooms in the app.
        """
        return self.read('/rooms')

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

        - `contextual (bool)`  
        When set to true only contextual messages will be returned in the result
        list.  
        When set to false only non-contextual messages will be returned in the
        result list.
        This argument may be omitted or set to `None`, in that case any kind of
        messages will be returned in the result list.

        **Return**

        The method returns a list of message objects, which may be empty if no
        messages were satisfying the query.
        """
        return self.read('/rooms/{}/messages'.format(room_id), params=params)

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
        return self.backend.update(path, params, payload)

    def update_room(self, room_id, **payload):
        """
        Updates an existing room object in the app and return that object.  
        The properties of that new room are given as keyword arguments to the
        method.

        **Arguments**

        - `room_id (int)`  
        The identifier of the room to fetch.

        - `title (str)`  
        The title associated to this room.

        - `status (str)`  
        One of `'unpublished'`, `'active'` or `'inactive'`.

        - `description (str)`  
        A description of what this chat room is intended for, it is usually a
        short description of topics that are discussed by participants.

        - `avatar_image_url (str)`  
        The URL of an image to use when the room is displayed in one of the
        mobile or web apps embedding a Frankly SDK.

        - `featured_image_url (str)`  
        The URL of an image to use when the room is featured in one of the
        mobile or web apps embedding a Frankly SDK.

        - `featured (bool)`  
        Whether the room should be featured in the mobile or web apps embedding
        a Frankly SDK.

        **Return**

        The method returns an object representing the newly created room.
        """
        return self.update('/rooms/{}'.format(room_id), payload=payload)

    def update_file(self, url, file_obj, file_size, mime_type, encoding=None):
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
        """
        self.upload(
            url,
            payload          = file_obj,
            content_length   = file_size,
            content_type     = mime_type,
            content_encoding = encoding
        )

    def update_file_from_path(self, url, file_path):
        """
        This method is a convenience wrapper for calling `frankly.FranklyClient.update_file`
        with a content provided by a local file.

        **Arguments**

        - `url (str)`  
        The URL at which the file is hosted on Frankly servers. This can be
        obtained from the `url` field of an object returned by
        `frankly.FranklyClient.create_file` for example.

        - `file_path (str)`  
        A path to a local file providing the new file content.
        """
        file_size = os.path.getsize(file_path)
        mime_type, encoding = mimetypes.guess_type(file_path)

        with open(file_path, 'rb') as file_obj:
            self.update_file(url, file_obj, file_size, mime_type, encoding)

    def upload(self, url, params=None, payload=None, content_length=None, content_type=None, content_encoding=None):
        """
        This method exposes a generic interface for uploading file contents to
        the Frankly API.  
        Every `upload_*` method is implemented on top of this one.

        **Arguments**

        - `url (str)`  
        The URL at which the file is hosted on Frankly servers. This can be
        obtained from the `url` field of an object returned by
        `frankly.FranklyClient.create_file` for example.

        - `params (dict)`  
        Parameters passed as part of the request.

        - `payload (dict)`  
        A file-like object or a memory buffer providing the new content of the
        file.

        - `content_length (str)`  
        The size of the new file content (in bytes).

        - `content_type (str)`  
        The mime type of the new file content.

        - `content_encoding (str)`  
        The encoding of the new file content (`'gzip'` for example).

        **Return**

        The method returns the object updated on the API at the specified path.
        """
        self.backend.upload(url, params, payload, content_length, content_type, content_encoding)

    def upload_file(self, file_obj, file_size, mime_type, encoding=None, **params):
        """
        This method is convenience wrapper for creating a new file object on the
        Frankly API and setting its content.

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

        - `category (str)`  
        One of the file categories supported by the API (see the *File* section
        of the documentation).

        - `type (str)`  
        One of the file types supported by the API (see the *File* section of
        the documentation).

        **Return**

        The method returns an object representing the newly created file.
        """
        if params.get('category') is None:
            params['category'] = 'chat'
        f = self.create_file(**params)
        self.update_file(f.url, file_obj, file_size, mime_type, encoding)
        return f

    def upload_file_from_path(self, file_path, **params):
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

        **Return**

        The method returns an object representing the newly created file.
        """
        file_size = os.path.getsize(file_path)
        mime_type, encoding = mimetypes.guess_type(file_path)

        if params.get('type') is None:
            params['type'] = mime_type.split('/')[0]

        with open(file_path, 'rb') as file_obj:
            return self.upload_file(file_obj, file_size, mime_type, encoding, **params)

class FranklyError(Exception):
    """
    Instances of this class are used to represent errors that may be raised from
    any call to methods of the `frankly.FranklyClient` class.
    """

    def __init__(self, operation, path, status, message):
        """
        Creates a new instance of this class.
        """
        self._operation = operation
        self._path      = path
        self._status    = status
        self._message   = message

    def __str__(self):
        return '%s %s [%s]: %s' % (self._operation, self._path, self._status, self._message)

    def __repr__(self):
        return 'FranklyError { %s }' % self.__str__()

    @property
    def operation(self):
        """
        The kind operation that generated this error, it may be one of `'create'`,
        `'read'`, `'update'`, `'upload'` or `'delete'`.
        """
        return self._operation

    @property
    def path(self):
        """
        The path of the operation that generated this error as a list of elements
        representing the resource the operation was executed on.
        """
        return self._path

    @property
    def status(self):
        """
        The status code of the error, which may be any of the
        [http status codes](http://en.wikipedia.org/wiki/List_of_HTTP_status_codes).
        """
        return self._status

    @property
    def message(self):
        """
        A human-readable description of why the error happened.
        """
        return self._message

class FranklyObject(dict):
    """
    This class provides the implementation of a dict-like type where properties
    are also available through an object notation.

    Instances of this type also expose an iterator iterface which produces tuples
    of key/value pairs.

    Every method calls on `frankly.FranklyClient` objects return instances of this
    class or a list of instances of this class.
    """

    def __iter__(self):
        return six.iteritems(self)

    def __delattr__(self, name):
        try:
            del self[name]
        except KeyError:
            raise AttributeError(name)

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)

    def __setattr__(self, name, value):
        self[name] = value

    def __str__(self):
        return json.dumps(self, cls=JsonEncoder)

    def __repr__(self):
        return json.dumps(self, cls=JsonEncoder, indent=2)

# Backend
# =======
#
# The Frankly API is available through multiple protocols, each of them
# is implemented as a different backend to the FranklyClient object.

class BaseBackend(object):

    def open(self, app_key, app_secret):
        raise NotImplementedError

    def close(self):
        raise NotImplementedError

    def create(self, path, params=None, payload=None):
        raise NotImplementedError

    def read(self, path, params=None, payload=None):
        raise NotImplementedError

    def update(self, path, params=None, payload=None):
        raise NotImplementedError

    def upload(self, url, params=None, payload=None, content_length=None, content_type=None, content_encoding=None):
        raise NotImplementedError

    def delete(self, path, params=None, payload=None):
        raise NotImplementedError

def request_wrapper(operation, path, f, *args, **kwargs):
    def _raise(code, message):
        raise FranklyError(operation, path, code, message)

    try:
        return f(*args, **kwargs)

    except RequestException as e:
        _raise(500, six.text_type(e))

    except ConnectionError as e:
        _raise(500, six.text_type(e))

    except HTTPError as e:
        _raise(400, six.text_type(e))

    except URLRequired as e:
        _raise(400, six.text_type(e))

    except TooManyRedirects as e:
        _raise(500, "frankly servers submitted too many redirections")

    except ConnectTimeout as e:
        _raise(408, "failed to connect the frankly servers in the allotted amount of time")

    except ReadTimeout as e:
        _raise(408, "failed to receive a response in the allotted amount of time")

    except Timeout as e:
        _raise(408, "failed to submit the request in the allotted amount of time")

    except Exception as e:
        _raise(500, six.text_type(e))

def api(f):
    @wraps(f)
    def _(self, path, *args, **kwargs):
        operation = f.__name__
        response  = request_wrapper(operation, path, f, self, path, *args, **kwargs)

        if operation in ('create', 'read', 'update'):
            try:
                content = response.json(cls=JsonDecoder)
            except ValueError as e:
                raise FranklyError(operation, path, 500, "the server didn't respond with a JSON payload")
        else:
            content = None

        if response.status_code >= 300:
            raise FranklyError(operation, path, response.status_code, content)

        return content
    return _

class HttpBackend(BaseBackend):

    def __init__(self, address, connect_timeout=None, request_timeout=None):
        self.address = address
        self.session = None
        self.connect_timeout = connect_timeout
        self.request_timeout = request_timeout
        self.http    = requests.Session()
        self.http.headers.update({
            'Accept'       : 'application/json',
            'Content-Type' : 'application/json',
            'User-Agent'   : 'Frankly-SDK/1.0.0 (Python)',
        })

    def open(self, app_key, app_secret):
        nce = self.read('/auth/nonce')
        idt = generate_identity_token(app_key, app_secret, nce, role='admin')

        session = self.read('/auth', params={
            'identity_token': idt,
        })

        self.session = session
        return FranklyObject(
            app_id      = session.get('app_id'),
            app_user_id = session.get('app_user_id'),
            platform    = session.get('platform', 'python'),
            version     = session.get('version', 1),
            role        = session.get('role'),
            created_on  = session.get('created_on'),
            updated_on  = session.get('updated_on'),
            expires_on  = session.get('expires_on'),
        )

    def close(self):
        self.http.close()

    @api
    def create(self, path, params=None, payload=None):
        return self.http.post(
            url     = self.make_url(path),
            params  = self.make_params(params),
            data    = json.dumps(payload, cls=JsonEncoder, separators=None),
            timeout = (self.connect_timeout, self.request_timeout),
        )

    @api
    def read(self, path, params=None, payload=None):
        return self.http.get(
            url     = self.make_url(path),
            params  = self.make_params(params),
            timeout = (self.connect_timeout, self.request_timeout),
        )

    @api
    def update(self, path, params=None, payload=None):
        return self.http.put(
            url     = self.make_url(path),
            params  = self.make_params(params),
            data    = json.dumps(payload, cls=JsonEncoder, separators=None),
            timeout = (self.connect_timeout, self.request_timeout),
        )

    def upload(self, url, params=None, payload=None, content_length=None, content_type=None, content_encoding=None):
        headers = deepcopy(self.http.headers)

        if content_length is not None:
            headers['Content-Length'] = six.text_type(content_length)

        if content_type is not None:
            headers['Content-Type'] = six.text_type(content_type)

        if content_encoding is not None:
            headers['Content-Encoding'] = six.text_type(content_encoding)

        operation = 'upload'
        path      = urlparse(url).path
        response  = request_wrapper(
            operation,
            path,
            self.http.put,
            url,
            params  = self.make_params(params),
            data    = payload,
            headers = headers,
            timeout = (self.connect_timeout, self.request_timeout if content_length is None else max(self.request_timeout, content_length / 1000)),
        )

        if response.status_code != 200:
            raise FranklyError(operation, path, response.status_code, response.text)

    @api
    def delete(self, path, params=None, payload=None):
        return self.http.delete(
            url     = self.make_url(path),
            params  = self.make_params(params),
            timeout = (self.connect_timeout, self.request_timeout),
        )

    def make_url(self, path):
        return '%s%s' % (self.address, path)

    def make_params(self, params):
        new_params = { }
        if params is not None:
            for k, v in six.iteritems(params):
                if v is None:
                    continue
                if isinstance(v, bool):
                    v = 'true' if v else 'false'
                elif not isinstance(v, six.text_type):
                    v = six.text_type(v)
                new_params[k] = v
        if self.session is not None:
            new_params['token'] = self.session.token
        return new_params

# Utilities
# =========
#
# Types and functions defined bellow this point are used as utilities to
# implement higher-level features of the frankly module.

class JsonDecoder(BaseJsonDecoder):

    def __init__(self, **kwargs):
        kwargs['strict'] = False
        kwargs['object_pairs_hook'] = FranklyObject
        BaseJsonDecoder.__init__(self, **kwargs)

    def decode(self, s):
        obj = BaseJsonDecoder.decode(self, s)
        obj = json_parse_dates(obj)
        return obj

class JsonEncoder(BaseJsonEncoder):

    def __init__(self, **kwargs):
        if kwargs.get('separators') is None:
            kwargs['separators'] = (',', ':')
        BaseJsonEncoder.__init__(self, **kwargs)

    def default(self, obj):
        if isinstance(obj, datetime):
            return format_date(obj)

        if isinstance(obj, set):
            return list(obj)

        return BaseJsonEncoder.default(self, obj)

def json_parse_dates(obj):
    if isinstance(obj, six.text_type):
        try:
            return parse_date(obj)
        except:
            return obj

    if isinstance(obj, list):
        return [json_parse_dates(x) for x in obj]

    if isinstance(obj, dict):
        return type(obj)((k, json_parse_dates(v)) for k, v in six.iteritems(obj))

    return obj

def format_date(d):
    tz = d.strftime('%z')
    if tz in ('', '+0000'):
        tz = 'Z'
    return '%04d-%02d-%02dT%02d:%02d:%02d.%03d%s' % (
        d.year,
        d.month,
        d.day,
        d.hour,
        d.minute,
        d.second,
        d.microsecond / 1000,
        tz,
    )
