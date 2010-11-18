
Axis Interoperability
=====================

The Apache Axis project is one of the most popular SOAP implementations around,
so it was very important for rpclib to easily work with it. As a subproject of
rpclib the axis_rpclib test suite was created to make sure rpclib and Axis
can understand each other. This test uses Apache Ant to run the tests and
generates the client-side java classes using the wsdl2java command.

How to run the test
-------------------

    * Start the rpclib interop service from the rpclib directory

       % python tests/interop_service.py

    * Modify the build.xml in axis_rpclib to reflect the correct url and path to the axis library
    * run the tests

      % ant
      Buildfile: build.xml

      wsdl2java:

      compile:
          [javac] Compiling 9 source files
          [javac] Note: Some input files use unchecked or unsafe operations.
          [javac] Note: Recompile with -Xlint:unchecked for details.

      test:
           [java] Results -------------------------------------------
           [java]         Total Tests 16
           [java]         Failures 0

      BUILD SUCCESSFUL
      Total time: 7 seconds


