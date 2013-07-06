
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
debug = logger.debug

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

from spyne.model.complex import XmlData
from spyne.model.complex import XmlAttribute
from spyne.model.complex import Array
from spyne.model.complex import ComplexModelBase
from spyne.model.complex import ComplexModelMeta

from spyne.protocol.xml import XmlDocument
from spyne.interface.xml_schema.defn import TYPE_MAP
from spyne.interface.xml_schema.defn import XmlSchema

PARSER = etree.XMLParser(remove_comments=True)


class _Schema(object):
    def __init__(self):
        self.types = {}
        self.elements = {}
        self.imports = set()


def own_repr(self, i0=0, I = '  '):
    if not hasattr(self.__class__, '_type_info'):
        return repr(self)

    i1 = i0 + 1
    i2 = i1 + 1

    retval = []
    retval.append(self.__class__.get_type_name())
    retval.append('(\n')
    for k,v in self._type_info.items():
        value = getattr(self, k, None)
        if (issubclass(v, Array) or v.Attributes.max_occurs > 1) and \
                                                        value is not None:
            retval.append("%s%s=[\n" %(I*i1, k))
            for subval in value:
                    retval.append("%s%s,\n" % (I*i2, own_repr(subval,i2)))
            retval.append('%s]\n' % (I*i1))
        else:
            retval.append("%s%s=%s,\n" %(I*i1, k,
                                        own_repr(getattr(self, k, None),i1)))
    retval.append('%s)' % (I*i0))
    return ''.join(retval)


class ParsingCtx(object):
    def __init__(self, files, base_dir=None, own_repr=own_repr):
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

    i0 = lambda self: "  " *  self.indent
    i1 = lambda self: "  " * (self.indent + 1)
    i2 = lambda self: "  " * (self.indent + 2)

try:
    import colorama
    r = lambda s: "%s%s%s%s" % (colorama.Fore.RED, colorama.Style.BRIGHT, s,
                                                    colorama.Style.RESET_ALL)
    g = lambda s: "%s%s%s" % (colorama.Fore.GREEN, s, colorama.Fore.RESET)
    b = lambda s: "%s%s%s%s" % (colorama.Fore.BLUE, colorama.Style.BRIGHT, s,
                                                    colorama.Style.RESET_ALL)
    y = lambda s: "%s%s%s%s" % (colorama.Fore.YELLOW, colorama.Style.BRIGHT, s,
                                                    colorama.Style.RESET_ALL)
    m = lambda s: "%s%s%s%s" % (colorama.Fore.MAGENTA, colorama.Style.BRIGHT, s,
                                                    colorama.Style.RESET_ALL)

except ImportError:
    r = lambda s: s
    g = lambda s: s
    b = lambda s: s
    y = lambda s: s
    m = lambda s: s


def parse_schema_file(ctx, file_name):
    elt = etree.fromstring(open(file_name).read(), parser=PARSER)
    return parse_schema(ctx, elt)


def process_includes(ctx, include):
    file_name = include.schema_location
    if file_name is None:
        return

    debug("%s including %s %s", ctx.i1(), ctx.base_dir, file_name)

    file_name = abspath(join(ctx.base_dir, file_name))
    data = open(file_name).read()
    elt = etree.fromstring(data, parser=PARSER)
    ctx.nsmap.update(elt.nsmap)
    ctx.prefmap = dict([(v,k) for k,v in ctx.nsmap.items()])

    sub_schema = XmlDocument().from_element(XmlSchema, elt)
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

def process_simple_type(ctx, s):
    if s.restriction is None:
        debug("%s skipping simple type: %s",  ctx.i1(), s.name)
        return
    if s.restriction.base is None:
        debug("%s skipping simple type: %s",  ctx.i1(), s.name)
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

    debug("%s adding   simple type: %s",  ctx.i1(), s.name)
    ctx.retval[ctx.tns].types[s.name] = base.customize(**kwargs)

def process_element(ctx, e):
    if e.name is None:
        return
    if e.type is None:
        return

    debug("%s adding element: %s", ctx.i1(), e.name)
    t = get_type(ctx, e.type)

    key = e.name
    if t:
        if key in ctx.pending_elements:
            del ctx.pending_elements[key]

        ctx.retval[ctx.tns].elements[e.name] = e

    else:
        ctx.pending_elements[key] = e

