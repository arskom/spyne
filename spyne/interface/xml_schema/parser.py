
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

# To see the list of xml schema builtins recognized by this parser, run defn.py
# in this package.

# This module is EXPERIMENTAL. Only a subset of Xml schema standard is
# implemented.


from collections import defaultdict

import logging
logger = logging.getLogger(__name__)

import os

from itertools import chain
from pprint import pformat
from copy import copy

from os.path import dirname
from os.path import abspath
from os.path import join

from lxml import etree

from spyne.util import memoize
from spyne.util.odict import odict

from spyne.model import Null
from spyne.model import XmlData
from spyne.model import XmlAttribute
from spyne.model import Array
from spyne.model import ComplexModelBase
from spyne.model import ComplexModelMeta
from spyne.model.complex import XmlModifier

from spyne.protocol.xml import XmlDocument

from spyne.interface.xml_schema.defn import TYPE_MAP
from spyne.interface.xml_schema.defn import SchemaBase
from spyne.interface.xml_schema.defn import XmlSchema10

from spyne.util.color import R, G, B, MAG, YEL

PARSER = etree.XMLParser(remove_comments=True)

_prot = XmlDocument()


class _Schema(object):
    def __init__(self):
        self.types = {}
        self.elements = {}
        self.imports = set()


# FIXME: Needs to emit delayed assignment of recursive structures instead of
# lousy ellipses.
@memoize
def Thier_repr(with_ns=False):
    """Template for ``hier_repr``, a ``repr`` variant that shows spyne
    ``ComplexModel``s in a hierarchical format.

    :param with_ns: either bool or a callable that returns the class name
    as string
    """

    if with_ns is False:
        def get_class_name(c):
            return c.get_type_name()
    elif with_ns is True or with_ns is 1:
        def get_class_name(c):
            return "{%s}%s" % (c.get_namespace(), c.get_type_name())
    else:
        def get_class_name(c):
            return with_ns(c.get_namespace(), c.get_type_name())

    def hier_repr(inst, i0=0, I='  ', tags=None):
        if tags is None:
            tags = set()

        cls = inst.__class__
        if not hasattr(cls, '_type_info'):
            return repr(inst)

        clsid = "%s" % (get_class_name(cls))
        if id(inst) in tags:
            return clsid

        tags.add(id(inst))

        i1 = i0 + 1
        i2 = i1 + 1

        retval = [clsid, '(']

        xtba = cls.Attributes._xml_tag_body_as
        if xtba is not None:
            xtba_key, xtba_type = next(xtba)
            if xtba_key is not None:
                value = getattr(inst, xtba_key, None)
                retval.append("%s,\n" % hier_repr(value, i1, I, tags))
            else:
                retval.append('\n')

        for k, v in inst.get_flat_type_info(cls).items():
            value = getattr(inst, k, None)
            if (issubclass(v, Array) or v.Attributes.max_occurs > 1) and \
                                                            value is not None:
                retval.append("%s%s=[\n" % (I * i1, k))
                for subval in value:
                    retval.append("%s%s,\n" % (I * i2,
                                                hier_repr(subval, i2, I, tags)))
                retval.append('%s],\n' % (I * i1))

            elif issubclass(v, XmlData):
                pass

            else:
                retval.append("%s%s=%s,\n" % (I * i1, k,
                                                hier_repr(value, i1, I, tags)))

        retval.append('%s)' % (I * i0))
        return ''.join(retval)

    return hier_repr

SchemaBase.__repr__ = Thier_repr()

hier_repr = Thier_repr()
hier_repr_ns = Thier_repr(with_ns=True)


