
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

from rpclib.error import ValidationError

from rpclib.protocol.xml.model._base import base_to_parent_element
from rpclib.protocol.xml.model._base import nillable_element
from rpclib.protocol.xml.model._base import nillable_value

@nillable_value
def enum_to_parent_element(prot, cls, value, tns, parent_elt, name='retval'):
    if name is None:
        name = cls.get_type_name()
    base_to_parent_element(prot, cls, str(value), tns, parent_elt, name)

@nillable_element
def enum_from_element(prot, cls, element):
    if prot.validator is prot.SOFT_VALIDATION and not (
                                        cls.validate_string(cls, element.text)):
        raise ValidationError(element.text)
    return getattr(cls, element.text)
