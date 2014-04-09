#!/usr/bin/env python
#encoding: utf8

from __future__ import print_function

import os
import re
import sys

from setuptools import setup
from setuptools import find_packages
from setuptools.command.test import test as TestCommand

try:
    import colorama
    colorama.init()
    from colorama import Fore
    RESET = Fore.RESET
    GREEN = Fore.GREEN
    RED = Fore.RED
except ImportError:
    RESET = ''
    GREEN = ''
    RED = ''

import inspect
from os.path import join, dirname, abspath
OWN_PATH = abspath(inspect.getfile(inspect.currentframe()))
EXAMPLES_DIR = join(dirname(OWN_PATH), 'examples')

v = open(os.path.join(os.path.dirname(__file__), 'spyne', '__init__.py'), 'r')
VERSION = re.match(r".*__version__ = '(.*?)'", v.read(), re.S).group(1)

SHORT_DESC="""A transport and architecture agnostic rpc library that focuses on
exposing public services with a well-defined API."""

LONG_DESC = """Spyne aims to save the protocol implementers the hassle of
implementing their own remote procedure call api and the application programmers
the hassle of jumping through hoops just to expose their services using multiple
protocols and transports.
"""

try:
    os.stat('CHANGELOG.rst')
    LONG_DESC += "\n\n" + open('CHANGELOG.rst', 'r').read()
except OSError:
    pass


###############################
# Testing stuff

def call_test(f, a, tests):
    import spyne.test
    from glob import glob
    from itertools import chain
    from multiprocessing import Process, Queue

    tests_dir = os.path.dirname(spyne.test.__file__)
    a.extend(chain(*[glob(join(tests_dir, test)) for test in tests]))

    queue = Queue()
    p = Process(target=_wrapper(f), args=[a, queue])
    p.start()
    p.join()

    ret = queue.get()
    if ret == 0:
        print(tests, "OK")
    else:
        print(tests, "FAIL")

    return ret


def _wrapper(f):
    def _(args, queue):
        try:
            retval = f(args)
        except TypeError: # it's a pain to call trial.
            sys.argv = ['trial']
            sys.argv.extend(args)
            retval = f()
        queue.put(retval)
    return _


def run_tests_and_create_report(report_name, *tests, **kwargs):
    import spyne.test
    import pytest
    from glob import glob
    from itertools import chain

    if os.path.isfile(report_name):
        os.unlink(report_name)

    tests_dir = os.path.dirname(spyne.test.__file__)

    args = ['--tb=short', '--junitxml=%s' % report_name]
    args.extend('--{0}={1}'.format(k, v) for k, v in kwargs.items())
    args.extend(chain(*[glob("%s/%s" % (tests_dir, test)) for test in tests]))

    return pytest.main(args)


_ctr = 0


def call_pytest(*tests, **kwargs):
    global _ctr

    _ctr += 1
    file_name = 'test_result.%d.xml' % _ctr
    return run_tests_and_create_report(file_name, *tests, **kwargs)


def call_pytest_subprocess(*tests, **kwargs):
    global _ctr
    import pytest
    _ctr += 1
    file_name = 'test_result.%d.xml' % _ctr
    if os.path.isfile(file_name):
        os.unlink(file_name)
    args = ['--tb=line', '--junitxml=%s' % file_name]
    args.extend('--{0}={1}'.format(k, v) for k, v in kwargs.items())
    return call_test(pytest.main, args, tests)

def call_trial(*tests, **kwargs):
    import spyne.test
    from glob import glob
    from itertools import chain

    global _ctr
    _ctr += 1
    file_name = 'test_result.%d.subunit' % _ctr
    with SubUnitTee(file_name):
        tests_dir = os.path.dirname(spyne.test.__file__)
        sys.argv = ['trial', '--reporter=subunit']
        sys.argv.extend('--{0}={1}'.format(k, v) for k, v in kwargs.items())
        sys.argv.extend(chain(*[glob(join(tests_dir, test)) for test in tests]))

        from twisted.scripts.trial import Options
        from twisted.scripts.trial import _makeRunner
        from twisted.scripts.trial import _getSuite

        config = Options()
        config.parseOptions()

        trialRunner = _makeRunner(config)
        suite = _getSuite(config)
        test_result = trialRunner.run(suite)

    try:
        subunit2junitxml(_ctr)
    except Exception as e:
        # this is not super important.
        print(e)

    return int(not test_result.wasSuccessful())