class XmlSchemaParser(object):
    def __init__(self, files, base_dir=None, repr_=Thier_repr(with_ns=False),
                                                             skip_errors=False):
        self.retval = {}
        self.indent = 0
        self.files = files
        self.base_dir = base_dir
        self.repr = repr_
        if self.base_dir is None:
            self.base_dir = os.getcwd()
        self.parent = None
        self.children = None
        self.nsmap = None
        self.schema = None
        self.prefmap = None

        self.tns = None
        self.pending_elements = None
        self.pending_types = None
        self.skip_errors = skip_errors

        self.pending_simple_types = defaultdict(set)

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

    def parse_schema_file(self, file_name):
        elt = etree.fromstring(open(file_name, 'rb').read(), parser=PARSER)
        return self.parse_schema(elt)

    def process_includes(self, include):
        file_name = include.schema_location
        if file_name is None:
            return

        self.debug1("including %s %s", self.base_dir, file_name)

        file_name = abspath(join(self.base_dir, file_name))
        data = open(file_name, 'rb').read()
        elt = etree.fromstring(data, parser=PARSER)
        self.nsmap.update(elt.nsmap)
        self.prefmap = dict([(v, k) for k, v in self.nsmap.items()])

        sub_schema = _prot.from_element(None, XmlSchema10, elt)
        if sub_schema.includes:
            for inc in sub_schema.includes:
                base_dir = dirname(file_name)
                child_ctx = self.clone(base_dir=base_dir)
                self.process_includes(inc)
                self.nsmap.update(child_ctx.nsmap)
                self.prefmap = dict([(v, k) for k, v in self.nsmap.items()])

        for attr in ('imports', 'simple_types', 'complex_types', 'elements'):
            sub = getattr(sub_schema, attr)
            if sub is None:
                sub = []

            own = getattr(self.schema, attr)
            if own is None:
                own = []

            own.extend(sub)

            setattr(self.schema, attr, own)

    def process_simple_type_list(self, s, name=None):
        item_type = s.list.item_type
        if item_type is None:
            self.debug1("skipping simple type: %s because its list itemType "
                        "could not be found", name)
            return

        base = self.get_type(item_type)
        if base is None:
            self.pending_simple_types[self.get_name(item_type)].add((s, name))
            self.debug1("pending  simple type list: %s "
                                   "because of unseen base %s", name, item_type)

            return

        self.debug1("adding   simple type list: %s", name)
        retval = Array(base, serialize_as='sd-list')  # FIXME: to be implemented
        retval.__type_name__ = name
        retval.__namespace__ = self.tns

        assert not retval.get_type_name() is retval.Empty
        return retval

    def process_simple_type_restriction(self, s, name=None):
        base_name = s.restriction.base
        if base_name is None:
            self.debug1("skipping simple type: %s because its restriction base "
                        "could not be found", name)
            return

        base = self.get_type(base_name)
        if base is None:
            self.pending_simple_types[self.get_name(base_name)].add((s, name))
            self.debug1("pending  simple type: %s because of unseen base %s",
                                                                name, base_name)

            return

        self.debug1("adding   simple type: %s", name)

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

        retval = base.customize(**kwargs)
        retval.__type_name__ = name
        retval.__namespace__ = self.tns
        if retval.__orig__ is None:
            retval.__orig__ = base

        if retval.__extends__ is None:
            retval.__extends__ = base

        assert not retval.get_type_name() is retval.Empty
        return retval

    def process_simple_type_union(self, s, name=None):
        self.debug1("skipping simple type: %s because its union is not "
                    "implemented", name)

    def process_simple_type(self, s, name=None):
        """Returns the simple Spyne type from `<simpleType>` tag."""
        retval = None

        if name is None:
            name = s.name

        if s.list is not None:
            retval = self.process_simple_type_list(s, name)

        elif s.union is not None:
            retval = self.process_simple_type_union(s, name)

        elif s.restriction is not None:
            retval = self.process_simple_type_restriction(s, name)

        if retval is None:
            self.debug1("skipping simple type: %s", name)
            return

        self.retval[self.tns].types[s.name] = retval

        key = self.get_name(name)
        dependents = self.pending_simple_types[key]
        for s, name in set(dependents):
            st = self.process_simple_type(s, name)
            if st is not None:
                self.retval[self.tns].types[s.name] = st

                self.debug2("added back simple type: %s", s.name)
                dependents.remove((s, name))

        if len(dependents) == 0:
            del self.pending_simple_types[key]

        return retval

    def process_schema_element(self, e):
        if e.name is None:
            return

        self.debug1("adding element: %s", e.name)

        t = self.get_type(e.type)
        if t:
            if e.name in self.pending_elements:
                del self.pending_elements[e.name]

            self.retval[self.tns].elements[e.name] = e

        else:
            self.pending_elements[e.name] = e

    def process_attribute(self, a):
        if a.ref is not None:
            t = self.get_type(a.ref)
            return t.type.get_type_name(), t

        if a.type is not None and a.simple_type is not None:
            raise ValueError(a, "Both type and simple_type are defined.")

        elif a.type is not None:
            t = self.get_type(a.type)

            if t is None:
                raise ValueError(a, 'type %r not found' % a.type)

        elif a.simple_type is not None:
            t = self.process_simple_type(a.simple_type, a.name)

            if t is None:
                raise ValueError(a, 'simple type %r not found' % a.simple_type)

        else:
            raise Exception("dunno attr")

        kwargs = {}
        if a.default is not None:
            kwargs['default'] = _prot.from_string(t, a.default)

        if len(kwargs) > 0:
            t = t.customize(**kwargs)
            self.debug2("t = t.customize(**%r)" % kwargs)
        return a.name, XmlAttribute(t)

    def process_complex_type(self, c):
        def process_type(tn, name, wrapper=None, element=None, attribute=None):
            if wrapper is None:
                wrapper = lambda x: x
            else:
                assert issubclass(wrapper, XmlModifier), wrapper

            t = self.get_type(tn)
            key = (c.name, name)
            if t is None:
                self.pending_types[key] = c
                self.debug2("not found: %r(%s)", key, tn)
                return

            if key in self.pending_types:
                del self.pending_types[key]

            assert name is not None, (key, e)

            kwargs = {}
            if element is not None:
                if e.min_occurs != "0":  # spyne default
                    kwargs['min_occurs'] = int(e.min_occurs)

                if e.max_occurs == "unbounded":
                    kwargs['max_occurs'] = e.max_occurs
                elif e.max_occurs != "1":
                    kwargs['max_occurs'] = int(e.max_occurs)

                if e.nillable != True:  # spyne default
                    kwargs['nillable'] = e.nillable

                if e.default is not None:
                    kwargs['default'] = _prot.from_string(t, e.default)

                if len(kwargs) > 0:
                    t = t.customize(**kwargs)

            if attribute is not None:
                if attribute.default is not None:
                    kwargs['default'] = _prot.from_string(t, a.default)

                if len(kwargs) > 0:
                    t = t.customize(**kwargs)

            ti.append( (name, wrapper(t)) )
            self.debug2("    found: %r(%s), c: %r", key, tn, kwargs)

        def process_element(e):
            if e.ref is not None:
                tn = e.ref
                name = e.ref.split(":", 1)[-1]

            elif e.name is not None:
                tn = e.type
                name = e.name

                if tn is None:
                    # According to http://www.w3.org/TR/2004/REC-xmlschema-1-20041028/structures.html#element-element
                    # this means this element is now considered to be a
                    # http://www.w3.org/TR/2004/REC-xmlschema-1-20041028/structures.html#ur-type-itself
                    self.debug2("  skipped: %s ur-type", e.name)
                    return

            else:
                raise Exception("dunno")

            process_type(tn, name, element=e)

        ti = []
        base = ComplexModelBase
        if c.name in self.retval[self.tns].types:
            self.debug1("modifying existing %r", c.name)
        else:
            self.debug1("adding complex type: %s", c.name)

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
            sc = c.simple_content
            ext = sc.extension
            restr = sc.restriction

            if ext is not None:
                base_name = ext.base
                b = self.get_type(ext.base)

                if ext.attributes is not None:
                    for a in ext.attributes:
                        ti.append(self.process_attribute(a))

            elif restr is not None:
                base_name = restr.base
                b = self.get_type(restr.base)

                if restr.attributes is not None:
                    for a in restr.attributes:
                        ti.append(self.process_attribute(a))

            else:
                raise Exception("Invalid simpleContent tag: %r", sc)

            if issubclass(b, ComplexModelBase):
                base = b
            else:
                process_type(base_name, "_data", XmlData)

        if c.name in self.retval[self.tns].types:
            r = self.retval[self.tns].types[c.name]
            r._type_info.update(ti)

        else:
            cls_dict = odict({
                '__type_name__': c.name,
                '__namespace__': self.tns,
                '_type_info': ti,
            })
            if self.repr is not None:
                cls_dict['__repr__'] = self.repr

            r = ComplexModelMeta(str(c.name), (base,), cls_dict)
            self.retval[self.tns].types[c.name] = r

        return r

    def get_name(self, tn):
        if tn.startswith("{"):
            ns, qn = tn[1:].split('}', 1)

        elif ":" in tn:
            ns, qn = tn.split(":", 1)
            ns = self.nsmap[ns]

        else:
            if None in self.nsmap:
                ns, qn = self.nsmap[None], tn
            else:
                ns, qn = self.tns, tn

        return ns, qn

    def get_type(self, tn):
        if tn is None:
            return Null

        ns, qn = self.get_name(tn)

        ti = self.retval.get(ns)
        if ti is not None:
            t = ti.types.get(qn)
            if t:
                return t

            e = ti.elements.get(qn)
            if e:
                if ":" in e.type:
                    return self.get_type(e.type)
                else:
                    retval = self.get_type("{%s}%s" % (ns, e.type))
                    if retval is None and None in self.nsmap:
                        retval = self.get_type("{%s}%s" %
                                                     (self.nsmap[None], e.type))
                    return retval

        return TYPE_MAP.get("{%s}%s" % (ns, qn))

    def process_pending(self):
        # process pending
        self.debug0("6 %s processing pending complex_types", B(self.tns))
        for (c_name, e_name), _v in list(self.pending_types.items()):
            self.process_complex_type(_v)

        self.debug0("7 %s processing pending elements", YEL(self.tns))
        for _k, _v in self.pending_elements.items():
            self.process_schema_element(_v)

    def print_pending(self, fail=False):
        ptt_pending = sum((len(v) for v in self.pending_simple_types.values())) > 0
        if len(self.pending_elements) > 0 or len(self.pending_types) > 0 or \
                                                                    ptt_pending:
            if fail:
                logging.basicConfig(level=logging.DEBUG)
            self.debug0("%" * 50)
            self.debug0(self.tns)
            self.debug0("")

            self.debug0("elements")
            self.debug0(pformat(self.pending_elements))
            self.debug0("")

            self.debug0("simple types")
            self.debug0(pformat(self.pending_simple_types))
            self.debug0("%" * 50)

            self.debug0("complex types")
            self.debug0(pformat(self.pending_types))
            self.debug0("%" * 50)

            if fail:
                raise Exception("there are still unresolved elements")

    def parse_schema(self, elt):
        self.nsmap = dict(elt.nsmap.items())
        self.prefmap = dict([(v, k) for k, v in self.nsmap.items()])
        self.schema = schema = _prot.from_element(self, XmlSchema10, elt)

        self.pending_types = {}
        self.pending_elements = {}

        self.tns = tns = schema.target_namespace
        if self.tns is None:
            self.tns = tns = '__no_ns__'
        if tns in self.retval:
            return
        self.retval[tns] = _Schema()

        self.debug0("1 %s processing includes", MAG(tns))
        if schema.includes:
            for include in schema.includes:
                self.process_includes(include)

        if schema.elements:
            schema.elements = odict([(e.name, e) for e in schema.elements])
        if schema.complex_types:
            schema.complex_types = odict([(c.name, c)
                                                 for c in schema.complex_types])
        if schema.simple_types:
            schema.simple_types = odict([(s.name, s)
                                                 for s in schema.simple_types])
        if schema.attributes:
            schema.attributes = odict([(a.name, a) for a in schema.attributes])

        self.debug0("2 %s processing imports", R(tns))
        if schema.imports:
            for imp in schema.imports:
                if not imp.namespace in self.retval:
                    self.debug1("%s importing %s", tns, imp.namespace)
                    fname = self.files[imp.namespace]
                    self.clone(2, dirname(fname)).parse_schema_file(fname)
                    self.retval[tns].imports.add(imp.namespace)

        self.debug0("3 %s processing simple_types", G(tns))
        if schema.simple_types:
            for s in schema.simple_types.values():
                self.process_simple_type(s)

            # no simple types should have been left behind.
            assert sum((len(v) for v in self.pending_simple_types.values())) == 0, \
                                              self.pending_simple_types.values()

        self.debug0("4 %s processing attributes", G(tns))
        if schema.attributes:
            for s in schema.attributes.values():
                n, t = self.process_attribute(s)
                self.retval[self.tns].types[n] = t

        self.debug0("5 %s processing complex_types", B(tns))
        if schema.complex_types:
            for c in schema.complex_types.values():
                self.process_complex_type(c)

        self.debug0("6 %s processing elements", YEL(tns))
        if schema.elements:
            for e in schema.elements.values():
                self.process_schema_element(e)

        self.process_pending()

        if self.parent is None:  # for the top-most schema
            if self.children is not None:  # if it uses <include> or <import>
                # This is needed for schemas with circular imports
                for c in chain([self], self.children):
                    c.print_pending()
                self.debug0('')

                # FIXME: should put this in a while loop that loops until no
                # changes occur
                for c in chain([self], self.children):
                    c.process_pending()
                for c in chain([self], self.children):
                    c.process_pending()
                self.debug0('')

                for c in chain([self], self.children):
                    c.print_pending(fail=(not self.skip_errors))

        return self.retval
