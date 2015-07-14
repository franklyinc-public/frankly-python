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

from fcntl import fcntl
from fcntl import F_SETFD
from fcntl import FD_CLOEXEC
from socket import AF_INET
from socket import AF_INET6
from socket import AI_PASSIVE
from socket import IPPROTO_TCP
from socket import IPPROTO_UDP
from socket import SHUT_RDWR
from socket import SHUT_RD
from socket import SHUT_WR
from socket import SOL_SOCKET
from socket import SO_REUSEADDR
from socket import SO_TYPE
from socket import SOMAXCONN
from socket import SOCK_DGRAM
from socket import SOCK_STREAM
from socket import TCP_NODELAY
from types import MethodType
import os
import six
import socket as pysocket

__all__ = [
    'bind',
    'connect',
    'getaddrinfo',
    'getprototype',
    'listen',
    'socket',
]

def getaddrinfo(host, port, socktype=0, protocol=0, flags=0):
    return pysocket.getaddrinfo(host, port, 0, socktype, protocol, flags)

def getprototype(protocol):
    if protocol == 'tcp':
        return SOCK_STREAM, IPPROTO_TCP

    elif protocol == 'udp':
        return SOCK_DGRAM, IPPROTO_UDP

    else:
        raise ValueError("maestro.net.bind: unknown protocol: %s" % protocol)

class socket(object):

    if six.PY3:
        def __init__(self, family, socktype=SOCK_STREAM, protocol=0, fileno=None, timeout=None, socket=None):
            self._socket = socket if socket is not None else pysocket.socket(family, socktype, protocol, fileno)
            self.timeout = timeout

    else:
        def __init__(self, family, socktype=SOCK_STREAM, protocol=0, fileno=None, timeout=None, socket=None):
            if socket is not None:
                self._socket = socket

            elif fileno is None:
                self._socket = pysocket.socket(family, socktype, protocol)
                self.cloexec = True

            else:
                try:
                    self._socket = pysocket.fromfd(fileno, family, socktype, protocol)
                    self.cloexec = True
                finally:
                    os.close(fileno)

            self.timeout = timeout

    def close(self):
        return self._socket.close()

    def fileno(self):
        return self._socket.fileno()

    def accept(self, cloexec=True):
        raw_socket, address = self._socket.accept()
        sock = socket(raw_socket.family, socket=raw_socket)
        sock.settimeout(self.gettimeout())
        sock.setnodelay(self.getnodelay())
        sock.setcloexec(True)
        return sock, address

    def bind(self, address):
        return self._socket.bind(address)

    def connect(self, address):
        return self._socket.connect(address)

    def listen(self, backlog=SOMAXCONN):
        return self._socket.listen(backlog)

    def recv(self, size, flags=0):
        return self._socket.recv(size, flags)

    def recvfrom(self, size, flags=0):
        return self._socket.recvfrom(size, flags)

    def recv_into(self, buf, size=0, flags=0):
        return self._socket.recv_into(buf, size, flags)

    def send(self, data, flags=0):
        return self._socket.send(data, flags)

    def sendto(self, data, flags=0, address=None):
        return self._socket.sendto(data, flags, address)

    def sendall(self, data):
        return self._socket.sendall(data)

    def shutdown(self, how=SHUT_RDWR):
        return self._socket.shutdown(how)

    def gettimeout(self):
        return self._socket.gettimeout()

    def settimeout(self, time):
        return self._socket.settimeout(time)

    def getsockopt(self, level, name):
        return self._socket.getsockopt(level, name)

    def setsockopt(self, level, name, value):
        return self._socket.setsockopt(level, name, value)

    def getnodelay(self):
        return bool(self.getsockopt(IPPROTO_TCP, TCP_NODELAY))

    def setnodelay(self, enable):
        self.setsockopt(IPPROTO_TCP, TCP_NODELAY, 1 if bool(enable) else 0)

    def getreuseaddr(self):
        return bool(self.getsockopt(SOL_SOCKET, SO_REUSEADDR))

    def setreuseaddr(self, enable):
        self.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1 if bool(enable) else 0)

    def getcloexec(self):
        return bool(fcntl(self.fileno(), FD_CLOEXEC))

    def setcloexec(self, enable):
        return fcntl(self.fileno(), 1 if enable else 0, FD_CLOEXEC)

    def getpeername(self):
        return self._socket.getpeername()

    def getsockname(self):
        return self._socket.getsockname()

    def getsocktype(self):
        return self.getsockopt(SOL_SOCKET, SO_TYPE)

    def getprotocol(self):
        socktype = self.getsocktype()
        return IPPROTO_UDP if socktype == SOCK_DGRAM else IPPROTO_TCP

    @property
    def family(self):
        return self._socket.family

    @property
    def socktype(self):
        return self.getsocktype()

    @property
    def protocol(self):
        return self.getprotocol()

    if six.PY3:
        def recvmsg(self, size, ancbufsize=0, flags=0):
            return self._socket.recvmsg(size, ancbufsize, flags)

        def sendmsg(self, buffers, ancdata=tuple(), flags=0, address=None):
            return self._socket.sendmsg(buffers, ancdata, flags, address)

def bind(address=None, port=None, backlog=SOMAXCONN, timeout=None, fileno=None, protocol='tcp'):
    socktype, protocol = getprototype(protocol)

    if fileno is not None:
        return socket(AF_INET, socktype, protocol, fileno=fileno, timeout=timeout)

    error = None

    for addrinfo in getaddrinfo(address, port, socktype, protocol, flags=AI_PASSIVE):
        family, type, proto, _, sockaddr = addrinfo
        server = socket(family, type, proto, timeout=timeout)
        try:
            server.settimeout(timeout)
            server.setreuseaddr(True)
            if proto == IPPROTO_TCP:
                server.setnodelay(True)
                server.bind(sockaddr)
                server.listen(backlog)
            else:
                server.bind(sockaddr)
            return server
        except Exception as e:
            error = e
            server.close()

    if error is not None:
        raise error
    raise socket.error('failed to listen on %s' % repr((address, port)))

def connect(host, port, timeout=None, fileno=None, protocol='tcp'):
    socktype, protocol = getprototype(protocol)

    if fileno is not None:
        return socket(AF_INET, socktype, protocol, fileno=fileno, timeout=timeout)

    error = None

    for addrinfo in getaddrinfo(host, port, socktype, protocol):
        family, type, proto, _, sockaddr = addrinfo
        client = socket(family, type, proto)
        try:
            if proto == IPPROTO_TCP:
                client.setnodelay(True)
            client.settimeout(timeout)
            client.connect(sockaddr)
            return client
        except Exception as e:
            error = e
            client.close()

    if error is not None:
        raise error
    raise socket.error('failed to connect to %s' % host)
