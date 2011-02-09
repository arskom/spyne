"""Mix-In Class to Export Decorated Methods using SOAP

   This file is not a Zope2 Product nor a Zope3 component.  It is a simple
   Python module that adds two elements: a hook into the Zope publisher to
   intercept SOAP requests, and a mix-in class to your Zope2 folder classes
   that make them SOAP-aware, with queryable WSDL descriptions of any methods
   decorated with @soapmethod.

   A tiny bit of code needs to be invoked from within ZPublisher during the
   parsing of an HTTP request that is a SOAP request.  To make this happen,
   change the code in the file lib/python/ZPublisher/HTTPRequest.py, within
   the processInputs() method of the HTTPRequest class, from this:

    fs=FieldStorage(fp=fp,environ=environ,keep_blank_values=1)
    if not hasattr(fs,'list') or fs.list is None:
        # Hm, maybe it's an XML-RPC
        if (fs.headers.has_key('content-type') and

   to this:

    fs=FieldStorage(fp=fp,environ=environ,keep_blank_values=1)
    if not hasattr(fs,'list') or fs.list is None:
        if environ.has_key('HTTP_SOAPACTION'):        #ADDED
            other['SOAPXML'] = fs.value               #ADDED
        # Hm, maybe it's an XML-RPC
        elif (fs.headers.has_key('content-type') and  #CHANGED
"""
import cgi

from xml.etree.ElementTree import ElementTree
from lxml import etree
from soaplib.core._base import MethodContext
from soaplib.core.mime import collapse_swa
from soaplib.core.model.exception import Fault

from soaplib.core.service import DefinitionBase,soap
from soaplib.core.model.primitive import string_encoding
from soaplib.core import Application
from soaplib.core.server._base import Base as BaseServer

from zope.interface import implements
from zope.interface.common.interfaces import IException
from zope.app.testing import ztapi

# public sumbols
__all__ = [
    'SoapFolder',  # to mix into your Zope Folders to make them into SOAP Service Points
    'AccessDeniedSOAP',  # exception object to signal a failed SOAP call
    ]


class SoapFolder(DefinitionBase):
    """Mix-In Class to Make a Folder into a SOAP Service Point

    Import this class into your Zope2 folder classes to make them SOAP-aware.
    Any methods in your folder class decorated with @soapmethod() will become
    callable over SOAP and the signature and docstring of that method will be
    reported as WSDL by a call to the index_html() method of that folder.

    Your class should also define a class attribute indicating the 'toplevel
    namespace' of your SOAP Service Point.  This name is arbitrary as far as
    this code goes, but appears in the SOAP response and the WSDL description
    generated.  This attribute looks like:   __tns__ = "PatientServices"
    """

    _v_soap_methods = None
    _v_cached_wsdl = None
    __wsdl__ = None


    def __init__(self, tns, environ=None):
        super(DefinitionBase, self).__init__(environ)
        self.soap_app = Application(self, tns, False)
        self.soap_handler = BaseServer(self.soap_app)


    def methods(self):
        """Returns a list of method descriptors for this object"""
        if self._v_soap_methods is None:
            self._v_soap_methods = self.build_public_methods()
        return self._v_soap_methods


    def service_description(self, REQUEST, RESPONSE):
        """ """

        if getattr(self, '__tns__', None) is None:
            self.__tns__ = self.get_tns(self.__class__)

        if self._v_soap_methods is None:
            self._v_soap_methods = self.build_public_methods()

        if self._v_cached_wsdl is None:
            self._v_cached_wsdl = self.soap_app.get_wsdl(self.absolute_url())
            self.__wsdl__ = None

        RESPONSE.setHeader('Content-Type', 'text/xml')
        return self._v_cached_wsdl

    def index_html(self, REQUEST, RESPONSE):
        """Handle an incoming SOAP request or a non-SOAP WSDL query."""

        if REQUEST.get('SOAPXML', None) == None:  # Not a SOAP Request, return WSDL
            return self.service_description(REQUEST, RESPONSE)

        try:
            # Deserialize the Body of the SOAP Request
            from soaplib.core._base import _from_soap
            header, payload = _from_soap(REQUEST.SOAPXML)

            # TODO: At this point I need dispatch method calls to the soaplib.Application
            # somehow....... :)
            ctx = MethodContext()

            content_type  = cgi.parse_header(REQUEST.get("Content-Type"))
            charset = content_type[1].get('charset',None)
            length = REQUEST.get("Content-Length")
            http_payload = REQUEST.read(int(length))

            if not charset:
                charset = "ascii"

            in_string = collapse_swa(content_type, http_payload)
            in_obj = self.soap_handler.get_in_object(ctx, in_string, charset)
            out_obj = self.soap_handler.get_out_object(ctx, in_obj)
            out_string = self.soap_handler.get_out_string(ctx, out_obj)
            
            return out_string

        except Exception, e:

            fault = Fault(faultstring=str(e))
            resp = etree.tostring(fault, encoding=string_encoding)

            RESPONSE.setStatus('InternalServerError', reason=faultstring)
            RESPONSE.setHeader('Content-Type', 'text/xml')
            return resp


class ISOAPException(IException):
    pass


class SOAPException(Exception):
    """Base exception class for all derived exceptions for SOAP"""

    implements(ISOAPException)

    def __init__(self, request):
        self.request = request
        self.request['faultexc'] = self

    def __str__(self):
        return self.__class__.__name__


class AccessDeniedSOAP(SOAPException):
    """An exception to raise in a SOAP method if access is being denied."""


class SOAPExceptionView:
    """Adapts an (ISOAPException, IRequest) to a View

       This view provides the XML representation of a SOAP fault that is
       returned to a caller.  To use it, register this view with Zope at some
       initialization point:

           from zope.app.testing import ztapi
           from dummy import ISOAPException, SOAPExceptionView
           ztapi.browserView(ISOAPException, u'index.html', SOAPExceptionView)

       and then within your SOAP logic raise a SOAP exception where needed:

           from dummy import SOAPException
           raise SOAPException(request)
    """

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self):
        faultstring = self.request['faultexc'].__class__.__name__
        self.request.response.setStatus('InternalServerError', reason=faultstring)

        faultcode = 'Server'
        fault = make_soap_fault(faultstring, faultcode, detail=None)

        self.request.response.setHeader('Content-Type', 'text/xml')
        return ElementTree.tostring(fault, encoding=string_encoding)

# The following registers 'SOAPExceptionView' as an adapter that knows how to
# display (generate and return the XML source for a SOAP fault) for anything
# that implements the 'ISOAPException' interface.

ztapi.browserView(ISOAPException, u'index.html', SOAPExceptionView)
