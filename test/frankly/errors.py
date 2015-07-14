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

import os

__all__ = [
    'Error',
]

class Error(Exception):

    def __init__(self, operation, path, status, reason):
        Exception.__init__(self, '[%s] %s' % (status, reason))

        if isinstance(path, list):
            if len(path) == 0:
                path = '/'
            else:
                path = '/' + os.path.join(*path)

        self.operation = operation
        self.path      = path
        self.status    = status
        self.reason    = reason

    def __str__(self):
        return 'error { operation = %s, path = %s, status = %s, reason = %s }' % (
            self.operation,
            self.path,
            self.status,
            self.reason,
        )

    def __repr__(self):
        return 'frankly.errors.Error { operation = %s, path = %s, status = %s, reason = %s }' % (
            self.operation,
            self.path,
            self.status,
            self.reason,
        )
