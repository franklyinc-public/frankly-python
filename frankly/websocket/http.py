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

from http_parser.http import HttpStream
from http_parser.http import NoMoreData
from http_parser.http import HTTP_REQUEST
from http_parser.http import HTTP_RESPONSE
from http_parser.parser import HttpParser
from http_parser.reader import SocketReader
from http_parser.util import IOrderedDict as HttpFields
from http_parser.util import status_reasons as reasons

import six
from six.moves.urllib.parse import urlencode
from six.moves.urllib.parse import urlparse
from six.moves.urllib.parse import urlunparse
from six.moves.urllib.parse import parse_qs

from wsgiref.util import guess_scheme

from . import net

__all__ = [
    'HTTP_10',
    'HTTP_11',
    'HttpSocket',
    'HttpConnection',
    'HttpClient',
    'HttpFields',
    'HttpServer',
    'bind',
    'connect',
    'reasons',
]

HTTP_10 = 'HTTP/1.0'
HTTP_11 = 'HTTP/1.1'

def parse_query_value(value):
    if isinstance(value, list):
        if len(value) == 0: return None
        if len(value) == 1: return parse_query_value(value[0])
        return [parse_query_value(x) for x in value]
    if value == '':      return None
    if value == 'true':  return True
    if value == 'false': return False
    return value

def format_query_value(value):
    if value is None:  return ''
    if value is True:  return 'true'
    if value is False: return 'false'
    if isinstance(value, list):  return [format_query_value(x) for x in value]
    if isinstance(value, tuple): return [format_query_value(x) for x in value]
    return value

class HttpSocket(object):

    def __init__(self, socket):
        self.socket = socket

    def __enter__(self):
        return self

    def __exit__(self, *args):
        try:
            self.close()
        except Exception as e:
            pass

    def close(self):
        if self.socket is not None:
            try:
                self.socket.close()
            finally:
                self.socket = None

    def detach(self):
        socket, self.socket = self.socket, None
        return socket

    def fileno(self):
        return -1 if self.socket is None else self.socket.fileno()

    @property
    def timeout(self):
        return self.socket.gettimeout()

    @timeout.setter
    def timeout(self, value):
        self.socket.settimeout(value)

class HttpConnection(HttpSocket):

    def __init__(self, socket=None, host=None):
        HttpSocket.__init__(self, socket)
        self.version = HTTP_11
        self.host    = host
        self.reader  = None if socket is None else SocketReader(self.socket)

    def connect(self, host, port='http', timeout=None, secure=None, **kwargs):
        assert self.socket is None, "http connection already established"

        if secure is None and port == 'https':
            secure = True

        self.socket = net.connect(host, port, timeout=timeout, secure=secure, **kwargs)
        self.reader = SocketReader(self.socket)
        self.host   = host

        if port not in ('http', 'https'):
            self.host += ':%s' % port

    def close(self):
        try:
            if self.reader is not None:
                self.reader.close()
        except Exception:
            pass
        finally:
            self.reader = None
            self.host   = None
        HttpSocket.close(self)

    def shutdown(self):
        self.socket.shutdown()

    def recv(self):
        try:
            stream  = HttpStream(self.reader, kind=HTTP_RESPONSE, parser_class=HttpParser, decompress=True)
            status  = stream.status_code()
            version = stream.version()
            fields  = stream.headers()
            content = stream.body_file()
            self.version = 'HTTP/%s.%s' % version
            return status, fields, content
        except NoMoreData:
            pass

    def send(self, method, path, query=None, fragment=None, fields=None, content=None, version=None):
        if fields is None:
            fields = HttpFields()

        elif not isinstance(fields, HttpFields):
            fields = HttpFields(fields)

        if query is None:
            query = { }

        if content is None:
            content = b''

        if version is None:
            version = self.version

        assert version in (HTTP_10, HTTP_11), "invalid http version: %s" % version
        fields.setdefault('Content-Length', six.text_type(len(content)))
        fields.setdefault('Host', self.host)

        for k, v in six.iteritems(dict(query)):
            query[k] = format_query_value(v)
        if six.PY3:
            query = urlencode(query, encoding='utf-8')
        else:
            query = urlencode(query)

        header  = ''
        header += method
        header += ' '
        header += urlunparse(('', '', path, '', query, fragment if bool(fragment) else ''))
        header += ' %s\r\n' % version
        header += ''.join('%s: %s\r\n' % (k, v) for k, v in six.iteritems(fields))
        header += '\r\n'
        header  = header.encode('utf-8')

        self.socket.sendall(header + content)

    def request(self, *args, **kwargs):
        self.send(*args, **kwargs)
        return self.recv()

    def delete(self, *args, **kwargs):
        return self.request('DELETE', *args, **kwargs)

    def get(self, *args, **kwargs):
        return self.request('GET', *args, **kwargs)

    def head(self, *args, **kwargs):
        return self.request('HEAD', *args, **kwargs)

    def options(self, *args, **kwargs):
        return self.request('OPTIONS', *args, **kwargs)

    def post(self, *args, **kwargs):
        return self.request('POST', *args, **kwargs)

    def put(self, *args, **kwargs):
        return self.request('PUT', *args, **kwargs)

