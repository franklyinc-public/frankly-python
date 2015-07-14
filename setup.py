#!/usr/bin/env python
from distutils.core import setup

if __name__ == '__main__':
    setup(name              = 'frankly',
          version           = '0.1.0',
          description       = 'Frankly Python SDK',
          long_description  = 'The module provides types and functions for interacting with the Frankly API.',
          author            = 'Achille Roussel',
          author_email      = 'achille@franklychat.com',
          license           = 'MIT',
          url               = 'https://github.com/franklyinc/frankly-python',
          scripts           = [
              'bin/frankly-upload',
          ],
          packages          = [
              'frankly',
              'frankly.websocket',
          ],
          install_requires  = [
              'python-dateutil>=2.4.2',
              'pyjwt>=1.1.0',
              'requests>=2.4.0',
              'six>=1.9.0',
          ]
    )
