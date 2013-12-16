#!/bin/bash -x
#
# Requirements:
#   1. A working build environment. Only tested on linux.
#
# Usage:
#   Run it like this:
#     $ PYVER=3.3 ./run_tests.sh
#
#   When missing, PYVER defaults to '2.7'.
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
PYTHON="$WORKSPACE/$PREFIX/bin/python$PYVER";
EA="$WORKSPACE/$PREFIX/bin/easy_install-$PYVER";
COVERAGE="$WORKSPACE/$PREFIX/bin/coverage-$PYVER";

# Set up python
if [ ! -f "$EA" ]; then
    # Set up the interpreter
  (
    mkdir -p .data
    cd .data
    wget -ct0 http://www.python.org/ftp/python/$FN;
    tar xf $(basename $FN);
    cd "$PREFIX";
    ./configure --prefix="$WORKSPACE/$PREFIX";
    make -j2 && make install;
  );

  # Set up distribute
  $PYTHON "$WORKSPACE"/bin/distribute_setup.py

  # Set up coverage
  $EA coverage
fi;

# Run tests
bash -c "$COVERAGE run --source=spyne setup.py test; exit 0"

# Generate coverage report
$COVERAGE xml -i --omit=spyne/test/*;
