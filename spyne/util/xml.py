
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


"""The `spyne.util.xml` module contains various Xml and Xml Schema related
utility functions.
"""

from lxml import etree

from pprint import pprint

from spyne.const import xml_ns
from spyne.util.odict import odict

from spyne.interface import Interface
from spyne.interface.xml_schema import XmlSchema
from spyne.protocol.xml import XmlDocument
from spyne.interface.xml_schema.defn import XmlSchema as XmlSchemaDefinition
from spyne.interface.xml_schema.defn import TYPE_MAP

from spyne.model.complex import ComplexModelBase
from spyne.model.complex import ComplexModelMeta

from spyne.const import xml_ns


class FakeApplication(object):
    pass


def get_schema_documents(models, default_namespace=None):
    '''Returns the schema documents in a dict whose keys are namespace prefixes
    and values are Element objects.

    :param models: A list of spyne.model classes that will be represented in
                   the schema.

    '''

    if default_namespace is None:
        default_namespace = models[0].get_namespace()

    fake_app = FakeApplication()
    fake_app.tns = default_namespace
    fake_app.services = []

    interface = Interface(fake_app)
    for m in models:
        m.resolve_namespace(m, default_namespace)
        interface.add_class(m)
    interface.populate_interface(fake_app)

    document = XmlSchema(interface)
    document.build_interface_document()

    return document.get_interface_document()


def get_validation_schema(models, default_namespace=None):
    '''Returns the validation schema object for the given models.

    :param models: A list of spyne.model classes that will be represented in
                   the schema.
    '''

    if default_namespace is None:
        default_namespace = models[0].get_namespace()

    fake_app = FakeApplication()
    fake_app.tns = default_namespace
    fake_app.services = []

    interface = Interface(fake_app)
    for m in models:
        interface.add_class(m)

    schema = XmlSchema(interface)
    schema.build_validation_schema()

    return schema.validation_schema


def _dig(par):
    for elt in par:
        elt.tag = elt.tag.split('}')[-1]
        _dig(elt)


def get_object_as_xml(value, cls=None, root_tag_name=None, no_namespace=False):
    '''Returns an ElementTree representation of a
    :class:`spyne.model.complex.ComplexModel` subclass.

    :param value: The instance of the class to be serialized.
    :param value: The root tag string to use. Defaults to the output of
        ``value.__class__.get_type_name_ns()``.
    '''

    if cls is None:
        cls = value.__class__
    xml_object = XmlDocument()
    parent = etree.Element("parent")

    xml_object.to_parent_element(cls, value, cls.get_namespace(),
                                                          parent, root_tag_name)

    if no_namespace:
        _dig(parent)
        etree.cleanup_namespaces(parent)

    return parent[0]


def get_xml_as_object(elt, cls):
    '''Returns a native :class:`spyne.model.complex.ComplexModel` child from an
    ElementTree representation of the same class.

    :param value: The class the xml document represents.
    :param value: The xml document to be deserialized.
    '''

    xml_object = XmlDocument()

    return xml_object.from_element(cls, elt)


parser = etree.XMLParser(remove_comments=True)
class Schema(object):
    def __init__(self):
        self.types = {}
        self.elements = {}
        self.imports = set()

def parse_schema(elt, files={}):
    return _parse_schema(elt, files, {}, 0)

def parse_schema_file(file_name, files):
    elt = etree.fromstring(open(file_name).read(), parser=parser)
    return _parse_schema(elt, files, {}, 0)

def _parse_schema_file(file_name, files, retval, indent):
    elt = etree.fromstring(open(file_name).read(), parser=parser)
    return _parse_schema(elt, files, retval, indent)

i = lambda i: "  " * i
j = lambda i: "  " * (i+1)
k = lambda i: "  " * (i+2)

import colorama
r = lambda s: "%s%s%s" % (colorama.Fore.RED, s, colorama.Fore.RESET)
g = lambda s: "%s%s%s" % (colorama.Fore.GREEN, s, colorama.Fore.RESET)
b = lambda s: "%s%s%s%s" % (colorama.Fore.BLUE, colorama.Style.BRIGHT, s, colorama.Style.RESET_ALL)
y = lambda s: "%s%s%s%s" % (colorama.Fore.YELLOW, colorama.Style.BRIGHT, s, colorama.Style.RESET_ALL)