class HttpClient(HttpSocket):

    def __init__(self, socket, address, server):
        HttpSocket.__init__(self, socket)
        self.address = address
        self.reader  = SocketReader(self.socket)
        self.server  = server
        self.version = HTTP_11

    def __iter__(self):
        while True:
            request = self.recv()
            if request is None:
                break
            yield request

    def iter_wsgi(self):
        while True:
            environ = self.recv(True)
            if environ is None:
                break
            yield environ

    def close(self):
        try:
            if self.reader is not None:
                self.reader.close()
        except Exception:
            pass
        finally:
            self.reader = None
        HttpSocket.close(self)

    def recv(self, wsgi=False):
        try:
            stream = HttpStream(self.reader, kind=HTTP_REQUEST, parser_class=HttpParser, decompress=True)

            if bool(wsgi):
                environ = stream.wsgi_environ()
                environ['wsgi.url_scheme'] = guess_scheme(environ)
                environ['wsgi.input'] = stream.body_file()
                environ['wsgi.socket'] = self.socket
                return environ

            # BUG:
            # http-parser has an issue here, if we call 'method' before 'headers'
            # and invalid method name is returned...
            fields  = stream.headers()
            method  = stream.method()
            url     = stream.url()
            version = stream.version()
            content = stream.body_file()

            url      = urlparse(url)
            path     = url.path
            query    = parse_qs(url.query, keep_blank_values=True)
            fragment = url.fragment

            for k, v in six.iteritems(dict(query)):
                query[k] = parse_query_value(v)

            self.version = 'HTTP/%s.%s' % version
            return method, path, query, fragment, fields, content
        except NoMoreData:
            pass

    def send(self, status, fields=None, content=None, version=None):
        if fields is None:
            fields = { }

        elif not isinstance(fields, HttpFields):
            fields = HttpFields(fields)

        if content is None:
            content = b''

        if version is None:
            version = self.version

        assert version in (HTTP_10, HTTP_11), "invalid http version: %s" % version
        fields.setdefault('Content-Length', six.text_type(len(content)))

        if self.server is not None:
            fields.setdefault('Server', self.server)

        if isinstance(status, int):
            status = '%s %s' % (status, reasons[status])

        header  = ''
        header += '%s %s\r\n' % (version, status)
        header += ''.join('%s: %s\r\n' % (k, v) for k, v in six.iteritems(fields))
        header += '\r\n'
        header  = header.encode('utf-8')

        return self.socket.sendall(header + content)

class HttpServer(HttpSocket):

    def __init__(self, socket=None, server='maestro-http'):
        HttpSocket.__init__(self, socket)
        self.server = server

    def __iter__(self):
        while True:
            yield self.accept()

    def accept(self):
        assert self.socket is not None, "http server not bound to any network interface"
        socket, address = self.socket.accept()
        socket.settimeout(self.socket.gettimeout())
        return HttpClient(socket, address, self.server)

    def bind(self, *args, **kwargs):
        assert self.socket is None, "http server already bound to network interface"
        self.socket = net.bind(*args, **kwargs)

def bind(*args, **kwargs):
    server = HttpServer()
    try:
        server.bind(*args, **kwargs)
    except:
        server.close()
        raise
    return server

def connect(*args, **kwargs):
    conn = HttpConnection()
    try:
        conn.connect(*args, **kwargs)
    except:
        conn.close()
        raise
    return conn
