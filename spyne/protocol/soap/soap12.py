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
from spyne.util.etreeconv import root_dict_to_etree
from spyne.util.six import string_types

logger = logging.getLogger(__name__)
logger_invalid = logging.getLogger(__name__ + ".invalid")



class Soap12(Soap11):
    """
    The base implementation of a subset of the Soap 1.2 standard. The
    document is available here: http://www.w3.org/TR/soap12/
    """
    def fault_to_parent(self, ctx, cls, inst, parent, ns, *args, **kwargs):
        pass
    #     tag_name = "{%s}Fault" % _ns_soap_env
    #
    #     subelts = [
    #         E("faultcode", '%s:%s' % (_pref_soap_env, inst.faultcode)),
    #         E("faultstring", inst.faultstring),
    #         E("faultactor", inst.faultactor),
    #     ]
    #
    #     # Accepting raw lxml objects as detail is deprecated. It's also not
    #     # documented. It's kept for backwards-compatibility purposes.
    #     if isinstance(inst.detail, string_types + (etree._Element,)):
    #         _append(subelts, E('detail', inst.detail))
    #     elif isinstance(inst.detail, dict):
    #         _append(subelts, E('detail', root_dict_to_etree(inst.detail)))
    #     elif inst.detail is None:
    #         pass
    #     else:
    #         raise TypeError('Fault detail Must be dict, got', type(inst.detail))
    #
    #     # add other nonstandard fault subelements with get_members_etree
    #     return self.gen_members_parent(ctx, cls, inst, parent, tag_name, subelts)
    #
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