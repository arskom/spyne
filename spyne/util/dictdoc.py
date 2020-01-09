
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

from spyne.context import FakeContext

from spyne.protocol.dictdoc import HierDictDocument
from spyne.protocol.dictdoc import SimpleDictDocument

try:
    from spyne.protocol.json import JsonDocument
except ImportError as _import_error:
    _local_import_error = _import_error
    def JsonDocument(*args, **kwargs):
        raise _local_import_error


try:
    from spyne.protocol.yaml import YamlDocument
except ImportError as _import_error:
    _local_import_error = _import_error
    def YamlDocument(*args, **kwargs):
        raise _local_import_error


try:
    from spyne.protocol.msgpack import MessagePackDocument
except ImportError as _import_error:
    _local_import_error = _import_error
    def MessagePackDocument(*args, **kwargs):
        raise _local_import_error


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

        self._from_unicode_handlers[Double] = lambda cls, val: val
        self._from_unicode_handlers[Boolean] = lambda cls, val: val
        self._from_unicode_handlers[Decimal] = lambda cls, val: val
        self._from_unicode_handlers[Integer] = lambda cls, val: val

        self._to_unicode_handlers[Double] = lambda cls, val: val
        self._to_unicode_handlers[Boolean] = lambda cls, val: val
        self._to_unicode_handlers[Decimal] = lambda cls, val: val
        self._to_unicode_handlers[Integer] = lambda cls, val: val


def get_doc_as_object(d, cls, ignore_wrappers=True, complex_as=list,
                                    protocol=_UtilProtocol, protocol_inst=None):
    if protocol_inst is None:
        protocol_inst = protocol(ignore_wrappers=ignore_wrappers,
                                                          complex_as=complex_as)

    return protocol_inst._doc_to_object(None, cls, d)


get_dict_as_object = get_doc_as_object
"""DEPRECATED: Use ``get_doc_as_object`` instead"""


def get_object_as_doc(o, cls=None, ignore_wrappers=True, complex_as=dict,
                                    protocol=_UtilProtocol, protocol_inst=None):
    if cls is None:
        cls = o.__class__

    if protocol_inst is None:
        protocol_inst = protocol(ignore_wrappers=ignore_wrappers,
                                                          complex_as=complex_as)

    retval = protocol_inst._object_to_doc(cls, o)

    if not ignore_wrappers:
        return {cls.get_type_name(): retval}

    return retval


get_object_as_dict = get_object_as_doc
"""DEPRECATED: Use ``get_object_as_doc`` instead."""

def get_object_as_simple_dict(o, cls=None, hier_delim='.', prefix=None):
    if cls is None:
        cls = o.__class__

    return SimpleDictDocument(hier_delim=hier_delim) \
                                   .object_to_simple_dict(cls, o, prefix=prefix)


def get_object_as_json(o, cls=None, ignore_wrappers=True, complex_as=list,
                     encoding='utf8', polymorphic=False, indent=None, **kwargs):
    if cls is None:
        cls = o.__class__

    prot = JsonDocument(ignore_wrappers=ignore_wrappers, complex_as=complex_as,
                               polymorphic=polymorphic, indent=indent, **kwargs)
    ctx = FakeContext(out_document=[prot._object_to_doc(cls, o)])
    prot.create_out_string(ctx, encoding)
    return b''.join(ctx.out_string)


def get_object_as_json_doc(o, cls=None, ignore_wrappers=True, complex_as=list,
                                      polymorphic=False, indent=None, **kwargs):
    if cls is None:
        cls = o.__class__

    prot = JsonDocument(ignore_wrappers=ignore_wrappers, complex_as=complex_as,
                               polymorphic=polymorphic, indent=indent, **kwargs)

    return prot._object_to_doc(cls, o)


def get_object_as_yaml(o, cls=None, ignore_wrappers=False, complex_as=dict,
                                            encoding='utf8', polymorphic=False):
    if cls is None:
        cls = o.__class__

    prot = YamlDocument(ignore_wrappers=ignore_wrappers, complex_as=complex_as,
                                                        polymorphic=polymorphic)
    ctx = FakeContext(out_document=[prot._object_to_doc(cls,o)])
    prot.create_out_string(ctx, encoding)
    return b''.join(ctx.out_string)


def get_object_as_yaml_doc(o, cls=None, ignore_wrappers=False, complex_as=dict,
                                                             polymorphic=False):
    if cls is None:
        cls = o.__class__

    prot = YamlDocument(ignore_wrappers=ignore_wrappers, complex_as=complex_as,
                                                        polymorphic=polymorphic)
    return prot._object_to_doc(cls, o)


def get_object_as_msgpack(o, cls=None, ignore_wrappers=False, complex_as=dict,
                                                             polymorphic=False):
    if cls is None:
        cls = o.__class__

    prot = MessagePackDocument(ignore_wrappers=ignore_wrappers,
                                 complex_as=complex_as, polymorphic=polymorphic)
    ctx = FakeContext(out_document=[prot._object_to_doc(cls,o)])
    prot.create_out_string(ctx)
    return b''.join(ctx.out_string)


def get_object_as_msgpack_doc(o, cls=None, ignore_wrappers=False,
                                            complex_as=dict, polymorphic=False):
    if cls is None:
        cls = o.__class__

    prot = MessagePackDocument(ignore_wrappers=ignore_wrappers,
                                 complex_as=complex_as, polymorphic=polymorphic)

    return prot._object_to_doc(cls, o)


def json_loads(s, cls, protocol=JsonDocument, **kwargs):
    if s is None:
        return None
    if s == '':
        return None
    prot = protocol(**kwargs)
    ctx = FakeContext(in_string=[s])
    prot.create_in_document(ctx)
    return prot._doc_to_object(None, cls, ctx.in_document,
                                                       validator=prot.validator)


get_json_as_object = json_loads


def yaml_loads(s, cls, protocol=YamlDocument, ignore_wrappers=False, **kwargs):
    if s is None:
        return None
    if s == '' or s == b'':
        return None
    prot = protocol(ignore_wrappers=ignore_wrappers, **kwargs)
    ctx = FakeContext(in_string=[s])
    prot.create_in_document(ctx)
    retval = prot._doc_to_object(None, cls, ctx.in_document,
                                                       validator=prot.validator)
    return retval


get_yaml_as_object = yaml_loads
