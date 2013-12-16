#!/bin/bash -x
#
# Sets up a Python testing environment from scratch. Mainly written for Jenkins.
#
# Requirements:
#   A working build environment inside the container. Only tested on Linux
#   variants.
#
# Usage:
#   Run it like this:
#
#     $ PYVER=3.3 ./run_tests.sh
#
#   - PYVER defaults to '2.7'.
#   - WORKSPACE defaults to $PWD. It's normally set by Jenkins.
#
# Jenkins guide:
#   1. Create a 'Multi configuration project'.
#   2. Set up stuff like git repo the usual way.
#   3. In the 'Configuration Matrix' section, create a user-defined axis named
#      'PYVER'. and set it to the Python versions you'd like to test, separated
#      by whitespace. For example: '2.7 3.3'
#   4. Add a new "Execute Shell" build step and type in './run_tests.sh'.
#   5. Add a new "Publish JUnit test report" post-build action and type in
#      'test_result.*.xml'
#   6. Add a new "Publish Cobertura Coverage Report" post-build action and type
#      in 'coverage.xml'. Install the "Cobertura Coverage Report" plug-in if you
#      don't see this option.
#   7. Have fun!
#

[ -z "$PYIMPL" ] && PYIMPL=cpy;
[ -z "$PYVER" ] && PYVER=2.7;
[ -z "$WORKSPACE" ] && WORKSPACE="$PWD";

if [ PYIMPL == "cpy" ]; then

    if   [ $PYVER == "2.6" ]; then
        FN=2.6.9/Python-2.6.9.tgz;

    elif [ $PYVER == "2.7" ]; then
        FN=2.7.6/Python-2.7.6.tgz;

    elif [ $PYVER == "3.3" ]; then
        FN=3.3.3/Python-3.3.3.tgz;

    else
        echo "Unknown python version $PYIMPL-$PYVER";
        exit 2;

    fi;

    PREFIX="$(basename $FN .tgz)";

elif [ $PYIMPL == "ipy" ]; then
    if [ $PYVER == "2.7" ]; then
        FN=ipy-2.7.4.zip

    else
        echo "Unknown Python version $PYIMPL-$PYVER";
        exit 2;

    fi;

    PREFIX="$(basename $FN .zip)";

else
    echo "Unknown Python implementation $PYIMPL";
    exit 2;
fi;

MONOVER=3.2.5
PYTHON="$WORKSPACE/$PREFIX/bin/python$PYVER";
EASY="$WORKSPACE/$PREFIX/bin/easy_install-$PYVER";
COVERAGE="$WORKSPACE/$PREFIX/bin/coverage-$PYVER";
COVERAGE2="$HOME/.local/bin/coverage-$PYVER"

if [ $PYIMPL == 'cpy' ]; then
    # Set up CPython
    if [ ! -x "$PYTHON" ]; then
      (
        mkdir -p .data;
        cd .data;
        wget -ct0 http://www.python.org/ftp/python/$FN;
        tar xf $(basename $FN);
        cd "$PREFIX";
        ./configure --prefix="$WORKSPACE/$PREFIX";
        make -j2 && make install;
      );
    fi;

elif [ $PYIMPL == 'ipy' ]; then
    # Set up Mono first
    # See: http://www.mono-project.com/Compiling_Mono_From_Tarball
    if [ ! -x "$MONO" ]; then
      (
        wget -ct0 http://download.mono-project.com/sources/mono/mono-$MONOVER.tar.bz2
        tar xf mono-$MONOVER.tar.bz2;
        cd mono-$MONOVER;
        ./configure --prefix=$WORKSPACE/mono-$MONOVER;
        make -j2 && make install;
      );
    fi

    # Set up IronPython
    # See: https://github.com/IronLanguages/main/wiki/Building#the-mono-runtime
    if [ ! -x "$PYTHON" ]; then
      (
        mkdir -p .data;
        cd .data;

        wget -ct0 "https://github.com/IronLanguages/main/archive/$FN";
        unzip "$FN";
        cd "main-$PREFIX";

        xbuild /p:Configuration=Release Solutions/IronPython.sln

        mkdir -p "$(dirname "$PYTHON")";
        echo 'mono "$PWD/bin/Release/ir.exe" "${@}"' > $PYTHON;
        chmod +x $PYTHON;
      );
    fi;

fi;

# Set up distribute
if [ ! -x "$EASY" ]; then
  $PYTHON "$WORKSPACE"/bin/distribute_setup.py;
fi;

# Set up coverage
if [ ! -x "$COVERAGE" ]; then
  $EASY coverage
fi;

# Sometimes, easy_install works in mysterious ways...
if [ ! -x "$COVERAGE" ]; then
  COVERAGE="$COVERAGE2"
fi;

# Run tests
bash -c "$COVERAGE run --source=spyne setup.py test; exit 0"

# Generate coverage report
$COVERAGE xml -i --omit=spyne/test/*;
