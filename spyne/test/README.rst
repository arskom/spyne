
*********************
Running Tests Locally
*********************

While the test coverage for Spyne is not that bad, we always accept new tests
that cover new use-cases. Please consider contributing tests even if your
use-case is working fine! Given the nature of open-source projects, Spyne may
shift focus or change maintainers in the future. This can result in patches
which may cause incompatibilities with your existing code base. The only way to
detect such corner cases is to have a great test suite.

Spyne's master repository is already integrated with travis-ci.org. Head over
to http://travis-ci.org/arskom/spyne to see it for yourself.

As the necessary configuration is already done, it's very simple to integrate
your own fork of Spyne with travis-ci.org, which should come in handy even if
you don't plan to be a long-time contributor to Spyne. Just sign in with your
Github account and follow instructions.

If you want to run the tests yourself, just run: ::

    python setup.py test

This call will install *every* possible dependency of Spyne in the current
working directory.

If you don't want this or just want to run a specific test,
`pytest <http://pytest.org/latest/>`_  is a nice tool that lets you do just
that: ::

    py.test -v --tb=short spyne/test/protocol/test_json.py

You can run tests directly by executing them as well. This will use Python's
builtin ``unittest`` package which is less polished, but just fine. ::

    spyne/test/protocol/test_json.py

Note that just running ``py.test`` or similar powerful test-juggling software
naively in the root directory of tests won't work. Spyne runs some
interoperability tests by starting an actual daemon listening to a particular
port and then making (or processing) real requests, so running all tests in one
go is problematic. The rather specialized logic in setup.py for running tests
is the result of these quirks. Patches are welcome!


SOAP Interoperability Tests
===========================

The interoperability servers require twisted.web.

Python
-------

Python interop tests currently use Spyne's own clients and suds. For The suds
test is the first thing we check and try not to break.

Ruby
----

You need Ruby 1.8.x to run the ruby interop test against soap_http_basic.
Unfortunately, the Ruby Soap client does not do proper handling of namespaces,
so you'll need to turn off strict validation if you want to work with ruby
clients.

Ruby test module is very incomplete, implementing only two (echo_string and
echo_integer) tests. We're looking for volunteers who'd like to work on
increasing test coverage for other use cases.

.Net
----

There isn't any .Net tests for Spyne. WS-I test compliance reportedly covers
.Net use cases as well. Patches are welcome!

Java
----

The WS-I test is written in Java. But unfortunately, it only focuses on Wsdl
document and not the Soap functionality itself. We're looking for volunteers
who'd like to work on writing Java interop tests for spyne.

To run the Wsdl tests, you should first get wsi-interop-tools package from
http://ws-i.org and unpack it next to test_wsi.py. Here are the relevant links:

http://www.ws-i.org/deliverables/workinggroup.aspx?wg=testingtools
http://www.ws-i.org/Testing/Tools/2005/06/WSI_Test_Java_Final_1.1.zip

See also test_wsi.py for more info.

Now run the soap_http_basic interop test server and run test_wsi.py. If all goes
well, you should get a new wsi-report-spyne.xml file in the same directory.

Here's the directory tree from a working setup:

::

    |-- README.rst
    |-- (...)
    |-- interop
    |   |-- (...)
    |   |-- test_wsi.py
    |   `-- wsi-test-tools
    |       |-- License.htm
    |       |-- README.txt
    |       `-- (...)
    `-- (...)


***************************
Integrating with CI systems
***************************

Spyne is already integrated with Jenkins and travis-ci.org.

The travis configuration file is located in the root of the source repository,
under its standard name: .travis.yml

A script for running Spyne test suite inside Jenkins can also be found in the
same directory as this README file, under the name jenkins.sh. Paste it to the
"executable script" section in jenkins configuration page.

