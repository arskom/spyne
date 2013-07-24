
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

import logging
logger = logging.getLogger(__name__)

import os

from itertools import chain
from pprint import pprint
from pprint import pformat

from copy import copy

from os.path import dirname
from os.path import abspath
from os.path import join

from lxml import etree

from spyne.const import xml_ns
from spyne.util.odict import odict

from spyne.model import Null
from spyne.model import SimpleModel
from spyne.model.complex import XmlModifier
from spyne.model.complex import XmlData
from spyne.model.complex import XmlAttribute
from spyne.model.complex import Array
from spyne.model.complex import ComplexModelBase
from spyne.model.complex import ComplexModelMeta

from spyne.protocol.xml import XmlDocument
from spyne.interface.xml_schema.defn import TYPE_MAP
from spyne.interface.xml_schema.defn import SchemaBase
from spyne.interface.xml_schema.defn import XmlSchema10

from spyne.util.color import R, G, B, M, Y

PARSER = etree.XMLParser(remove_comments=True)

_prot = XmlDocument()


class _Schema(object):
    def __init__(self):
        self.types = {}
        self.elements = {}
        self.imports = set()


def Town_repr(with_ns=False):
    if with_ns == False:
        def get_class_name(c):
            return c.get_type_name()
    elif with_ns == True:
        def get_class_name(c):
            return "{%s}%s" % (c.get_namespace(), c.get_type_name())
    else:
        def get_class_name(c):
            return with_ns(c.get_namespace(), c.get_type_name())

    def own_repr(self, i0=0, I='  '):
        if not hasattr(self.__class__, '_type_info'):
            return repr(self)

        i1 = i0 + 1
        i2 = i1 + 1

        retval = []
        retval.append(get_class_name(self.__class__))
        retval.append('(\n')
        for k,v in self._type_info.items():
            value = getattr(self, k, None)
            if (issubclass(v, Array) or v.Attributes.max_occurs > 1) and \
                                                            value is not None:
                retval.append("%s%s=[\n" %(I*i1, k))
                for subval in value:
                    retval.append("%s%s,\n" % (I*i2, own_repr(subval,i2)))
                retval.append('%s],\n' % (I*i1))

            else:
                retval.append("%s%s=%s,\n" % (I*i1, k,
                                        own_repr(getattr(self, k, None),i1)))
        retval.append('%s)' % (I*i0))
        return ''.join(retval)

    return own_repr

SchemaBase.__repr__ = Town_repr()

class ParsingCtx(object):
    def __init__(self, files, base_dir=None, own_repr=Town_repr(with_ns=False)):
        self.retval = {}
        self.indent = 0
        self.files = files
        self.base_dir = base_dir
        self.own_repr = own_repr
        if self.base_dir is None:
            self.base_dir = os.getcwd()
        self.parent = None
        self.children = None

        self.tns = None
        self.pending_elements = None
        self.pending_types = None

    def clone(self, indent=0, base_dir=None):
        retval = copy(self)

        if retval.parent is None:
            retval.parent = self
            if self.children is None:
                self.children = [retval]
            else:
                self.children.append(retval)

        else:
            retval.parent.children.append(retval)

        retval.indent = self.indent + indent
        if base_dir is not None:
            retval.base_dir = base_dir

        return retval

    def debug0(self, s, *args, **kwargs):
        logger.debug("%s%s" % ("  " *  self.indent, s), *args, **kwargs) 

    def debug1(self, s, *args, **kwargs):
        logger.debug("%s%s" % ("  " * (self.indent + 1), s), *args, **kwargs)

    def debug2(self, s, *args, **kwargs):
        logger.debug("%s%s" % ("  " * (self.indent + 2), s), *args, **kwargs)


def parse_schema_file(ctx, file_name):
    elt = etree.fromstring(open(file_name).read(), parser=PARSER)
    return parse_schema(ctx, elt)


