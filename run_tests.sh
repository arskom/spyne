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
#   4. Call this script from Jenkins' "executable script" section in the
#      configuration page. In other words, type in './run_tests.sh'.
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

# set up postgres
if [ $(psql -tAlU postgres | cut -d "|" -f1 | grep -w spyne_test_$USER_${PYVER/./} | wc -l) -eq 1 ]; then
   psql -c "drop database spyne_test_$USER_${PYVER/./}" -U postgres
fi;

psql -c "create database spyne_test_$USER_${PYVER/./}" -U postgres

bash -c "coverage run --source=../spyne ../setup.py test; exit 0"
coverage xml -i --omit=../spyne/test/*;

);
