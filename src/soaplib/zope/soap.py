from Products.Five.browser import BrowserView

from soaplib.core.model.primitive import String, Integer
from soaplib.core.service import DefinitionBase, rpc

from soaplib.core.model.clazz import ClassModel
from soaplib.zope.metaconfigure import SoaplibHandler, consturct_soaplib_application


class Person(ClassModel):
    first_name = String
    last_name = String
    age = Integer


class SoapService(DefinitionBase):

    @rpc(String, _returns=String)
    def echo_string(self, string):
        return string

    @rpc(Person, _returns=Person)
    def echo_person(self, person):
        return person




class WSDLView(BrowserView):
    """Display a wsdl
    """

    def __init__(self, context, request):
        BrowserView.__init__(self, context, request)
        soap_app = consturct_soaplib_application([SoapService], "T2")
        self.soaplib_handler = SoaplibHandler(self.request, soap_app)


    def __call__(self, *args, **kwargs):
        return self.soaplib_handler.handle_request()