#!/usr/bin/env python
#
# spyne - Copyright (C) Spyne contributors.
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301

import unittest

from webtest import TestApp as _TestApp  # avoid confusing py.test

from spyne.application import Application
from spyne.decorator import srpc
from spyne.service import Service
from spyne.model.primitive import Integer, Unicode
from spyne.model.complex import Iterable
from spyne.protocol.soap import Soap11
from spyne.protocol.http import HttpRpc
from spyne.protocol.json import JsonDocument
from spyne.server.wsgi import WsgiApplication

from spyne.const.xml import PREFMAP, NS_WSDL11_SOAP

def strip_whitespace(string):
    return ''.join(string.split())


class TestOperationRequestSuffix(unittest.TestCase):
    """
    test different protocols with REQUEST_SUFFIX and _operation_name
    _in_message_name is a concern, will test that as well
    """

    default_function_name = 'echo'

    # output is not affected, will use soap output for all tests
    result_body = '''
        <soap11env:Body>
            <tns:echoResponse>
                <tns:echoResult>
                    <tns:string>Echo, test</tns:string>
                    <tns:string>Echo, test</tns:string>
                </tns:echoResult>
            </tns:echoResponse>
        </soap11env:Body>'''

    def get_function_names(self, suffix, _operation_name=None,
                           _in_message_name=None):
        """This tests the logic of how names are produced.
        Its logic should match expected behavior of the decorator.
        returns operation name, in message name, service name depending on
        args"""
        function_name = self.default_function_name

        if _operation_name is None:
            operation_name = function_name
        else:
            operation_name = _operation_name

        if _in_message_name is None:
            request_name = operation_name + suffix
        else:
            request_name = _in_message_name

        return function_name, operation_name, request_name

    def get_app(self, in_protocol, suffix, _operation_name=None,
                _in_message_name=None):
        """setup testapp dependent on suffix and _in_message_name"""

        import spyne.const
        spyne.const.REQUEST_SUFFIX = suffix

        class EchoService(Service):

            srpc_kparams = {'_returns': Iterable(Unicode)}
            if _in_message_name:
                srpc_kparams['_in_message_name'] = _in_message_name
            if _operation_name:
                srpc_kparams['_operation_name'] = _operation_name

            @srpc(Unicode, Integer, **srpc_kparams)
            def echo(string, times):
                for i in range(times):
                    yield 'Echo, %s' % string

        application = Application([EchoService],
            tns='spyne.examples.echo',
            in_protocol=in_protocol,
            out_protocol=Soap11()
        )
        app = WsgiApplication(application)

        testapp = _TestApp(app)

        # so that it doesn't interfere with other tests.
        spyne.const.REQUEST_SUFFIX = ''

        return testapp

    def assert_response_ok(self, resp):
        """check the default response"""
        self.assertEqual(resp.status_int, 200, resp)
        self.assertTrue(
            strip_whitespace(self.result_body) in strip_whitespace(str(resp)),
            '{0} not in {1}'.format(self.result_body, resp))

    ### application error tests ###
    def assert_application_error(self, suffix, _operation_name=None,
                                                         _in_message_name=None):
        self.assertRaises(ValueError,
                          self.get_app, Soap11(validator='lxml'), suffix,
                          _operation_name, _in_message_name)

    def test_assert_application_error(self):
        """check error when op namd and in name are both used"""
        self.assert_application_error(suffix='',
                                      _operation_name='TestOperationName',
                                      _in_message_name='TestMessageName')

    ### soap tests ###
    def assert_soap_ok(self, suffix, _operation_name=None,
                                                         _in_message_name=None):
        """helper to test soap requests"""

        # setup
        app = self.get_app(Soap11(validator='lxml'), suffix, _operation_name,
                           _in_message_name)

        function_name, operation_name, request_name = self.get_function_names(
            suffix, _operation_name, _in_message_name)

        soap_input_body = """
        <SOAP-ENV:Envelope xmlns:ns0="spyne.examples.echo"
        xmlns:ns1="http://schemas.xmlsoap.org/soap/envelope/"
        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/">
           <SOAP-ENV:Header/>
           <ns1:Body>
              <ns0:{0}>
                 <ns0:string>test</ns0:string>
                 <ns0:times>2</ns0:times>
              </ns0:{0}>
           </ns1:Body>
        </SOAP-ENV:Envelope>""".format(request_name)

        # check wsdl
        wsdl = app.get('/?wsdl')
        self.assertEqual(wsdl.status_int, 200, wsdl)
        self.assertTrue(request_name in wsdl,
                        '{0} not found in wsdl'.format(request_name))

        soap_strings = [
            '<wsdl:operation name="{0}"'.format(operation_name),
            '<{0}:operation soapAction="{1}"'.format(PREFMAP[NS_WSDL11_SOAP], operation_name),
            '<wsdl:input name="{0}">'.format(request_name),
            '<xs:element name="{0}"'.format(request_name),
            '<xs:complexType name="{0}">'.format(request_name),
        ]
        for soap_string in soap_strings:
            self.assertTrue(soap_string in wsdl,
                            '{0} not in {1}'.format(soap_string, wsdl))
        if request_name != operation_name:
            wrong_string = '<wsdl:operation name="{0}"'.format(request_name)
            self.assertFalse(wrong_string in wsdl,
                             '{0} in {1}'.format(wrong_string, wsdl))

        output_name = '<wsdl:output name="{0}Response"'.format(
            self.default_function_name)
        self.assertTrue(output_name in wsdl,
                        'REQUEST_SUFFIX or _in_message_name changed the '
                        'output name, it should be: {0}'.format(
                            output_name))

        # check soap operation succeeded
        resp = app.post('/', soap_input_body,
                                    content_type='applicaion/xml; charset=utf8')
        self.assert_response_ok(resp)

    def test_soap_with_suffix(self):
        self.assert_soap_ok(suffix='Request')

    def test_soap_no_suffix(self):
        self.assert_soap_ok(suffix='')

    def test_soap_with_suffix_with_message_name(self):
        self.assert_soap_ok(suffix='Request',
                            _in_message_name='TestInMessageName')

    def test_soap_no_suffix_with_message_name(self):
        self.assert_soap_ok(suffix='', _in_message_name='TestInMessageName')

    def test_soap_with_suffix_with_operation_name(self):
        self.assert_soap_ok(suffix='Request',
                            _operation_name='TestOperationName')

    def test_soap_no_suffix_with_operation_name(self):
        self.assert_soap_ok(suffix='', _operation_name='TestOperationName')

    ### json tests ###
    def assert_json_ok(self, suffix, _operation_name=None,
                       _in_message_name=None):
        """helper to test json requests"""

        # setup
        app = self.get_app(JsonDocument(validator='soft'), suffix,
                           _operation_name, _in_message_name)

        function_name, operation_name, request_name = self.get_function_names(
            suffix, _operation_name, _in_message_name)

        json_input_body = '{"' + request_name + '": {"string": "test", ' \
                                                '"times": 2}}'

        # check json operation succeeded
        resp = app.post('/', json_input_body,
                                  content_type='application/json; charset=utf8')
        self.assert_response_ok(resp)

    def test_json_with_suffix(self):
        self.assert_json_ok(suffix='Request')

    def test_json_no_suffix(self):
        self.assert_json_ok(suffix='')

    def test_json_with_suffix_with_message_name(self):
        self.assert_json_ok(suffix='Request',
                            _in_message_name='TestInMessageName')

    def test_json_no_suffix_with_message_name(self):
        self.assert_json_ok(suffix='', _in_message_name='TestInMessageName')

    def test_json_with_suffix_with_operation_name(self):
        self.assert_soap_ok(suffix='Request',
                            _operation_name='TestOperationName')

    def test_json_no_suffix_with_operation_name(self):
        self.assert_soap_ok(suffix='', _operation_name='TestOperationName')

    ### HttpRpc tests ###
    def assert_httprpc_ok(self, suffix, _operation_name=None,
                          _in_message_name=None):
        """Helper to test HttpRpc requests"""

        # setup
        app = self.get_app(HttpRpc(validator='soft'),
                           suffix, _operation_name, _in_message_name)

        function_name, operation_name, request_name = \
            self.get_function_names(suffix, _operation_name, _in_message_name)

        url = "/{0}?string=test&times=2".format(request_name)

        # check httprpc operation succeeded
        resp = app.get(url)
        self.assert_response_ok(resp)

    def test_httprpc_with_suffix(self):
        self.assert_httprpc_ok(suffix='Request')

    def test_httprpc_no_suffix(self):
        self.assert_httprpc_ok(suffix='')

    def test_httprpc_with_suffix_with_message_name(self):
        self.assert_httprpc_ok(suffix='Request',
                               _in_message_name='TestInMessageName')

    def test_httprpc_no_suffix_with_message_name(self):
        self.assert_httprpc_ok(suffix='', _in_message_name='TestInMessageName')

    def test_httprpc_with_suffix_with_operation_name(self):
        self.assert_soap_ok(suffix='Request',
                            _operation_name='TestOperationName')

    def test_httprpc_no_suffix_with_operation_name(self):
        self.assert_soap_ok(suffix='', _operation_name='TestOperationName')
