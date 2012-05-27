
*************
Running Tests
*************

While the test coverage for Rpclib is not that bad, we always accept new tests
that cover new use-cases. Please consider contributing tests even if your
use-case is working fine! Given the nature of open-source projects, Rpclib may
shift focus or change maintainers in the future. This can result in patches
which may cause incompatibilities with your existing code base. The only way to
detect such corner cases is to have a great test suite.

run_tests.sh
============

This is a shell script to make it easier to run all tests in one go. Twisted
tests need to be run using trial. Interop tests start their own servers in the
background, so they (currently) need to be run one by one in separate
processes. This simple script heeds all these little things and is the
recommended way of running rpclib tests.

Requirements
============

While simply executing test modules is normally enough to run Python tests,
using py.test from pytest package is just a more pleasant way to run them.
Simply easy_install pytest to get it. You can run the following command in the
test directory: ::

    py.test -v --tb=short

You can use the module name as an argument: ::

    py.test -v --tb=short test_sqla.py

You can also choose which test to run: ::

    py.test -v --tb=short test_sqla.py -k test_same_table_inheritance

See `pytest documentation <http://pytest.org/latest/>`_ for more info.

Note that you need to do several other preparations to have the interop tests
working. See the next section for the specifics.

SOAP Interoperability Tests
===========================

The interoperability servers require twisted.web.

Python
-------

Python interop tests currently use Rpclib's own clients and suds. For The suds
test is the first thing we check and try not to break.

Two tests that fail in the suds interop tests due to the lack of proper assert
statements, so they're false alarms.

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

There isn't any .Net tests for rpclib. WS-I test compliance reportedly covers
.Net use cases as well. Patches are welcome!

Java
----

The WS-I test is written in Java. But unfortunately, it only focuses on Wsdl
document and not the Soap functionality itself. We're looking for volunteers
who'd like to work on writing Java interop tests for rpclib.

To run the Wsdl tests, you should first get wsi-interop-tools package from
http://ws-i.org and unpack it next to test_wsi.py. Here are the relevant links:

http://www.ws-i.org/deliverables/workinggroup.aspx?wg=testingtools
http://www.ws-i.org/Testing/Tools/2005/06/WSI_Test_Java_Final_1.1.zip

See also test_wsi.py for more info.

Now run the soap_http_basic interop test server and run test_wsi.py. If all goes
well, you should get a new wsi-report-rpclib.xml file in the same directory.

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
