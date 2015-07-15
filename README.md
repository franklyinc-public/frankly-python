#Frankly Python SDK

The Python module makes it easy to create deeper Frankly chat integrations in your app by interacting with Frankly's server APIs for managing Rooms, Messages, and Users.

Installation
------------

The frankly module can be installed like most python modules using pip:

```
$ pip install git+https://github.com/franklyinc/frankly-python.git#egg=frankly
```

**Compatiblity**

The frankly-python module requires Pytohn 2.7.9+ or Python 3.4.0+ to be used
successfully.

Testing
-------

The test suite relies on environment variables to figure out where to connect to
for tests that make API calls.  
You should set these three environment variables before running the tests:
```
export FRANKLY_APP_HOST=https://app.franklychat.com
export FRANKLY_APP_KEY={app key from the Frankly Console}
export FRANKLY_APP_SECRET={app secret from the Frankly Console}
```
The easiest way to run the test suite is to use the nose python module, then run:
```
$ python2 -m nose
```
```
$ python3 -m nose
```

Documentation
-------------

Please fine the complete Python integration guide and API reference, generated from [pdoc](https://github.com/BurntSushi/pdoc), at
[http://franklyinc.github.io/frankly-python](http://franklyinc.github.io/frankly-python/).


Making Improvements
-------------------

Frankly Platform provides a great way for brands to integrate chat in their iOS, Android, and Web apps in order to build and engage their communities. But of course, that's not possible without developers like you. Have ideas for improving the integration experience? Let us know by [creating a Github issue in this repo](https://github.com/franklyinc/frankly-python/issues/new)!


Access & Support
----------------

Right now Frankly Platform is limited in access. If you'd like to learn more about how to get access, please reach out to us by emailing [platform-support@franklychat.com](mailto:platform-support@franklychat.com).


