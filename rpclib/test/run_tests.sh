#!/bin/bash -x

PYTEST_ARGS="-v --tb=short"

py.test $PYTEST_ARGS test_* interface/* model/* protocol/*
py.test $PYTEST_ARGS interop/test_httprpc.py
py.test $PYTEST_ARGS interop/test_soap_client_http.py
py.test $PYTEST_ARGS interop/test_soap_client_zeromq.py
py.test $PYTEST_ARGS interop/test_suds.py
trial      interop/test_soap_client_http_twisted.py

cd interop
./test_wsi.py
cd -
