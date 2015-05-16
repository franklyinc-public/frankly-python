from __future__ import division
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import dateutil
import json

from datetime import datetime
from unittest import TestCase

from frankly import JsonDecoder
from frankly import JsonEncoder

def json_dumps(obj):
    return json.dumps(obj, cls=JsonEncoder)

def json_loads(s):
    return json.loads(s, cls=JsonDecoder)

class TestJsonEncoder(TestCase):

    def test_encode_string(self):
        self.assertEqual("{\"hello\":\"world!\"}", json_dumps({
            'hello': 'world!',
        }))

    def test_encode_date(self):
        self.assertEqual("{\"date\":\"2015-05-11T12:33:42.000Z\"}", json_dumps({
            'date': datetime(
                year        = 2015,
                month       = 5,
                day         = 11,
                hour        = 12,
                minute      = 33,
                second      = 42,
                tzinfo      = dateutil.tz.tzutc()
            ),
        }))

class TestJsonDecoder(TestCase):

    def test_decode_string(self):
        self.assertEqual({'hello': 'world!'}, json_loads("{\"hello\":\"world!\"}"))

    def test_decode_date(self):
        self.assertEqual({
            'date': datetime(
                year        = 2015,
                month       = 5,
                day         = 11,
                hour        = 12,
                minute      = 33,
                second      = 42,
                tzinfo      = dateutil.tz.tzutc()
                ),
            }, json_loads("{\"date\":\"2015-05-11T12:33:42.000Z\"}"))

