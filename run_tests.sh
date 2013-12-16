#!/bin/bash -x
#
# Requirements:
#   1. easy_install executables of various Python installations accesible with
#      a Python version suffix. E.g. the easy_install-2.7 command should call
#      the easy_install script of a Python 2.7 environment.
#   2. A working Postgresql>=9.2 installation with 'trust' authentication.
#
# Usage:
#   Run it like this:
#     $ PYVER=3.3 ./run_tests.sh
#
# Jenkins guide:
#   1. Create a multi configuration project
#   2. In the 'Configuration Matrix' section, create a user-defined axis named
#      'PYVER'. and set it to the Python versions you'd like to test, separated
#      by whitespace. For example: '2.7 3.3'
#   3. Set up other stuff like git repo the usual way.
#   4. Add a new "Execute Shell" build step and type in './run_tests.sh'.
#   5. Add a new "Publish JUnit test report" post-build action and type in
#      '**/test_result.*.xml'
#   6. If you have the "Cobertura Coverage Report" plug-in, add a
#      'Publish Cobertura Coverage Report' post-build action and type in
#      '**/coverage.xml'.
#

[ -z "$PYVER" ] && PYVER=2.7

echo pyver: $PYVER
mkdir -p .test

(

cd .test;

easy_install-$PYVER -U --user virtualenv
if [ '!' -d _ve ]; then
    ~/.local/bin/virtualenv-$PYVER --distribute _ve-$PYVER
fi;

source _ve-$PYVER/bin/activate

easy_install coverage

bash -c "coverage run --source=../spyne ../setup.py test; exit 0"
coverage xml -i --omit=../spyne/test/*;

);