def process_complex_type(ctx, c):
    def process_type(tn, name, wrapper=lambda x:x):
        t = get_type(ctx, tn)
        key = (c.name, name)
        if t is None:
            ctx.pending_types[key] = c
            debug("%s not found: %r", ctx.i2(), key)

        else:
            if key in ctx.pending_types:
                del ctx.pending_types[key]
            assert name, (key, e)

            ti.append( (name, wrapper(t)) )
            debug("%s     found: %r", ctx.i2(), key)


    ti = []
    _pending = False
    debug("%s adding complex type: %s", ctx.i1(), c.name)

    if c.sequence is not None and c.sequence.element is not None:
        for e in c.sequence.element:
            if e.ref is not None:
                tn = e.ref
                name = e.ref.split(":", 1)[-1]

            elif e.type is not None:
                tn = e.type
                name = e.name

            else:
                raise Exception("dunno")

            process_type(tn, name)

    if c.attributes is not None:
        for a in c.attributes:
            if a.name is None:
                continue
            if a.type is None:
                continue

            t = process_type(a.type, a.name)


    if c.simple_content is not None:
        if c.simple_content.extension is not None: 
            ext = c.simple_content.extension
            if ext.base is not None:
                # FIXME: find a way to generate _data
                process_type(ext.base, "_data", XmlData)
            if ext.attributes is not None:
                for a in ext.attributes:
                    if a.ref is not None:
                        tn = a.ref
                        name = a.ref.split(":", 1)[-1]

                    elif a.type is not None:
                        tn = a.type
                        name = a.name

                    else:
                        raise Exception("dunno attr")

                    process_type(tn, name, XmlAttribute)

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
    if tn.startswith("{"):
        ns, qn = tn[1:].split('}',1)
    elif ":" in tn:
        ns, qn = tn.split(":",1)
        ns = ctx.nsmap[ns]
    else:
        if None in ctx.prefmap:
            ns, qn = ctx.tns, tn
        else:
            ns, qn = ctx.nsmap[None], tn

    ti = ctx.retval.get(ns)
    if ti:
        t = ti.types.get(qn)
        if t:
            return t

        e = ti.elements.get(qn)
        if e:
            if ":" in e.type:
                return get_type(ctx, e.type)
            else:
                return get_type(ctx, "{%s}%s" % (ns, e.type))

    return TYPE_MAP.get("{%s}%s" % (ns, qn))

def process_pending(ctx):
    # process pending
    debug("%s6 %s processing pending complex_types", ctx.i0(), b(ctx.tns))
    for (c_name, e_name), _v in ctx.pending_types.items():
        process_complex_type(ctx, _v)

    debug("%s7 %s processing pending elements", ctx.i0(), y(ctx.tns))
    for _k,_v in ctx.pending_elements.items():
        process_element(ctx, _v)

def print_pending(ctx):
    if len(ctx.pending_elements) > 0 or len(ctx.pending_types) > 0:
        debug("%" * 50)
        debug(ctx.tns)
        debug("")

        debug("elements")
        debug(pformat(ctx.pending_elements))
        debug("")

        debug("types")
        debug(pformat(ctx.pending_types))
        debug("%" * 50)

def parse_schema(ctx, elt):
    ctx.nsmap = nsmap = elt.nsmap
    ctx.prefmap = prefmap = dict([(v,k) for k,v in ctx.nsmap.items()])
    ctx.schema = schema = XmlDocument().from_element(XmlSchema, elt)

    ctx.pending_types = {}
    ctx.pending_elements = {}

    ctx.tns = tns = schema.target_namespace
    if tns in ctx.retval:
        return
    ctx.retval[tns] = _Schema()

    debug("%s1 %s processing includes", ctx.i0(), m(tns))
    if schema.includes:
        for include in schema.includes:
            process_includes(ctx, include)

    if schema.elements:
        schema.elements = odict([(e.name, e) for e in schema.elements])
    if schema.complex_types:
        schema.complex_types = odict([(c.name, c) for c in schema.complex_types])
    if schema.simple_types:
        schema.simple_types = odict([(s.name, s) for s in schema.simple_types])

    debug("%s2 %s processing imports", ctx.i0(), r(tns))
    if schema.imports:
        for imp in schema.imports:
            if not imp.namespace in ctx.retval:
                debug("%s %s importing %s", ctx.i1(), tns, imp.namespace)
                file_name = ctx.files[imp.namespace]
                parse_schema_file(ctx.clone(2, dirname(file_name)), file_name)

    debug("%s3 %s processing simple_types", ctx.i0(), g(tns))
    if schema.simple_types:
        for s in schema.simple_types.values():
            process_simple_type(ctx, s)

    debug("%s4 %s processing complex_types", ctx.i0(), b(tns))
    if schema.complex_types:
        for c in schema.complex_types.values():
            process_complex_type(ctx, c)

    debug("%s5 %s processing elements", ctx.i0(), y(tns))
    if schema.elements:
        for e in schema.elements.values():
            process_element(ctx, e)

    process_pending(ctx)

    if ctx.parent is None: # for the top-most schema
        if ctx.children is not None: # # if it uses <include> or <import>
            # This is needed for schemas with circular imports
            for c in chain([ctx], ctx.children):
                print_pending(c)
            debug('')

            for c in chain([ctx], ctx.children):
                process_pending(c)
            for c in chain([ctx], ctx.children):
                process_pending(c)
            debug('')
            for c in chain([ctx], ctx.children):
                print_pending(c)

    return ctx.retval
