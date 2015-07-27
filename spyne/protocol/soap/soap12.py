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

"""
The ``spyne.protoco.soap.soap12`` module contains the implementation of a
subset of the Soap 1.2 standard.

This modules is EXPERIMENTAL.
"""

import logging

from lxml.builder import E

from spyne.protocol.soap.soap11 import Soap11
from spyne.protocol.xml import _append
from spyne.util.six import string_types
from spyne.util.etreeconv import root_dict_to_etree
from spyne.const.xml import NS_SOAP12_ENV, NS_XML, PREFMAP


logger = logging.getLogger(__name__)
logger_invalid = logging.getLogger(__name__ + ".invalid")


class Soap12(Soap11):
    """
    The base implementation of a subset of the Soap 1.2 standard. The
    document is available here: http://www.w3.org/TR/soap12/
    """
    mime_type = 'application/soap+xml; charset=utf-8'

    soap_env = PREFMAP[NS_SOAP12_ENV]
    ns_soap_env = NS_SOAP12_ENV

    def generate_subcode(self, value, subcode=None):
        subcode_node = E("{%s}Subcode" % self.ns_soap_env)
        subcode_node.append(E("{%s}Value" % self.ns_soap_env, value))
        if subcode:
            subcode_node.append(subcode)
        return subcode_node

    def gen_fault_codes(self, faultstring):
        faultstrings = faultstring.split('.')
        value = faultstrings.pop(0)

        if value == 'Client':
            value = '%s:Sender' % self.soap_env
        elif value == 'Server':
            value = '%s:Receiver' % self.soap_env
        else:
            raise TypeError('Wrong fault code, got', type(faultstring))

        return value, faultstrings

    def generate_faultcode(self, element):
        nsmap = element.nsmap
        faultcode = []
        faultcode.append(element.find('soap:Code/soap:Value', namespaces=nsmap).text)
        subcode = element.find('soap:Code/soap:Subcode', namespaces=nsmap)
        while subcode:
            faultcode.append(subcode.find('soap:Value', namespaces=nsmap).text)
            subcode = subcode.find('soap:Subcode', namespaces=nsmap)

        return '.'.join(faultcode)

    def fault_to_parent(self, ctx, cls, inst, parent, ns, **_):
        reason = E("{%s}Reason" % self.ns_soap_env)
        reason.append(E("{%s}Text" % self.ns_soap_env, inst.faultstring,
                        **{'{%s}lang' % NS_XML: inst.lang}))

        subelts = [
            reason,
            E("{%s}Role" % self.ns_soap_env, inst.faultactor),
        ]

        return self._fault_to_parent_impl(ctx, cls, inst, parent, ns, subelts)

    def _fault_to_parent_impl(self, ctx, cls, inst, parent, ns, subelts, **_):
        tag_name = "{%s}Fault" % self.ns_soap_env

        if isinstance(inst.faultcode, string_types):
            value, faultcodes  = self.gen_fault_codes(inst.faultcode)

            code = E("{%s}Code" % self.ns_soap_env)
            code.append(E("{%s}Value" % self.ns_soap_env, value))

            child_subcode = 0
            for value in faultcodes:
                if child_subcode:
                    child_subcode = self.generate_subcode(value, child_subcode)
                else:
                    child_subcode = self.generate_subcode(value)
            code.append(child_subcode)

            _append(subelts, code)

        if isinstance(inst.detail, dict):
            _append(subelts, E('{%s}Detail' % self.ns_soap_env, root_dict_to_etree(inst.detail)))

        elif inst.detail is None:
            pass

        else:
            raise TypeError('Fault detail Must be dict, got', type(inst.detail))

        return self.gen_members_parent(ctx, cls, inst, parent, tag_name,
                                                        subelts, add_type=False)

    def schema_validation_error_to_parent(self, ctx, cls, inst, parent, ns, **_):
        subelts = [
            E("{%s}Reason" % self.soap_env, inst.faultstring),
            E("{%s}Role" % self.soap_env, inst.faultactor),
        ]

        return self._fault_to_parent_impl(ctx, cls, inst, parent, ns, subelts)

    def fault_from_element(self, ctx, cls, element):
        nsmap  = element.nsmap

        code = self.generate_faultcode(element)
        reason = element.find("soap:Reason/soap:Text", namespaces=nsmap).text.strip()
        role = element.find("soap:Role", namespaces=nsmap)
        node = element.find("soap:Node", namespaces=nsmap)
        detail = element.find("soap:Detail", namespaces=nsmap)
        faultactor = ''
        if role:
            faultactor += role.text.strip()
        if node:
            faultactor += node.text.strip()
        return cls(faultcode=code, faultstring=reason,
                   faultactor = faultactor, detail=detail)
