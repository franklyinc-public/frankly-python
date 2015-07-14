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

from frankly.version import __version__
from six.moves import urllib
urlparse = urllib.parse.urlparse

USER_AGENT = 'Frankly-SDK/%s (Python)' % __version__

import jwt
import requests
import six
import time

from . import util
from . import errors
from . import logger as log

__all__ = [
    'USER_AGENT',
    'Session',
    'authenticate',
    'generate_identity_token',
    'identity_token_generator',
]

def generate_identity_token(app_key, app_secret, nonce, uid=None, role=None):
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

    - `uid (str)`  
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

    if uid is not None:
        tok['uid'] = uid

    if role is not None:
        tok['role'] = role

    idt = jwt.encode(tok, app_secret, algorithm='HS256', headers={
        'typ': 'JWS',
        'cty': 'frankly-it;v1',
    })

    return six.text_type(idt, encoding='utf-8')

def identity_token_generator(app_key, app_secret, uid=None, role=None):
    """
    Given app and user credentials this function creates a callable object
    that accepts nonce values as arguments and generates valid identity tokens
    to authenticate a user.


    - `app_key (str)`  
    The key that specifies which app this client is authenticating for, this
    value is provided by the Frankly Console.

    - `app_secret (str)`  
    The secret value associated the the key allowing the client to securely
    authenticate against the Frankly API.

    - `uid (str)`  
    This argument must be set to make the SDK operate on behalf of a specific
    user of the app.  
    For backend services willing to interact with the API directly this may be
    omitted.

    - `role (str)`  
    For backend services using the Frankly API this can be set to `'admin'` to
    generate a token allowing the client to get admin priviledges and perform
    operations that regular users are forbidden to.

    **Return**

    The function returns an identity token generator.
    """
    return lambda nonce: generate_identity_token(app_key, app_secret, nonce, uid, role)

class Session(object):

    def __init__(self, key=None, secret=None, user=None, role=None, headers=None, cookies=None, info=None):
        self.key     = key
        self.secret  = secret
        self.user    = user
        self.role    = role
        self.headers = headers
        self.cookies = cookies
        self.info    = info

    def __str__(self):
        if self.key is None:
            return 'session { app = %s, user = %s, cookies = %s }' % (
                self.info.app.id,
                self.info.user.id,
                self.cookies,
            )
        else:
            return 'session { key = %s, user = %s, role = %s }' % (
                self.key,
                self.user,
                self.role,
            )

    def __repr__(self):
        if self.key is None:
            return 'frankly.auth.Session { app = %s, user = %s, cookies = %s }' % (
                self.info.app.id,
                self.info.user.id,
                self.cookies,
            )
        else:
            return 'frankly.auth.Session { key = %s, user = %s, role = %s }' % (
                self.key,
                self.user,
                self.role,
            )

def authenticate(address, generate_identity_token, timeout=None, http=None):
    if http is None:
        http = requests

    # Guess what the address should be if it's set to a websocket endpoint
    # or contains some extra stuff (path, query, ...)
    url = urlparse(address)

    if url.scheme == 'wss':
        scheme = 'https'
    elif url.scheme == 'ws':
        scheme = 'http'
    else:
        scheme = url.scheme

    address = scheme + '://' + url.netloc
    headers = {
        'Accept'     : 'application/json',
        'User-Agent' : USER_AGENT,
    }

    # Get a nonce value from the Frankly API.
    try:
        response = http.get(
            url     = address + '/auth/nonce',
            headers = headers,
            timeout = timeout,
        )
    except errors.Error:
        raise
    except Exception as e:
        raise errors.Error('auth', '/auth/nonce', 500, str(e))

    if response.status_code != 200:
        raise errors.Error('auth', '/auth/nonce', response.status_code, response.json(cls=util.JsonDecoder))

    # Generate the identity token now that we have a nonce value.
    try:
        nonce = response.json(cls=util.JsonDecoder)
        token = generate_identity_token(nonce)
    except errors.Error:
        raise
    except Exception as e:
        raise errors.Error('auth', '/auth', 500, str(e))

    # Authenticate, this will return session cookies that we set into the
    # session.cookies jar.
    try:
        headers['Frankly-App-Identity-Token'] = token
        response = http.get(
            url     = address + '/auth',
            headers = headers,
            timeout = timeout,
        )
    except errors.Error:
        raise
    except Exception as e:
        raise errors.Error('auth', '/auth', 500, str(e))

    if response.status_code != 200:
        raise errors.Error('auth', '/auth', response.status_code, response.json(cls=util.JsonDecoder))

    return Session(
        headers = response.headers,
        cookies = response.cookies,
        info    = response.json(cls=util.JsonDecoder),
    )
