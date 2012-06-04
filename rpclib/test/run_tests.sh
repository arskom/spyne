#!/bin/bash -x

py.test -v test_* interface/* model/* protocol/* --tb=short

py.test -v interop/test_httprpc.py
py.test -v interop/test_soap_client_http.py
trial      interop/test_soap_client_http_twisted.py
py.test -v interop/test_soap_client_zeromq.py
py.test -v interop/test_suds.py

cd interop
./test_wsi.py
cd -
