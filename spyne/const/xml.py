
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
#

"""The ``spyne.const.xml`` module contains various XML-related constants like
namespace prefixes, namespace values and schema uris.
"""

NS_XML = 'http://www.w3.org/XML/1998/namespace'
NS_XSD = 'http://www.w3.org/2001/XMLSchema'
NS_XSI = 'http://www.w3.org/2001/XMLSchema-instance'
NS_WSA = 'http://schemas.xmlsoap.org/ws/2003/03/addressing'
NS_XOP = 'http://www.w3.org/2004/08/xop/include'
NS_XHTML = 'http://www.w3.org/1999/xhtml'
NS_PLINK = 'http://schemas.xmlsoap.org/ws/2003/05/partner-link/'
NS_SOAP11_ENC = 'http://schemas.xmlsoap.org/soap/encoding/'
NS_SOAP11_ENV = 'http://schemas.xmlsoap.org/soap/envelope/'
NS_SOAP12_ENC = 'http://www.w3.org/2003/05/soap-encoding'
NS_SOAP12_ENV = 'http://www.w3.org/2003/05/soap-envelope'

NS_WSDL11 = 'http://schemas.xmlsoap.org/wsdl/'
NS_WSDL11_SOAP = 'http://schemas.xmlsoap.org/wsdl/soap/'

NSMAP = {
    'xml': NS_XML,
    'xs': NS_XSD,
    'xsi': NS_XSI,
    'plink': NS_PLINK,
    'wsdlsoap11': NS_WSDL11_SOAP,
    'wsdl': NS_WSDL11,
    'soap11enc': NS_SOAP11_ENC,
    'soap11env': NS_SOAP11_ENV,
    'soap12env': NS_SOAP12_ENV,
    'soap12enc': NS_SOAP12_ENC,
    'wsa': NS_WSA,
    'xop': NS_XOP,
}

PREFMAP = None
def regen_prefmap():
    global PREFMAP
    PREFMAP = dict([(b, a) for a, b in NSMAP.items()])

regen_prefmap()

schema_location = {
    NS_XSD: 'http://www.w3.org/2001/XMLSchema.xsd',
}

class DEFAULT_NS(object):
    pass


def Tnswrap(ns):
    return lambda s: "{%s}%s" % (ns, s)

XML = Tnswrap(NS_XML)
XSD = Tnswrap(NS_XSD)
XSI = Tnswrap(NS_XSI)
WSA = Tnswrap(NS_WSA)
XOP = Tnswrap(NS_XOP)
XHTML = Tnswrap(NS_XHTML)
PLINK = Tnswrap(NS_PLINK)
SOAP11_ENC = Tnswrap(NS_SOAP11_ENC)
SOAP11_ENV = Tnswrap(NS_SOAP11_ENV)
SOAP12_ENC = Tnswrap(NS_SOAP12_ENC)
SOAP12_ENV = Tnswrap(NS_SOAP12_ENV)
WSDL11 = Tnswrap(NS_WSDL11)
WSDL11_SOAP = Tnswrap(NS_WSDL11_SOAP)
