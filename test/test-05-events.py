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

import frankly.events as events
import unittest

class TestEmitter(unittest.TestCase):

    def test_01_on(self):
        x = { 'ok': False }

        def callback(value):
            x['ok'] = value

        emitter = events.Emitter()
        emitter.on('pulse', callback)

        emitter.emit('other', True)
        self.assertFalse(x['ok'])

        emitter.emit('pulse', True)
        self.assertTrue(x['ok'])

        emitter.emit('pulse', False)
        self.assertFalse(x['ok'])

    def test_02_once(self):
        x = { 'ok': False }

        def callback(value):
            x['ok'] = value

        emitter = events.Emitter()
        emitter.once('pulse', callback)

        emitter.emit('other', True)
        self.assertFalse(x['ok'])

        emitter.emit('pulse', True)
        self.assertTrue(x['ok'])

        emitter.emit('pulse', False)
        self.assertTrue(x['ok'])

    def test_03_iterator(self):
        emitter = events.Emitter()

        with events.Iterator(emitter, 'one', 'two', 'three') as iterator:
            emitter.emit('one', 1, plus=1)
            emitter.emit('two', 2, plus=2)
            emitter.emit('other')

            generator = iter(iterator)

            name, args, kwargs = next(generator)
            self.assertEqual(name, 'one')
            self.assertEqual(args, (1,))
            self.assertEqual(kwargs, {'plus': 1})

            name, args, kwargs = next(generator)
            self.assertEqual(name, 'two')
            self.assertEqual(args, (2,))
            self.assertEqual(kwargs, {'plus': 2})

        self.assertRaises(StopIteration, next, generator)
