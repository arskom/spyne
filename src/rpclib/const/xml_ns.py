
#
# rpclib - Copyright (C) Rpclib contributors.
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

xml = 'http://www.w3.org/XML/1998/namespace'
xsd = 'http://www.w3.org/2001/XMLSchema'
xsi = 'http://www.w3.org/2001/XMLSchema-instance'
plink = 'http://schemas.xmlsoap.org/ws/2003/05/partner-link/'
soap = 'http://schemas.xmlsoap.org/wsdl/soap/'
wsdl = 'http://schemas.xmlsoap.org/wsdl/'
soap_enc = 'http://schemas.xmlsoap.org/soap/encoding/'
soap_env = 'http://schemas.xmlsoap.org/soap/envelope/'
soap12_env = 'http://www.w3.org/2003/05/soap-envelope/'
soap12_enc = 'http://www.w3.org/2003/05/soap-encoding/'
wsa = 'http://schemas.xmlsoap.org/ws/2003/03/addressing'
xop = 'http://www.w3.org/2004/08/xop/include'

const_nsmap = {
    'xml': xml,
    'xs': xsd,
    'xsi': xsi,
    'plink': plink,
    'soap': soap,
    'wsdl': wsdl,
    'senc': soap_enc,
    'senv': soap_env,
    's12env': soap12_env,
    's12enc': soap12_enc,
    'wsa': wsa,
    'xop': xop,
}

const_prefmap = dict([(b, a) for a, b in const_nsmap.items()])

schema_location = {
    xsd: 'http://www.w3.org/2001/XMLSchema.xsd',
}

class DEFAULT_NS(object):
    pass