class InstallTestDeps(TestCommand):
    pass


def subunit2junitxml(ctr):
    from testtools import ExtendedToStreamDecorator
    from testtools import StreamToExtendedDecorator

    from subunit import StreamResultToBytes
    from subunit.filters import filter_by_result
    from subunit.filters import run_tests_from_stream

    from spyne.util.six import BytesIO

    from junitxml import JUnitXmlResult

    sys.argv = ['subunit-1to2']
    subunit1_file_name = 'test_result.%d.subunit' % ctr

    subunit2 = BytesIO()
    run_tests_from_stream(open(subunit1_file_name, 'rb'),
                    ExtendedToStreamDecorator(StreamResultToBytes(subunit2)))
    subunit2.seek(0)

    sys.argv = ['subunit2junitxml']
    sys.stdin = subunit2

    def f(output):
        return StreamToExtendedDecorator(JUnitXmlResult(output))

    junit_file_name = 'test_result.%d.xml' % ctr

    filter_by_result(f, junit_file_name, True, False, protocol_version=2,
                                passthrough_subunit=True, input_stream=subunit2)


class ExtendedTestCommand(TestCommand):

    """TestCommand customized to project needs."""

    user_options = TestCommand.user_options + [
        ('capture=', 'k', "py.test output capture control (see py.test "
         "--capture)"),
    ]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.capture = 'fd'

    def finalize_options(self):
        TestCommand.finalize_options(self)

        self.test_args = []
        self.test_suite = True


class RunTests(ExtendedTestCommand):

    def run_tests(self):
        print("running tests")
        sys.path.append(join(EXAMPLES_DIR, 'django'))
        os.environ['DJANGO_SETTINGS_MODULE'] = 'rpctest.settings'
        ret = 0
        ret = call_pytest('interface', 'model', 'multipython', 'protocol',
                          'test_null_server.py', 'test_service.py',
                          'test_soft_validation.py', 'test_util.py',
                          'test_sqlalchemy.py',
                          'test_sqlalchemy_deprecated.py',
                          # here we run django tests in the same process
                          # for coverage reason
                          'interop/test_django.py',
                          'interop/test_pyramid.py', capture=self.capture) or ret
        # test different versions of Django
        # FIXME: better to use tox in CI script
        # For now we run it here
        from tox._config import parseconfig
        from tox._cmdline import Session
        tox_args = ['-ctox.django.ini']
        config = parseconfig(tox_args, 'tox')
        ret = Session(config).runcommand()

        ret = call_pytest_subprocess('interop/test_httprpc.py',
                                     capture=self.capture) or ret
        ret = call_pytest_subprocess('interop/test_soap_client_http.py',
                                     capture=self.capture) or ret
        ret = call_pytest_subprocess('interop/test_soap_client_zeromq.py',
                                     capture=self.capture) or ret
        ret = call_pytest_subprocess('interop/test_suds.py',
                                     capture=self.capture) or ret
        ret = call_trial('interop/test_soap_client_http_twisted.py',
                         'transport/test_msgpack.py', capture=self.capture) or ret

        if ret == 0:
            print(GREEN + "All that glisters is not gold." + RESET)
        else:
            print(RED + "Something is rotten in the state of Denmark." + RESET)

        raise SystemExit(ret)


class RunDjangoTests(ExtendedTestCommand):

    """Run django interoperability tests.

    Useful for Tox.

    """

    def run_tests(self):
        import django
        print("running django tests")
        sys.path.append(join(EXAMPLES_DIR, 'django'))
        os.environ['DJANGO_SETTINGS_MODULE'] = 'rpctest.settings'
        file_name = 'test_result_django_{0}.xml'.format(django.get_version())
        ret = run_tests_and_create_report(file_name, 'interop/test_django.py',
                                          capture=self.capture)

        if ret == 0:
            print(GREEN + "All Django tests passed." + RESET)
        else:
            print(RED + "At least one Django test failed." + RESET)

        raise SystemExit(ret)


