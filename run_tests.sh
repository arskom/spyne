#!/bin/bash -x
#
# Requirements:
#   1. A working build environment
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
[ -z "$WORKSPACE" ] && WORKSPACE="$PWD"

# Set up python

if   [ $PYVER == "2.6" ]; then
    FN=2.6.9/Python-2.6.9.tgz;

elif [ $PYVER == "2.7" ]; then
    FN=2.7.6/Python-2.7.6.tgz;

elif [ $PYVER == "3.3" ]; then
    FN=3.3.3/Python-3.3.3.tgz;

else
    echo "Unknown python version $PYVER";
    exit 2;

fi;

PREFIX="$(basename $FN .tgz)";

if [ -z "$(which easy_install-$PYVER)" ]; then
    wget -ct0 http://www.python.org/ftp/python/$FN;
    tar xf $(basename $FN);
    cd "$PREFIX";
    ./configure --prefix="$WORKSPACE/$PREFIX";
    make -j2 && make install;
fi;

# Set up distribute
export PATH="$WORKSPACE/$PREFIX/bin:$PATH";
wget -ct0 http://python-distribute.org/distribute_setup.py
python$PYVER distribute_setup.py

# Run tests
echo pyver: $PYVER

easy_install-$PYVER -U --user virtualenv
if [ '!' -d _ve ]; then
    ~/.local/bin/virtualenv-$PYVER --distribute _ve-$PYVER
fi;

source _ve-$PYVER/bin/activate

easy_install coverage

bash -c "coverage run --source=spyne setup.py test; exit 0"
coverage xml -i --omit=../spyne/test/*;