def _parse_schema(elt, files, retval, indent):
    def process_simple_type(s, second_pass=False):
        if s.restriction is None:
            return
        if s.restriction.base is None:
            return

        base = get_type(s.restriction.base)
        if base is None and second_pass:
            raise ValueError(base)

        kwargs = {}
        if s.restriction.enumeration:
            kwargs['values'] = [e.value for e in s.restriction.enumeration]

        tn = "{%s}%s" % (tns, s.name)
        print j(indent), "adding simple type:", tn
        retval[tns].types[tn] = base.customize(**kwargs)

    def process_element(e, second_pass=False):
        if e.name is None:
            return
        if e.type is None:
            return

        print j(indent), "adding element:", e.name
        t = get_type(e.type)
        if t:
            retval[tns].elements[e.name] = e

        elif second_pass:
            raise ValueError((tns, e.name))

        else:
            pending_elements[e.name] = e

    def process_complex_type(c, second_pass=False):
        ti = []
        _pending = False
        if c.sequence is not None and c.sequence.element is not None:
            for e in c.sequence.element:
                if e.ref is not None:
                    tn = e.ref
                elif e.type is not None:
                    tn = e.type
                else:
                    raise Exception("dunno")

                t = get_type(tn)
                if t is None:
                    if second_pass or ":" in tn:
                        raise ValueError(tn)

                    ti.append( (e.name, e) )
                    pending_types[c.name] = c
                    _pending = True

                else:
                    ti.append( (e.name, t) )

        if not _pending:
            print j(indent),
            print "adding complex type (2=%s):" % second_pass,
            print c.name

            retval[tns].types[c.name] = ComplexModelMeta(
                    str(c.name),
                    (ComplexModelBase,),
                    {
                        '__type_name__': c.name,
                        '__namespace__': tns,
                        '_type_info': ti,
                    }
                )

    def get_type(tn):
        if tn.startswith("{"):
            ns, qn = tn[1:].split('}',1)
        elif ":" in tn:
            ns, qn = tn.split(":",1)
            ns = nsmap[ns]
        else:
            ns, qn = tns, tn

        print k(indent), tn, "=>", tns, qn
        ti = retval.get(ns)
        if ti:
            t = ti.types.get(qn)
            if t:
                return t

            e = ti.elements.get(qn)
            if e:
                if ":" in e.type:
                    return get_type(e.type)
                else:
                    return get_type("{%s}%s" % (ns, e.type))

        return TYPE_MAP.get("{%s}%s" % (ns, qn))

    nsmap = elt.nsmap
    schema = get_xml_as_object(elt, XmlSchemaDefinition)

    if schema.elements:
        schema.elements = odict([(e.name,e) for e in schema.elements])
    if schema.complex_types:
        schema.complex_types = odict([(c.name, c) for c in schema.complex_types])
    if schema.simple_types:
        schema.simple_types = odict([(s.name, s) for s in schema.simple_types])

    pending_types = {}
    pending_elements = {}

    tns = schema.target_namespace
    if tns in retval:
        return
    retval[tns] = Schema()

    print i(indent), 1, r(tns), "processing imports"
    if schema.imports:
        for imp in schema.imports:
            if not imp.namespace in retval:
                print j(indent), tns, "importing", imp.namespace
                file_name = files[imp.namespace]
                _parse_schema_file(file_name, files, retval, indent+2)

    print i(indent), 2, g(tns), "processing simple_types"
    if schema.simple_types:
        for s in schema.simple_types.values():
            process_simple_type(s)

    print i(indent), 3, b(tns), "processing complex_types"
    if schema.complex_types:
        for c in schema.complex_types.values():
            process_complex_type(c)

    print i(indent), 4, y(tns), "processing elements"
    if schema.elements:
        for e in schema.elements.values():
            process_element(e)

    # process pending
    print i(indent), 5, b(tns), "processing pending complex_types"
    for _k,_v in pending_types.items():
        process_complex_type(_v, True)
    print

    print i(indent), 6, b(tns), "processing pending elements"
    for _k,_v in pending_elements.items():
        process_element(_v, True)
    print

    print r('*'*30)
    pprint(retval[tns].elements)
    print r('*'*30)

    return retval[tns]
