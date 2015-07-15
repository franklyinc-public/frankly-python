#!/usr/bin/env python
from distutils.core import setup

import sys
import imp

if __name__ == '__main__':
    frankly = imp.load_module('frankly', *imp.find_module('frankly', ['.']))

    setup(name              = 'frankly-python',
          version           = frankly.__version__,
          description       = 'Frankly Python SDK',
          long_description  = 'The module provides types and functions for interacting with the Frankly API.',
          author            = 'Achille Roussel',
          author_email      = 'achille@franklychat.com',
          license           = 'MIT',
          url               = 'https://github.com/franklyinc/frankly-python',
          packages          = [
              'frankly',
              'frankly.websocket',
          ],
          install_requires  = [
              'iso8601>=0.1.10',
              'http_parser>=0.8.3',
              'msgpack-python>=0.4.6',
              'pyjwt>=1.1.0',
              'requests>=2.4.0',
              'six>=1.9.0',
          ]
    )

