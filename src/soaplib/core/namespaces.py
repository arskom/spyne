#
# soaplib - Copyright (C) Soaplib contributors.
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

# namespace map

ns_xml = 'http://www.w3.org/XML/1998/namespace'
ns_xsd = 'http://www.w3.org/2001/XMLSchema'
ns_xsi = 'http://www.w3.org/2001/XMLSchema-instance'
ns_plink = 'http://schemas.xmlsoap.org/ws/2003/05/partner-link/'
ns_soap = 'http://schemas.xmlsoap.org/wsdl/soap/'
ns_wsdl = 'http://schemas.xmlsoap.org/wsdl/'
ns_soap_enc = 'http://schemas.xmlsoap.org/soap/encoding/'
ns_soap_env = 'http://schemas.xmlsoap.org/soap/envelope/'
ns_soap12_env = 'http://www.w3.org/2003/05/soap-envelope/'
ns_soap12_enc = 'http://www.w3.org/2003/05/soap-encoding/'
ns_wsa = 'http://schemas.xmlsoap.org/ws/2003/03/addressing'
ns_xop = 'http://www.w3.org/2004/08/xop/include'

const_nsmap = {
    'xml': ns_xml,
    'xs': ns_xsd,
    'xsi': ns_xsi,
    'plink': ns_plink,
    'soap': ns_soap,
    'wsdl': ns_wsdl,
    'senc': ns_soap_enc,
    'senv': ns_soap_env,
    's12env': ns_soap12_env,
    's12enc': ns_soap12_enc,
    'wsa': ns_wsa,
    'xop': ns_xop,
}

const_prefmap = dict([(b,a) for a,b in const_nsmap.items()])
