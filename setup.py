#!/usr/bin/env python
#encoding: utf8

from __future__ import print_function

import io
import os
import re
import sys
import inspect

from glob import glob
from itertools import chain
from os.path import join, dirname, abspath

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

IS_PYPY = '__pypy__' in sys.builtin_module_names
OWN_PATH = abspath(inspect.getfile(inspect.currentframe()))
EXAMPLES_DIR = join(dirname(OWN_PATH), 'examples')
PYVER = ''.join([str(i) for i in sys.version_info[:2]])

with io.open(os.path.join(os.path.dirname(__file__), 'spyne', '__init__.py'), 'r') as v:
    VERSION = re.match(r".*__version__ = '(.*?)'", v.read(), re.S).group(1)

SHORT_DESC="A transport and architecture agnostic rpc library that focuses on" \
" exposing public services with a well-defined API."

LONG_DESC = """Homepage: http://spyne.io

Spyne aims to save the protocol implementers the hassle of
implementing their own remote procedure call api and the application programmers
the hassle of jumping through hoops just to expose their services using multiple
protocols and transports.
"""

try:
    os.stat('CHANGELOG.rst')
    with io.open('CHANGELOG.rst', 'rb') as f:
        LONG_DESC += u"\n\n" + f.read().decode('utf8')
except OSError:
    pass


###############################
# Testing stuff

def call_test(f, a, tests, env={}):
    import spyne.test
    from multiprocessing import Process, Queue

    tests_dir = os.path.dirname(spyne.test.__file__)
    if len(tests) > 0:
        a.extend(chain(*[glob(join(tests_dir, test)) for test in tests]))

    queue = Queue()
    p = Process(target=_wrapper(f), args=[a, queue, env])
    p.start()
    p.join()

    ret = queue.get()
    if ret == 0:
        print(tests or a, "OK")
    else:
        print(tests or a, "FAIL")

    print()

    return ret


def _wrapper(f):
    import traceback
    def _(args, queue, env):
        print("env:", env)
        for k, v in env.items():
            os.environ[k] = v
        try:
            retval = f(args)
        except SystemExit as e:
            retval = e.code
        except BaseException as e:
            print(traceback.format_exc())
            retval = 1

        queue.put(retval)

    return _


def run_tests_and_create_report(report_name, *tests, **kwargs):
    import spyne.test
    import pytest

    if os.path.isfile(report_name):
        os.unlink(report_name)

    tests_dir = os.path.dirname(spyne.test.__file__)

    args = [
        '--verbose',
        '--cov-report=', '--cov', 'spyne',
        '--cov-append',
        '--tb=short',
        '--junitxml=%s' % report_name,
    ]
    args.extend('--{0}={1}'.format(k, v) for k, v in kwargs.items())
    args.extend(chain(*[glob("%s/%s" % (tests_dir, test)) for test in tests]))

    return pytest.main(args)


_ctr = 0


def call_pytest(*tests, **kwargs):
    global _ctr

    _ctr += 1
    file_name = 'test_result.%d.xml' % _ctr
    os.environ['COVERAGE_FILE'] = '.coverage.%d' % _ctr

    return run_tests_and_create_report(file_name, *tests, **kwargs)


def call_pytest_subprocess(*tests, **kwargs):
    global _ctr
    import pytest

    _ctr += 1
    file_name = 'test_result.%d.xml' % _ctr
    if os.path.isfile(file_name):
        os.unlink(file_name)

    # env = {'COVERAGE_FILE': '.coverage.%d' % _ctr}
    env = {}

    args = [
        '--verbose',
        '--cov-append',
        '--cov-report=',
        '--cov', 'spyne',
        '--tb=line',
        '--junitxml=%s' % file_name
    ]
    args.extend('--{0}={1}'.format(k, v) for k, v in kwargs.items())
    return call_test(pytest.main, args, tests, env)


def call_tox_subprocess(env):
    import tox.session

    args = ['-e', env]

    return call_test(tox.session.main, args, [])

def call_coverage():
    import coverage.cmdline

    # coverage.cmdline.main(['combine'])
    # call_test(coverage.cmdline.main, ['combine'], [])
    call_test(coverage.cmdline.main, ['xml', '-i'], [])

    return 0


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
        cfn = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])),
                                                                      'tox.ini')
        from collections import OrderedDict
        djenvs = tuple(OrderedDict(((k, None) for k in
                            re.findall('py%s-dj[0-9]+' % PYVER,
                                open(cfn, 'rb').read().decode('utf8')))).keys())

        print("Running tests, including djenvs", djenvs)
        ret = 0
        tests = [
            'interface', 'model', 'multipython', 'protocol', 'util',

            'interop/test_pyramid.py',
            'interop/test_soap_client_http_twisted.py',

            'transport/test_msgpack.py'

            'test_null_server.py',
            'test_service.py',
            'test_soft_validation.py',
            'test_sqlalchemy.py',
            'test_sqlalchemy_deprecated.py',
        ]

        ret = call_pytest_subprocess(*tests, capture=self.capture) or ret
        ret = call_pytest_subprocess('interop/test_httprpc.py',
                                                    capture=self.capture) or ret
        ret = call_pytest_subprocess('interop/test_soap_client_http.py',
                                                    capture=self.capture) or ret
        ret = call_pytest_subprocess('interop/test_soap_client_zeromq.py',
                                                    capture=self.capture) or ret

        # excluding PyPy as it chokes here on LXML
        if not IS_PYPY:
            ret = call_pytest_subprocess('interop/test_suds.py',
                                                    capture=self.capture) or ret
            ret = call_pytest_subprocess('interop/test_zeep.py',
                                                    capture=self.capture) or ret
        for djenv in djenvs:
            ret = call_tox_subprocess(djenv) or ret

        if ret == 0:
            print(GREEN + "All that glisters is not gold." + RESET)
        else:
            print(RED + "Something is rotten in the state of Denmark." + RESET)

        print ("Generating coverage.xml")
        call_coverage()

        raise SystemExit(ret)


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
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: Implementation :: CPython',
        #'Programming Language :: Python :: Implementation :: Jython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Operating System :: OS Independent',
        'Natural Language :: English',
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ],
    keywords='soap wsdl wsgi zeromq rest rpc json http msgpack xml'
             ' django pyramid postgresql sqlalchemy twisted yaml',
    author='Burak Arslan',
    author_email='burak+package@spyne.io',
    maintainer='Burak Arslan',
    maintainer_email='burak+package@spyne.io',
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

    cmdclass = {
        'test': RunTests,
    },
)
