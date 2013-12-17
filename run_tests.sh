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

[ -z "$PYVER" ] && PYVER=cpy-2.7;
[ -z "$WORKSPACE" ] && WORKSPACE="$PWD";

PYIMPL=(${PYVER//-/ })
PYVER=${PYIMPL[1]}

if [ -z "$PYVER" ]; then
    PYVER=${PYIMPL[0]};
    PYIMPL=cpy;
else
    PYIMPL=${PYIMPL[0]}

fi

if [ $PYIMPL == "cpy" ]; then
    PYNAME=python$PYVER

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
    PYNAME=python$PYVER

    if [ $PYVER == "2.7" ]; then
        FN=ipy-2.7.4.zip

    else
        echo "Unknown Python version $PYIMPL-$PYVER";
        exit 2;

    fi;

    PREFIX="$(basename $FN .zip)";

elif [ $PYIMPL == "jpy" ]; then
    PYNAME=jython

    if [ $PYVER == "2.5" ]; then
        FN=2.5.3/jython-installer-2.5.3.jar;

    elif [ $PYVER == "2.7" ]; then
        FN=2.7-b1/jython-installer-2.7-b1.jar;

    else
        echo "Unknown Python version $PYIMPL-$PYVER";
        exit 2;

    fi;

    PREFIX="$(basename $FN .jar)";

else
    echo "Unknown Python implementation $PYIMPL";
    exit 2;
fi;

MONOVER=2.11.4
MONOPREFIX="$WORKSPACE/mono-$MONOVER"
XBUILD="$MONOPREFIX/bin/xbuild"

PYTHON="$WORKSPACE/$PREFIX/bin/$PYNAME";
EASY="$WORKSPACE/$PREFIX/bin/easy_install-$PYVER";
COVERAGE="$WORKSPACE/$PREFIX/bin/coverage-$PYVER";
COVERAGE2="$HOME/.local/bin/coverage-$PYVER"

if [ $PYIMPL == 'cpy' ]; then
    # Set up CPython
    if [ ! -x "$PYTHON" ]; then
      (
        mkdir -p .data; cd .data;

        wget -ct0 http://www.python.org/ftp/python/$FN;
        tar xf $(basename $FN);
        cd "$PREFIX";
        ./configure --prefix="$WORKSPACE/$PREFIX";
        make -j2 && make install;
      );
    fi;

elif [ $PYIMPL == 'jpy' ]; then
    if [ ! -x "$PYTHON" ]; then
      (
        mkdir -p .data; cd .data;

        FILE=$(basename $FN);
        wget -O $FILE -ct0 "http://search.maven.org/remotecontent?filepath=org/python/jython-installer/$FN";
        java -jar $FILE -s -d "$WORKSPACE/$PREFIX"

      );
    fi

elif [ $PYIMPL == 'ipy' ]; then
    # Set up Mono first
    # See: http://www.mono-project.com/Compiling_Mono_From_Tarball
    if [ ! -x "$XBUILD" ]; then
      (
        mkdir -p .data; cd .data;

        wget -ct0 http://download.mono-project.com/sources/mono/mono-$MONOVER.tar.bz2
        tar xf mono-$MONOVER.tar.bz2;
        cd mono-$MONOVER;
        ./configure --prefix=$WORKSPACE/mono-$MONOVER;
        make -j5 && make install;
      );
    fi

    # Set up IronPython
    # See: https://github.com/IronLanguages/main/wiki/Building#the-mono-runtime
    if [ ! -x "$PYTHON" ]; then
      (
        mkdir -p .data; cd .data;
        export PATH="$(dirname "$XBUILD"):$PATH"

        wget -ct0 "https://github.com/IronLanguages/main/archive/$FN";
        unzip -q "$FN";
        cd "main-$PREFIX";

        $XBUILD /p:Configuration=Release Solutions/IronPython.sln || exit 1

        mkdir -p "$(dirname "$PYTHON")";
        echo 'mono "$PWD/bin/Release/ir.exe" "${@}"' > $PYTHON;
        chmod +x $PYTHON;
      ) || exit 1;
    fi;

fi;

# Set up distribute
if [ ! -x "$EASY" ]; then
  $PYTHON "$WORKSPACE"/bin/distribute_setup.py;
fi;

if [ $PYIMPL == 'jpy' ]; then
    # Run tests. No coverage in jython.
    $PYTHON setup.py test;

else
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
fi;
