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

from soaplib.service import SoapServiceBase, getTNS
from soaplib.soap import make_soap_envelope, make_soap_fault, from_soap
from soaplib.serializers.primitive import string_encoding

import cElementTree as ElementTree


# public sumbols
__all__ = [
    'SoapFolder', # to mix into your Zope Folders to make them into SOAP Service Points
    ]

class SoapFolder(SoapServiceBase):
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

    def _get_soap_methods(self):
        """Returns a list of method descriptors for this object"""
        soap_methods = []
        for funcName in dir(self):
            if funcName != 'permissionMappingPossibleValues' and not funcName.startswith('_v_'):
                func = getattr(self, funcName)
                if callable(func) and hasattr(func, '_is_soap_method'):
                    descriptor = func(_soap_descriptor=True, klazz=self.__class__)
                    soap_methods.append(descriptor)
        return soap_methods

    def methods(self):
        """Returns a list of method descriptors for this object"""
        if self._v_soap_methods is None:
            self._v_soap_methods = self._get_soap_methods()
        return self._v_soap_methods

    def service_description(self, REQUEST, RESPONSE):
        """ """

        if getattr(self, '__tns__', None) is None:
            self.__tns__ = getTNS(self.__class__)

        if self._v_soap_methods is None:
            self._v_soap_methods = self._get_soap_methods()

        if self._v_cached_wsdl is None:
            self._v_cached_wsdl = self.wsdl(self.absolute_url())
            self.__wsdl__ = None

        RESPONSE.setHeader('Content-Type', 'text/xml')
        return self._v_cached_wsdl

    def index_html(self, REQUEST, RESPONSE):
        """Handle an incoming SOAP request or a non-SOAP WSDL query."""

        if REQUEST.get('SOAPXML', None) == None: # Not a SOAP Request, return WSDL
            return self.service_description(REQUEST, RESPONSE)

        try:
            # Deserialize the Body of the SOAP Request
            payload, header = from_soap(REQUEST.SOAPXML)
            methodname = payload.tag.split('}')[-1]

            # Look-up the method within our class and obtain its SOAP descriptor
            # specifying its arguments signature and return type.
            try:
                func = getattr(self, methodname)
                descriptor = func(_soap_descriptor=True)
            except AttributeError:
                faultstring = 'No Such SOAP Method: %s' % `methodname`
                faultcode = 'Server'

                fault = make_soap_fault(faultstring, faultcode, detail=None)
                resp = ElementTree.tostring(fault, encoding=string_encoding)

                RESPONSE.setStatus('NotImplemented', reason=faultstring)
                RESPONSE.setHeader('Content-Type', 'text/xml')
                return resp
            except TypeError, e:
                if "unexpected keyword argument '_soap_descriptor'" not in str(e):
                    raise

                faultstring = 'Method %s Exists But Not SOAP-Callable' % `methodname`
                faultcode = 'Server'

                fault = make_soap_fault(faultstring, faultcode, detail=None)
                resp = ElementTree.tostring(fault, encoding=string_encoding)

                RESPONSE.setStatus('BadRequest', reason=faultstring)
                RESPONSE.setHeader('Content-Type', 'text/xml')
                return resp

            # Run the supplied arguments through the arguments signature and catch
            # any argument type or count mismatches.
            try:
                params = descriptor.inMessage.from_xml(payload)
            except Exception, e:
                faultstring = "%s: Argument Parse Error" % str(e)
                faultcode = '%sFault' % methodname

                fault = make_soap_fault(faultstring, faultcode, detail=None)
                resp = ElementTree.tostring(fault, encoding=string_encoding)

                RESPONSE.setStatus('BadRequest', reason=faultstring)
                RESPONSE.setHeader('Content-Type', 'text/xml')
                return resp

            # Finally call the actual SOAP Method
            retval = func(*params)

            # Transform the return value into an element; only expect a single element
            results = None
            if not (descriptor.isAsync or descriptor.isCallback):
                results = descriptor.outMessage.to_xml(*[retval])

            envelope = make_soap_envelope(results, tns=self.__tns__)
            resp = ElementTree.tostring(envelope, encoding=string_encoding)

            RESPONSE.setHeader('Content-Type', 'text/xml')
            return resp

        except Exception, e:
            faultstring = str(e)
            if methodname:
                faultcode = '%sFault' % methodname
            else:
                faultcode = 'Server'

            fault = make_soap_fault(faultstring, faultcode, detail=None)
            resp = ElementTree.tostring(fault, encoding=string_encoding)

            RESPONSE.setStatus('InternalServerError', reason=faultstring)
            RESPONSE.setHeader('Content-Type', 'text/xml')
            return resp

