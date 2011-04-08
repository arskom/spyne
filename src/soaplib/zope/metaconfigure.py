import cgi
from cgi import parse_header
from collections import namedtuple
from zope.app.publisher.browser.viewmeta import page
from lxml import etree

import soaplib
from soaplib.core import Application
from soaplib.core.model.exception import Fault
from soaplib.core._base import resolve_hrefs
from soaplib.core.mime import collapse_swa, apply_mtom


string_encoding = 'utf-8'
HTTP_500 = 500 #'500 Internal server error'
HTTP_200 = 200 #'200 OK'
HTTP_405 = 405 #'405 Method Not Allowed'

RespComp = namedtuple("RespComp", "xml_response headers resp_code")


def consturct_soaplib_application(service_list, tns):
    soap_app = Application(service_list, tns)
    soap_app.transport = "http://schemas.xmlsoap.org/soap/http"
    return soap_app


def handle_soaplib_req(_context, name, for_, service_definitions, app_namespace):
    """Not working just yet"""

    soap_app = consturct_soaplib_application(service_definitions, app_namespace)
    soap_handler = SoaplibHandler(soap_app)
    page(_context, name, for_, class_=soap_handler)


class SoaplibHandler(object):
    """A ZTK soaplib parser."

    This handlers parsers a HttpRequest and returns a text/xml response
    """

    def __init__(self, request, soap_app):
        self.request = request
        self.soap_app = soap_app


    def handle_request(self):
        if self.is_wsdl():
            return self.get_wsdl()

        try:
            resp_comp = self.parse_soap_request()
            self.request.response.setStatus(resp_comp.resp_code)
            self.request.response['Content-Type'] = "text/xml; charset=utf-8"

            return resp_comp.xml_response

        except TypeError as te:
            fault = Fault(
                faultcode="Client",
                faultstring=te.message,
                faultactor="Client"
            )
            return fault




    def from_soap(self):
        sp_str = self.request.other.get('SOAPXML') or self.request['BODY']
        root, xmlids = etree.XMLID(sp_str)
        if xmlids:
            # resolve_hrefs operates on the root element
            resolve_hrefs(root, xmlids)
        body = None
        header = None
        for e in root.getchildren():
            name = e.tag.split('}')[-1].lower()
            if name == 'body':
                body = e
            elif name == 'header':
                header = e

        payload = None

        if len(body.getchildren()):
            payload = body.getchildren()[0]

        return payload, header

    def get_in_object(self, ctx, in_string, in_string_charset=None):
        in_object = None
        root, xmlids = self.soap_app.parse_xml_string(in_string, in_string_charset)

        try:
            in_object = self.soap_app.deserialize_soap(ctx, self.soap_app.IN_WRAPPER, root, xmlids)
        except Fault, e:
            ctx.in_error = e

        return in_object


    def get_out_object(self, ctx, in_object):
        out_object = self.soap_app.process_request(ctx, in_object)

        if isinstance(out_object, Fault):
            ctx.out_error = out_object
        else:
            assert not isinstance(out_object, Exception)

        return out_object

    def get_out_string(self, ctx, out_object):
        out_xml = self.soap_app.serialize_soap(ctx, self.soap_app.OUT_WRAPPER, out_object)
        out_string = etree.tostring(out_xml, xml_declaration=True, encoding=string_encoding)
        return out_string

    def parse_soap_request(self):
        soap = self.request.other.get('SOAPXML') or self.request['BODY']
        #these are lxml etree elements
        payload, header = self.from_soap()
        ctx = soaplib.core.MethodContext()

        content_type = cgi.parse_header(self.request.get("CONTENT_TYPE"))
        charset = content_type[1].get('charset', None)

        if charset is None:
            charset = 'ascii'

        in_string = collapse_swa(content_type, soap)
        in_object = self.get_in_object(ctx, in_string, charset)
        return_code = HTTP_200

        if ctx.in_error:
            out_object = ctx.in_error
            return_code = HTTP_500
        else:
            assert ctx.service != None
            out_object = self.get_out_object(ctx, in_object)
            if ctx.out_error:
                out_object = ctx.out_error
                return_code = HTTP_500

        out_string = self.get_out_string(ctx, out_object)

        http_resp_headers = {
            'Content-Type': 'text/xml',
            'Content-Length': '0',
            }

        if ctx.descriptor and ctx.descriptor.mtom:
            # when there are more than one return type, the result is
            # encapsulated inside a list. when there's just one, the result
            # is returned unencapsulated. the apply_mtom always expects the
            # objects to be inside an iterable, hence the following test.
            out_type_info = ctx.descriptor.out_message._type_info
            if len(out_type_info) == 1:
                out_object = [out_object]

            http_resp_headers, out_string = apply_mtom(http_resp_headers,
                                                       out_string, ctx.descriptor.out_message._type_info.values(),
                                                       out_object)

        # initiate the response
        http_resp_headers['Content-Length'] = str(len(out_string))

        rc = RespComp(out_string, http_resp_headers, return_code)

        return rc

    def is_wsdl(self):
        """True, if this is a Zope standard request.

        A Zope standard request is a request for which Zope has parsed the
        arguments and provided them in ``form``.
        """
        if not self.request.get('CONTENT_TYPE'):
            # "GET" request
            return True
        ct, _ = parse_header(self.request['CONTENT_TYPE'])
        return ct in ('application/x-www-form-urlencoded', 'multipart/form-data')


    def get_wsdl(self):
        self.request.response.setHeader("Content-Type', 'text/xml", True)
        return self.soap_app.get_wsdl(self.request.getURL())