def process_includes(ctx, include):
    file_name = include.schema_location
    if file_name is None:
        return

    ctx.debug1("including %s %s", ctx.base_dir, file_name)

    file_name = abspath(join(ctx.base_dir, file_name))
    data = open(file_name).read()
    elt = etree.fromstring(data, parser=PARSER)
    ctx.nsmap.update(elt.nsmap)
    ctx.prefmap = dict([(v,k) for k,v in ctx.nsmap.items()])

    sub_schema = _prot.from_element(XmlSchema10, elt)
    if sub_schema.includes:
        for inc in sub_schema.includes:
            base_dir = dirname(file_name)
            child_ctx = ctx.clone(base_dir=base_dir)
            process_includes(ctx, inc)
            ctx.nsmap.update(child_ctx.nsmap)
            ctx.prefmap = dict([(v,k) for k,v in ctx.nsmap.items()])

    for attr in ('imports', 'simple_types', 'complex_types', 'elements'):
        sub = getattr(sub_schema, attr)
        if sub is None:
            sub = []

        own = getattr(ctx.schema, attr)
        if own is None:
            own = []

        own.extend(sub)

        setattr(ctx.schema, attr, own)


def process_simple_type(ctx, s, name=None):
    """Returns the simple Spyne type. Doesn't do any 'pending' processing."""

    if name is None:
        name = s.name

    if s.restriction is None:
        ctx.debug1("skipping simple type: %s", name)
        return
    if s.restriction.base is None:
        ctx.debug1("skipping simple type: %s", name)
        return

    base = get_type(ctx, s.restriction.base)
    if base is None:
        raise ValueError(s)

    kwargs = {}
    restriction = s.restriction
    if restriction.enumeration:
        kwargs['values'] = [e.value for e in restriction.enumeration]

    if restriction.max_length:
        if restriction.max_length.value:
            kwargs['max_len'] = int(restriction.max_length.value)

    if restriction.min_length:
        if restriction.min_length.value:
            kwargs['min_len'] = int(restriction.min_length.value)

    if restriction.pattern:
        if restriction.pattern.value:
            kwargs['pattern'] = restriction.pattern.value

    ctx.debug1("adding   simple type: %s", name)
    retval = base.customize(**kwargs)
    if retval.__orig__ is None:
        retval.__orig__ = base

    if retval.__extends__ is None:
        retval.__extends__ = base
        retval.__type_name__ = name
        retval.__namespace__ = ctx.tns

    return retval


def process_schema_element(ctx, e):
    if e.name is None:
        return

    ctx.debug1("adding element: %s", e.name)
    t = get_type(ctx, e.type)

    key = e.name
    if t:
        if key in ctx.pending_elements:
            del ctx.pending_elements[key]

        ctx.retval[ctx.tns].elements[e.name] = e

    else:
        ctx.pending_elements[key] = e


def process_attribute(ctx, a):
    if a.ref is not None:
        t = get_type(ctx, a.ref)
        return t.type.get_type_name(), t

    if a.type is not None:
        t = get_type(ctx, a.type)

    elif a.simple_type is not None:
        t = process_simple_type(ctx, a.simple_type, a.name)

    else:
        raise Exception("dunno attr")

    if t is None:
        raise ValueError(a, 'not found')

    kwargs = {}
    if a.default is not None:
        kwargs['default'] = a.default

    if len(kwargs) > 0:
        t = t.customize(**kwargs)
        ctx.debug2("t = t.customize(**%r)" % kwargs)
    return (a.name, XmlAttribute(t))


