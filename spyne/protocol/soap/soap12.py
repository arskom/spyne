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
The ``spyne.protoco.soap.soap1_2`` module contains the implementation of a
subset of the Soap 1.2 standard.
"""

import logging

from lxml import etree
from lxml.builder import E

from spyne.protocol.soap.soap11 import Soap11
from spyne.protocol.xml import _append
from spyne.util.six import string_types
from spyne.util.etreeconv import root_dict_to_etree
from spyne.const.xml_ns import soap_env as _ns_soap_env
from spyne.const.xml_ns import const_prefmap

_pref_soap_env = const_prefmap[_ns_soap_env]

logger = logging.getLogger(__name__)
logger_invalid = logging.getLogger(__name__ + ".invalid")



class Soap12(Soap11):
    """
    The base implementation of a subset of the Soap 1.2 standard. The
    document is available here: http://www.w3.org/TR/soap12/
    """

    def generate_subcode(self, value, subcode=None):
        subcode_node = E("{%s}Subcode" % _pref_soap_env)
        subcode_node.append(E("{%s}Value" % _pref_soap_env, value))
        if subcode:
            subcode_node.append(subcode)
        return subcode_node

    def fault_to_parent(self, ctx, cls, inst, parent, ns, *args, **kwargs):
        tag_name = "{%s}Fault" % _ns_soap_env

        subelts = [
            E("{%s}Reason" % _pref_soap_env, inst.faultstring),
            E("{%s}Role" % _pref_soap_env, inst.faultactor),
        ]

        if isinstance(inst.faultstring, string_types):
            faultstrings = inst.faultstring.split('.')
            value = faultstrings.pop(0)
            if value == 'Client':
                value = 'Sender'
            elif value == 'Server':
                value = 'Receiver'
            else:
                raise TypeError('Wrong fault code, got', type(inst.faultstring))

            code = E("{%s}Code" % _pref_soap_env)
            code.append(E("{%s}Value" % _pref_soap_env, value))

            child_subcode = 0
            for value in inst.faultstring.split('.')[::-1]:
                if child_subcode:
                    child_subcode = self.generate_subcode(value, child_subcode)
                else:
                    child_subcode = self.generate_subcode(value)
            code.append(child_subcode)

            _append(subelts, code)

        if isinstance(inst.detail, string_types + (etree._Element,)):
            _append(subelts, E('{%s}Detail' % _pref_soap_env, inst.detail))

        elif isinstance(inst.detail, dict):
            _append(subelts, E('{%s}Detail' % _pref_soap_env, root_dict_to_etree(inst.detail)))

        elif inst.detail is None:
            pass
        else:
            raise TypeError('Fault detail Must be dict, got', type(inst.detail))

        # add other nonstandard fault subelements with get_members_etree
        return self.gen_members_parent(ctx, cls, inst, parent, tag_name, subelts)

    # TODO
    def fault_from_element(self, ctx, cls, element):
        pass
        # code = element.find('faultcode').text
        # string = element.find('faultstring').text
        # factor = element.find('faultactor')
        # if factor is not None:
        #     factor = factor.text
        # detail = element.find('detail')
        #
        # return cls(faultcode=code, faultstring=string, faultactor=factor,
        #                                                           detail=detail)

    def schema_validation_error_to_parent(self, ctx, cls, inst, parent, ns):
        pass
    #     tag_name = "{%s}Fault" % _ns_soap_env
    #
    #     subelts = [
    #         E("faultcode", '%s:%s' % (_pref_soap_env, inst.faultcode)),
    #         # HACK: Does anyone know a better way of injecting raw xml entities?
    #         E("faultstring", html.fromstring(inst.faultstring).text),
    #         E("faultactor", inst.faultactor),
    #     ]
    #     if inst.detail != None:
    #         _append(subelts, E('detail', inst.detail))
    #
    #     # add other nonstandard fault subelements with get_members_etree
    #     return self.gen_members_parent(ctx, cls, inst, parent, tag_name, subelts)