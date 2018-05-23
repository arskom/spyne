from unittest import TestCase

from spyne import MethodContext
from spyne.server import ServerBase
from spyne.service import ServiceBase
from spyne import Application
from spyne.protocol.soap import Soap11
from spyne.model import ComplexModel
from spyne.model.complex import XmlAttribute
from spyne.model.primitive import String
from spyne.util.odict import odict
from spyne.decorator import rpc

# Namespaces
XSI_NS = 'http://www.w3.org/2001/XMLSchema-instance'
SOAP_ENV = 'http://schemas.xmlsoap.org/soap/envelope/'
SOAP_ENC = 'http://schemas.xmlsoap.org/soap/encoding/'
CWMP_NS = 'urn:dslforum-org:cwmp-1-0'


class Tr069ComplexModel(ComplexModel):
    """ Base class for TR-069 models, to set common attributes. Does not appear
        in CWMP XSD file. """
    __namespace__ = CWMP_NS

class EventStruct(Tr069ComplexModel):
    _type_info = odict()
    _type_info["EventCode"] = String(max_length=64)
    _type_info["CommandKey"] = String(max_length=32)

class EventList(Tr069ComplexModel):
    _type_info = odict()
    _type_info["EventStruct"] = EventStruct.customize(max_occurs='unbounded')
    _type_info["arrayType"] = XmlAttribute(String, ns=SOAP_ENC)
    _type_info["type"] = XmlAttribute(String)


class Inform(Tr069ComplexModel):
    _type_info = odict()
    _type_info["Event"] = EventList

class AutoConfigServer(ServiceBase):
    @rpc(Inform,
         _returns=None,
         _body_style="bare")
    def Inform(ctx, request):
        return None

class Tr069Test(TestCase):
    """
    Tests for SOAP-ENC Attribute
    """

    def setUp(self):
        self.app = Application([AutoConfigServer],
                                    CWMP_NS,
                                    in_protocol=Soap11(validator='soft'),
                                    out_protocol=Soap11()
                                    )

    def test_parse_inform(self):
        cpe_string = b'''<?xml version="1.0" encoding="UTF-8"?>
        <SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/" xmlns:SOAP-ENC="http://schemas.xmlsoap.org/soap/encoding/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:cwmp="urn:dslforum-org:cwmp-1-0">
          <SOAP-ENV:Header>
            <cwmp:ID SOAP-ENV:mustUnderstand="1">CPE_1002</cwmp:ID>
          </SOAP-ENV:Header>
          <SOAP-ENV:Body SOAP-ENV:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
            <cwmp:Inform>
              <Event xsi:type="SOAP-ENC:Array" SOAP-ENC:arrayType="cwmp:EventStruct[1]">
                <EventStruct>
                  <EventCode>0 BOOTSTRAP</EventCode>
                  <CommandKey></CommandKey>
                </EventStruct>
              </Event>
              <MaxEnvelopes>1</MaxEnvelopes>
              <CurrentTime>1970-01-02T00:01:05.021239+00:00</CurrentTime>
              <RetryCount>2</RetryCount>
            </cwmp:Inform>
          </SOAP-ENV:Body>
        </SOAP-ENV:Envelope>
        '''

        server = ServerBase(self.app)

        ctx = MethodContext(server, MethodContext.SERVER)
        ctx.in_string = [cpe_string]
        ctx, = server.generate_contexts(ctx)

        if ctx.in_error is not None:
            print('In error: %s' % ctx.in_error)
        self.assertEqual(ctx.in_error, None)

        server.get_in_object(ctx)

        self.assertEqual(
            ctx.in_object.Event.EventStruct[0].EventCode, '0 BOOTSTRAP')