def process_complex_type(ctx, c):
    def process_type(tn, name, wrapper=lambda x: x, element=None, attribute=None):
        t = get_type(ctx, tn)
        key = (c.name, name)
        if t is None:
            ctx.pending_types[key] = c
            ctx.debug2("not found: %r(%s)", key, tn)
            return

        if key in ctx.pending_types:
            del ctx.pending_types[key]

        assert name is not None, (key, e)

        kwargs = {}
        if element is not None:
            if e.min_occurs != "0": # spyne default
                kwargs['min_occurs'] = int(e.min_occurs)

            if e.max_occurs == "unbounded":
                kwargs['max_occurs'] = e.max_occurs
            elif e.max_occurs != "1":
                kwargs['max_occurs'] = int(e.max_occurs)

            if e.nillable != True: # spyne default
                kwargs['nillable'] = e.nillable

            if e.default is not None:
                kwargs['default'] = e.default

            if len(kwargs) > 0:
                t = t.customize(**kwargs)

        if attribute is not None:
            if attribute.default is not None:
                kwargs['default'] = a.default

            if len(kwargs) > 0:
                t = t.customize(**kwargs)

        ti.append( (name, wrapper(t)) )
        ctx.debug2("    found: %r(%s), c: %r", key, tn, kwargs)

    def process_element(e):
        if e.ref is not None:
            tn = e.ref
            name = e.ref.split(":", 1)[-1]

        elif e.name is not None:
            tn = e.type
            name = e.name

        else:
            raise Exception("dunno")

        process_type(tn, name, element=e)

    ti = []
    if c.name in ctx.retval[ctx.tns].types:
        ctx.debug1("modifying existing %r", c.name)
    else:
        ctx.debug1("adding complex type: %s", c.name)

    if c.sequence is not None:
        if c.sequence.elements is not None:
            for e in c.sequence.elements:
                process_element(e)

        if c.sequence.choices is not None:
            for ch in c.sequence.choices:
                if ch.elements is not None:
                    for e in ch.elements:
                        process_element(e)

    if c.choice is not None:
        if c.choice.elements is not None:
            for e in c.choice.elements:
                process_element(e)

    if c.attributes is not None:
        for a in c.attributes:
            if a.name is None:
                continue
            if a.type is None:
                continue

            process_type(a.type, a.name, XmlAttribute, attribute=a)

    if c.simple_content is not None:
        ext = c.simple_content.extension
        if ext is not None: 
            if ext.base is not None:
                # FIXME: find a way to generate _data
                process_type(ext.base, "_data", XmlData)

            if ext.attributes is not None:
                for a in ext.attributes:
                    ti.append(process_attribute(ctx, a))

        restr = c.simple_content.restriction
        if restr is not None:
            if restr.base is not None:
                # FIXME: find a way to generate _data
                process_type(restr.base, "_data", XmlData)

            if restr.attributes is not None:
                for a in restr.attributes:
                    ti.append(process_attribute(ctx, a))

    if c.name in ctx.retval[ctx.tns].types:
        ctx.retval[ctx.tns].types[c.name]._type_info.update(ti)

    else:
        cls_dict = {
            '__type_name__': c.name,
            '__namespace__': ctx.tns,
            '_type_info': ti,
        }
        if ctx.own_repr is not None:
            cls_dict['__repr__'] = ctx.own_repr

        ctx.retval[ctx.tns].types[c.name] = ComplexModelMeta(str(c.name),
                                                  (ComplexModelBase,), cls_dict)

def get_type(ctx, tn):
    if tn is None:
        return Null
    if tn.startswith("{"):
        ns, qn = tn[1:].split('}',1)
    elif ":" in tn:
        ns, qn = tn.split(":",1)
        ns = ctx.nsmap[ns]
    else:
        if None in ctx.nsmap:
            ns, qn = ctx.nsmap[None], tn
        else:
            ns, qn = ctx.tns, tn

    ti = ctx.retval.get(ns)
    if ti is not None:
        t = ti.types.get(qn)
        if t:
            return t

        e = ti.elements.get(qn)
        if e:
            if ":" in e.type:
                return get_type(ctx, e.type)
            else:
                retval = get_type(ctx, "{%s}%s" % (ns, e.type))
                if retval is None and None in ctx.nsmap:
                    retval = get_type(ctx, "{%s}%s" % (ctx.nsmap[None], e.type))
                return retval

    return TYPE_MAP.get("{%s}%s" % (ns, qn))

