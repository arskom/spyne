
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
nsmap = {
    'xs': 'http://www.w3.org/2001/XMLSchema',
    'xsi': 'http://www.w3.org/1999/XMLSchema-instance',
    'plink': 'http://schemas.xmlsoap.org/ws/2003/05/partner-link/',
    'soap': 'http://schemas.xmlsoap.org/wsdl/soap/',
    'wsdl': 'http://schemas.xmlsoap.org/wsdl/',
    'soap_enc': 'http://schemas.xmlsoap.org/soap/encoding/',
    'soap_env': 'http://schemas.xmlsoap.org/soap/envelope/',
    'wsa': 'http://schemas.xmlsoap.org/ws/2003/03/addressing',
}

# prefix map
prefmap = dict([(a[1],a[0]) for a in nsmap.items() ])

_ns_counter = 0
def get_namespace_prefix(ns):
    global _ns_counter

    if not (ns in prefmap):
        pref = "tns%d" % _ns_counter
        prefmap[ns] = pref
        nsmap[pref] = ns

        _ns_counter += 1
    else:
        pref = prefmap[ns]

    return pref