class RunMultiPythonTests(TestCommand):

    """Run tests compatible with different python implementations. """

    def finalize_options(self):
        TestCommand.finalize_options(self)

        self.test_args = []
        self.test_suite = True

    def get_python_flavour(self):
        try:
            # CPython2, PyPy
            return sys.subversion[0]
        except AttributeError:
            pass

        try:
            # CPython3
            return sys.implementation.cache_tag
        except AttributeError:
            pass

        try:
            # Jython
            return sys.JYTHON_JAR
        except AttributeError:
            pass

        raise NotImplementedError

    def run_tests(self):
        flavour = self.get_python_flavour()
        file_name = 'test_result_multi_python_{0}.xml'.format(flavour)
        ret = run_tests_and_create_report(file_name, 'multipython')

        if ret == 0:
            print(GREEN + "All multi Python tests passed." + RESET)
        else:
            print(RED + "At least one multi Python test failed." + RESET)

        raise SystemExit(ret)


multi_python_test_reqs = ['pytest', 'coverage', 'junitxml']

if 'test_multi_python' in sys.argv:
    test_reqs = multi_python_test_reqs
else:
    test_reqs = multi_python_test_reqs + [
        'pytest', 'werkzeug', 'sqlalchemy',
        'lxml>=2.3', 'pyyaml', 'pyzmq', 'twisted', 'colorama',
        'msgpack-python', 'webtest', 'django', 'pytest_django',
        'python-subunit', 'pyramid',
        'tox'
    ]

    if sys.version_info < (3,0):
        test_reqs.extend(['pyparsing<1.99', 'suds'])
    else:
        test_reqs.extend(['pyparsing'])


class SubUnitTee(object):
    def __init__(self, name):
        self.name = name
    def __enter__(self):
        self.file = open(self.name, 'wb')
        self.stdout = sys.stdout
        self.stderr = sys.stderr
        sys.stdout = sys.stderr = self

    def __exit__(self, *args):
        sys.stdout = self.stdout
        sys.stderr = self.stderr
        print("CLOSED")
        self.file.close()

    def writelines(self, data):
        for d in data:
            self.write(data)
            self.write('\n')

    def write(self, data):
        if data.startswith("test:") \
                or data.startswith("successful:") \
                or data.startswith("error:") \
                or data.startswith("failure:") \
                or data.startswith("skip:") \
                or data.startswith("notsupported:"):
            self.file.write(data)
            if not data.endswith("\n"):
                self.file.write("\n")

        self.stdout.write(data)

    def read(self,d=0):
        return ''

    def flush(self):
        self.stdout.flush()
        self.stderr.flush()

# Testing stuff ends here.
###############################

setup(
    name='spyne',
    packages=find_packages(),

    version=VERSION,
    description=SHORT_DESC,
    long_description=LONG_DESC,
    classifiers=[
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Operating System :: OS Independent',
        'Natural Language :: English',
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ],
    keywords=('soap', 'wsdl', 'wsgi', 'zeromq', 'rest', 'rpc', 'json', 'http',
              'msgpack', 'xml', 'django', 'pyramid', 'postgresql', 'sqlalchemy',
              'werkzeug', 'twisted', 'yaml'),
    author='Burak Arslan',
    author_email='burak+spyne@arskom.com.tr',
    maintainer='Burak Arslan',
    maintainer_email='burak+spyne@arskom.com.tr',
    url='http://spyne.io',
    license='LGPL-2.1',
    zip_safe=False,
    install_requires=[
      'pytz',
    ],

    entry_points={
        'console_scripts': [
            'sort_wsdl=spyne.test.sort_wsdl:main',
        ]
    },

    tests_require = test_reqs,
    cmdclass = {'test': RunTests, 'install_test_deps': InstallTestDeps,
                'test_django': RunDjangoTests,
                'test_multi_python': RunMultiPythonTests
               },
)
