
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

from spyne._base import FakeContext

from spyne.protocol.dictdoc import HierDictDocument
from spyne.protocol.dictdoc import SimpleDictDocument

try:
    from spyne.protocol.json import JsonDocument
except ImportError as e:
    def JsonDocument(*args, **kwargs):
        raise e

try:
    from spyne.protocol.yaml import YamlDocument
except ImportError as e:
    def YamlDocument(*args, **kwargs):
        raise e


from spyne.model.primitive import Double
from spyne.model.primitive import Boolean
from spyne.model.primitive import Decimal
from spyne.model.primitive import Integer


class _UtilProtocol(HierDictDocument):
    def __init__(self, app=None, validator=None, mime_type=None,
                                        ignore_uncap=False,
                                        # DictDocument specific
                                        ignore_wrappers=True,
                                        complex_as=dict,
                                        ordered=False):

        super(_UtilProtocol, self).__init__(app, validator, mime_type, ignore_uncap,
                                           ignore_wrappers, complex_as, ordered)

        self._from_string_handlers[Double] = lambda cls, val: val
        self._from_string_handlers[Boolean] = lambda cls, val: val
        self._from_string_handlers[Decimal] = lambda cls, val: val
        self._from_string_handlers[Integer] = lambda cls, val: val

        self._to_string_handlers[Double] = lambda cls, val: val
        self._to_string_handlers[Boolean] = lambda cls, val: val
        self._to_string_handlers[Decimal] = lambda cls, val: val
        self._to_string_handlers[Integer] = lambda cls, val: val


def get_dict_as_object(d, cls, ignore_wrappers=True, complex_as=list,
                                                        protocol=_UtilProtocol):
    return protocol(ignore_wrappers=ignore_wrappers,
                                   complex_as=complex_as)._doc_to_object(cls, d)


def get_object_as_dict(o, cls, ignore_wrappers=True, complex_as=dict,
                                                        protocol=_UtilProtocol):
    retval = protocol(ignore_wrappers=ignore_wrappers,
                                   complex_as=complex_as)._object_to_doc(cls, o)
    if not ignore_wrappers:
        return {cls.get_type_name(): retval}
    return retval


def get_object_as_simple_dict(o, cls, hier_delim='_'):
    return SimpleDictDocument(hier_delim=hier_delim) \
                                                  .object_to_simple_dict(cls, o)


def get_object_as_json(o, cls, ignore_wrappers=True, complex_as=list,
                                            encoding='utf8', polymorphic=False):
    prot = JsonDocument(ignore_wrappers=ignore_wrappers, complex_as=complex_as,
                                                        polymorphic=polymorphic)
    ctx = FakeContext(out_document=[prot._object_to_doc(cls,o)])
    prot.create_out_string(ctx, encoding)
    return ''.join(ctx.out_string)


def get_object_as_yaml(o, cls, ignore_wrappers=False, complex_as=dict,
                                            encoding='utf8', polymorphic=False):
    prot = YamlDocument(ignore_wrappers=ignore_wrappers, complex_as=complex_as,
                                                        polymorphic=polymorphic)
    ctx = FakeContext(out_document=[prot._object_to_doc(cls,o)])
    prot.create_out_string(ctx, encoding)
    return ''.join(ctx.out_string)


def json_loads(s, cls, protocol=JsonDocument, encoding=None, **kwargs):
    prot = protocol(**kwargs)
    ctx = FakeContext(in_string=[s])
    prot.create_in_document(ctx)
    return prot._doc_to_object(cls, ctx.in_document)


def yaml_loads(s, cls, protocol=YamlDocument, ignore_wrappers=False, **kwargs):
    prot = protocol(ignore_wrappers=ignore_wrappers, **kwargs)
    ctx = FakeContext(in_string=[s])
    prot.create_in_document(ctx)
    return prot._doc_to_object(cls, ctx.in_document)
