

TESTS_ROOT=$(shell dirname $$(python -c "import spyne.test; print(spyne.test.__file__)"))
PYTEST=py.test -v --tb=short

test:
	$(PYTEST) $(TESTS_ROOT)/{test_*,interface,model,protocol,wsdl}
	$(PYTEST) $(TESTS_ROOT)/interop/test_httprpc.py
	$(PYTEST) $(TESTS_ROOT)/interop/test_soap_client_http.py
	$(PYTEST) $(TESTS_ROOT)/interop/test_soap_client_zeromq.py
	$(PYTEST) $(TESTS_ROOT)/interop/test_suds.py
	$(TRIAL)  $(TESTS_ROOT)/interop/test_soap_client_http_twisted.py

	cd $(TESTS_ROOT)/interop; ./test_wsi.py