def process_pending(ctx):
    # process pending
    ctx.debug0("6 %s processing pending complex_types", B(ctx.tns))
    for (c_name, e_name), _v in ctx.pending_types.items():
        process_complex_type(ctx, _v)

    ctx.debug0("7 %s processing pending elements", Y(ctx.tns))
    for _k,_v in ctx.pending_elements.items():
        process_schema_element(ctx, _v)


def print_pending(ctx, fail=False):
    if len(ctx.pending_elements) > 0 or len(ctx.pending_types) > 0:
        if fail:
            logging.basicConfig(level=logging.DEBUG)
        ctx.debug0("%" * 50)
        ctx.debug0(ctx.tns)
        ctx.debug0("")

        ctx.debug0("elements")
        ctx.debug0(pformat(ctx.pending_elements))
        ctx.debug0("")

        ctx.debug0("types")
        ctx.debug0(pformat(ctx.pending_types))
        ctx.debug0("%" * 50)
        if fail:
            raise Exception("there are still unresolved elements")


def parse_schema(ctx, elt):
    ctx.nsmap = nsmap = elt.nsmap
    ctx.prefmap = prefmap = dict([(v,k) for k,v in ctx.nsmap.items()])
    ctx.schema = schema = _prot.from_element(XmlSchema10, elt)

    ctx.pending_types = {}
    ctx.pending_elements = {}

    ctx.tns = tns = schema.target_namespace
    if tns in ctx.retval:
        return
    ctx.retval[tns] = _Schema()

    ctx.debug0("1 %s processing includes", M(tns))
    if schema.includes:
        for include in schema.includes:
            process_includes(ctx, include)

    if schema.elements:
        schema.elements = odict([(e.name, e) for e in schema.elements])
    if schema.complex_types:
        schema.complex_types = odict([(c.name, c) for c in schema.complex_types])
    if schema.simple_types:
        schema.simple_types = odict([(s.name, s) for s in schema.simple_types])
    if schema.attributes:
        schema.attributes = odict([(a.name, a) for a in schema.attributes])

    ctx.debug0("2 %s processing imports", R(tns))
    if schema.imports:
        for imp in schema.imports:
            if not imp.namespace in ctx.retval:
                ctx.debug1("%s importing %s", tns, imp.namespace)
                file_name = ctx.files[imp.namespace]
                parse_schema_file(ctx.clone(2, dirname(file_name)), file_name)
                ctx.retval[tns].imports.add(imp.namespace)

    ctx.debug0("3 %s processing attributes", G(tns))
    if schema.attributes:
        for s in schema.attributes.values():
            n, t= process_attribute(ctx, s)
            ctx.retval[ctx.tns].types[n] = t

    ctx.debug0("4 %s processing simple_types", G(tns))
    if schema.simple_types:
        for s in schema.simple_types.values():
            st = process_simple_type(ctx, s)
            ctx.retval[ctx.tns].types[s.name] = st

    ctx.debug0("5 %s processing complex_types", B(tns))
    if schema.complex_types:
        for c in schema.complex_types.values():
            process_complex_type(ctx, c)

    ctx.debug0("6 %s processing elements", Y(tns))
    if schema.elements:
        for e in schema.elements.values():
            process_schema_element(ctx, e)

    process_pending(ctx)

    if ctx.parent is None: # for the top-most schema
        if ctx.children is not None: # # if it uses <include> or <import>
            # This is needed for schemas with circular imports
            for c in chain([ctx], ctx.children):
                print_pending(c)
            ctx.debug0('')

            for c in chain([ctx], ctx.children):
                process_pending(c)
            for c in chain([ctx], ctx.children):
                process_pending(c)
            ctx.debug0('')

            for c in chain([ctx], ctx.children):
                print_pending(c, fail=True)

    return ctx.retval
