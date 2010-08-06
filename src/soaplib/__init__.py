
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

ns_xsd = 'http://www.w3.org/2001/XMLSchema'
ns_xsi = 'http://www.w3.org/2001/XMLSchema-instance'
ns_plink = 'http://schemas.xmlsoap.org/ws/2003/05/partner-link/'
ns_soap = 'http://schemas.xmlsoap.org/wsdl/soap/'
ns_wsdl = 'http://schemas.xmlsoap.org/wsdl/'
ns_soap_enc = 'http://schemas.xmlsoap.org/soap/encoding/'
ns_soap_env = 'http://schemas.xmlsoap.org/soap/envelope/'
ns_soap_env_w3c = 'http://www.w3.org/2003/05/soap-envelope/'
ns_wsa = 'http://schemas.xmlsoap.org/ws/2003/03/addressing'
ns_xop = 'http://www.w3.org/2004/08/xop/include'

nsmap = {
    'xs': ns_xsd,
    'xsi': ns_xsi,
    'plink': ns_plink,
    'soap': ns_soap,
    'wsdl': ns_wsdl,
    'senc': ns_soap_enc,
    'senv': ns_soap_env,
    'senvw': ns_soap_env_w3c,
    'wsa': ns_wsa,
    'xop': ns_xop,
}

# prefix map
prefmap = dict([(b,a) for a,b in nsmap.items()])

const_prefmap = dict(prefmap)
const_nsmap = dict(nsmap)

_ns_counter = 0
def get_namespace_prefix(ns):
    global _ns_counter

    assert ns != "__main__"
    assert ns != "soaplib.serializers.base"

    assert (isinstance(ns, str) or isinstance(ns, unicode)), ns

    if not (ns in prefmap):
        pref = "s%d" % _ns_counter
        while pref in nsmap:
            _ns_counter += 1
            pref = "s%d" % _ns_counter

        prefmap[ns] = pref
        nsmap[pref] = ns

        _ns_counter += 1

    else:
        pref = prefmap[ns]

    return pref
