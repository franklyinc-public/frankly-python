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

from datetime import datetime
from iso8601 import parse_date
from json import JSONDecoder as BaseJsonDecoder
from json import JSONEncoder as BaseJsonEncoder

import json
import logging
import six

logging.getLogger('iso8601').setLevel(logging.ERROR)

__all__ = [
    'Object',
    'JsonDecoder',
    'JsonEncoder',
]

class Object(dict):
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

class JsonDecoder(BaseJsonDecoder):

    def __init__(self, **kwargs):
        kwargs['strict'] = False
        kwargs['object_pairs_hook'] = Object
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
        if len(obj) > 50 or 'T' not in obj:
            return obj
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
