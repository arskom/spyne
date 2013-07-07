import unittest
from webtest import TestApp

from spyne.application import Application
from spyne.decorator import srpc
from spyne.service import ServiceBase
from spyne.model.primitive import Integer,Unicode
from spyne.model.complex import Iterable
from spyne.protocol.soap import Soap11
from spyne.protocol.http import HttpRpc
from spyne.protocol.json import JsonDocument
from spyne.server.wsgi import WsgiApplication

def strip_whitespace(string):
    return ''.join(string.split())

class TestRequestSuffix(unittest.TestCase):
    '''
    test different protocols with the request suffix
    _in_message_name is a concern, will test that as well
    '''

    default_service_name = 'echo'

    # output is not affected, will use soap output for all tests
    result_body = '''
        <senv:Body>
            <tns:echoResponse>
                <tns:echoResult>
                    <tns:string>Echo, test</tns:string>
                    <tns:string>Echo, test</tns:string>
                </tns:echoResult>
            </tns:echoResponse>
        </senv:Body>'''


    def get_app(self, in_protocol, suffix, _in_message_name = None):
        '''setup testapp dependent on suffix and _in_message_name'''
        import spyne.const
        spyne.const.REQUEST_SUFFIX = suffix

        class EchoService(ServiceBase):

            srpc_kparams = {'_returns': Iterable(Unicode)}
            if _in_message_name:
                srpc_kparams['_in_message_name'] = _in_message_name

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

        testapp = TestApp(app)
        return testapp


    def assert_response_ok(self, resp):
        '''check the default response'''
        self.assertEqual(resp.status_int, 200, resp)
        self.assertIn(strip_whitespace(self.result_body), strip_whitespace(str(resp)),
                      '{0} not in {1}'.format(self.result_body, resp))


    ### soap tests ###


    def assert_soap_ok(self, suffix, in_message_name=None):
        '''helper to test soap requests'''

        # setup
        app = self.get_app(Soap11(validator='lxml'), suffix, in_message_name)

        service_name = self.default_service_name
        if in_message_name:
            service_name = in_message_name
        request_name = service_name + suffix

        soap_input_body = """
        <SOAP-ENV:Envelope xmlns:ns0="spyne.examples.echo" xmlns:ns1="http://schemas.xmlsoap.org/soap/envelope/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/">
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
        self.assertIn(request_name, wsdl)

        soap_strings = [
            '<wsdl:operation name="{0}"'.format(service_name),
            '<soap:operation soapAction="{0}"'.format(service_name),
            '<wsdl:input name="{0}">'.format(request_name),
            '<xs:element name="{0}"'.format(request_name),
            '<xs:complexType name="{0}">'.format(request_name),
        ]
        for soap_string in soap_strings:
            self.assertIn(soap_string, wsdl, '{0} not in {1}'.format(soap_string, wsdl))

        output_name = '<wsdl:output name="{0}Response"'.format(self.default_service_name)
        self.assertIn(output_name, wsdl, 'REQUEST_SUFFIX or _in_message_name changed the output name, it should be: {0}'.format(output_name))

        # check soap operation succeeded
        resp = app.post('/', soap_input_body)
        self.assert_response_ok(resp)


    def test_soap_with_suffix(self):
        self.assert_soap_ok('Request')


    def test_soap_no_suffix(self):
        self.assert_soap_ok('')


    def test_soap_with_suffix_with_message_name(self):
        self.assert_soap_ok('Request', 'TestInMessageName')


    def test_soap_no_suffix_with_message_name(self):
        self.assert_soap_ok('', 'TestInMessageName')


    ### json tests ###


    def assert_json_ok(self, suffix, in_message_name=None):
        '''helper to test json requests'''

        # setup
        app = self.get_app(JsonDocument(validator='soft'), suffix, in_message_name)

        service_name = self.default_service_name
        if in_message_name:
            service_name = in_message_name
        request_name = service_name + suffix

        json_input_body = '{"'+ request_name+ '": {"string": "test", "times": 2}}'

        # check json operation succeeded
        resp = app.post('/', json_input_body)
        self.assert_response_ok(resp)


    def test_json_with_suffix(self):
        self.assert_json_ok('Request')


    def test_json_no_suffix(self):
        self.assert_json_ok('')


    def test_json_with_suffix_with_message_name(self):
        self.assert_json_ok('Request', 'TestInMessageName')


    def test_json_no_suffix_with_message_name(self):
        self.assert_json_ok('', 'TestInMessageName')


    ### HttpRpc tests ###


    def assert_httprpc_ok(self, suffix, in_message_name=None):
        '''helper to test HttpRpc requests'''

        # setup
        app = self.get_app(HttpRpc(validator='soft'), suffix, in_message_name)

        service_name = self.default_service_name
        if in_message_name:
            service_name = in_message_name
        request_name = service_name + suffix

        url = "/{0}?string=test&times=2".format(request_name)

        # check httprpc operation succeeded
        resp = app.get(url)
        self.assert_response_ok(resp)


    def test_httprpc_with_suffix(self):
        self.assert_httprpc_ok('Request')


    def test_httprpc_no_suffix(self):
        self.assert_httprpc_ok('')


    def test_httprpc_with_suffix_with_message_name(self):
        self.assert_httprpc_ok('Request', 'TestInMessageName')


    def test_httprpc_no_suffix_with_message_name(self):
        self.assert_httprpc_ok('', 'TestInMessageName')