# coding: utf-8

"""Test logging utilities."""

import logging
import unittest

from StringIO import StringIO

from lxml import etree
from spyne.application import Application
from spyne.decorator import rpc
from spyne.error import Fault
from spyne.model import String
from spyne.protocol.soap import Soap11
from spyne.service import ServiceBase
from spyne.server.wsgi import WsgiApplication
from spyne.util.logtools import log_server_faults

Application.transport = 'test'


def start_response(code, headers):
    print(code, headers)


class TestLogTools(unittest.TestCase):

    """Test case for logging utilities."""

    def test_log_server_faults(self):
        """Test if log_server_faults works for server faults."""

        class SomeService(ServiceBase):
            @rpc(_body_style='bare', _returns=String)
            def some_call(ctx):
                raise Fault('Server.SomeServerFault', 'Some server fault')

        app = Application([SomeService], 'tns',
                          in_protocol=Soap11(),
                          out_protocol=Soap11(cleanup_namespaces=True))
        app.event_manager.add_listener('method_fault_object',
                                       log_server_faults)

        req = """
        <senv:Envelope  xmlns:senv="http://schemas.xmlsoap.org/soap/envelope/"
                        xmlns:tns="tns">
            <senv:Body>
                <tns:some_call/>
            </senv:Body>
        </senv:Envelope>
        """

        server = WsgiApplication(app)
        resp = etree.fromstring(''.join(server({
            'QUERY_STRING': '',
            'PATH_INFO': '/call',
            'REQUEST_METHOD': 'GET',
            'SERVER_NAME': 'localhost',
            'wsgi.input': StringIO(req)
        }, start_response, "http://null")))

    def test_not_log_client_faults(self):
        """Test if log_server_faults works for client faults."""

        class SomeService(ServiceBase):
            @rpc(_body_style='bare', _returns=String)
            def some_call(ctx):
                raise Fault('Client.SomeClientFault', 'Some client fault')

        app = Application([SomeService], 'tns',
                          in_protocol=Soap11(),
                          out_protocol=Soap11(cleanup_namespaces=True))
        app.event_manager.add_listener('method_fault_object',
                                       log_server_faults)

        req = """
        <senv:Envelope  xmlns:senv="http://schemas.xmlsoap.org/soap/envelope/"
                        xmlns:tns="tns">
            <senv:Body>
                <tns:some_call/>
            </senv:Body>
        </senv:Envelope>
        """

        server = WsgiApplication(app)
        resp = etree.fromstring(''.join(server({
            'QUERY_STRING': '',
            'PATH_INFO': '/call',
            'REQUEST_METHOD': 'GET',
            'SERVER_NAME': 'localhost',
            'wsgi.input': StringIO(req)
        }, start_response, "http://null")))

if __name__ == '__main__':
    logging.basicConfig(level=logging.ERROR)
    unittest.main()
