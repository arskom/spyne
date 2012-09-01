
*************
Running Tests
*************

While the test coverage for Spyne is not that bad, we always accept new tests
that cover new use-cases. Please consider contributing tests even if your
use-case is working fine! Given the nature of open-source projects, Spyne may
shift focus or change maintainers in the future. This can result in patches
which may cause incompatibilities with your existing code base. The only way to
detect such corner cases is to have a great test suite.

Spyne's master repository is already integrated with travis-ci.org. Head over to
http://travis-ci.org/arskom/spyne to see it for yourself.

As the necessary configuration is already done, It's very simple to integrate
your own fork of Spyne. Just sign in with your Github account and follow
instructions.

If you want to run the tests yourself, `pytest <http://pytest.org/latest/>`_ : ::

    python setup.py test

or you can run individiual tests with py.test: ::

    py.test -v --tb=short spyne/test/protocol/test_json.py

or directly by executing them: ::

    spyne/test/protocol/test_json.py

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
