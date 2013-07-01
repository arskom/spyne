#!/usr/bin/env python
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
import unittest

from lxml import etree

from spyne.util.odict import odict
from spyne.application import Application
from spyne.const import xml_ns as ns
from spyne.decorator import rpc
from spyne.model.binary import ByteArray
from spyne.model.complex import ComplexModel
from spyne.model.complex import XmlAttribute
from spyne.model.complex import XmlData
from spyne.model.primitive import AnyXml
from spyne.model.primitive import Integer
from spyne.model.primitive import Mandatory
from spyne.model.primitive import Unicode
from spyne.model.primitive import Uuid
from spyne.protocol.soap import Soap11
from spyne.service import ServiceBase
from spyne.util.xml import get_schema_documents
from spyne.util.xml import parse_schema
from spyne.interface.xml_schema import XmlSchema


class TestXmlSchema(unittest.TestCase):
    def test_customized_class_with_empty_subclass(self):
        class SummaryStatsOfDouble(ComplexModel):
            _type_info = [('Min', XmlAttribute(Integer, use='required')),
                          ('Max', XmlAttribute(Integer, use='required')),
                          ('Avg', XmlAttribute(Integer, use='required'))]

        class SummaryStats(SummaryStatsOfDouble):
            ''' this is an empty base class '''

        class Payload(ComplexModel):
            _type_info = [('Stat1', SummaryStats.customize(nillable=False)),
                          ('Stat2', SummaryStats),
                          ('Stat3', SummaryStats),
                          ('Dummy', Unicode)]

        class JackedUpService(ServiceBase):
            @rpc(_returns=Payload)
            def GetPayload(ctx):
                return Payload()

        Application([JackedUpService],
            tns='kickass.ns',
            in_protocol=Soap11(validator='lxml'),
            out_protocol=Soap11()
        )

        # if no exceptions while building the schema, no problem.
        # see: https://github.com/arskom/spyne/issues/226


    def test_namespaced_xml_attribute(self):
        class RdfAbout(XmlAttribute):
            __type_name__ = "about"
            __namespace__ = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"

        class Release(ComplexModel):
            __namespace__ = "http://usefulinc.com/ns/doap#"

            _type_info = [
                ('about', RdfAbout(Unicode, ns="http://www.w3.org/1999/02/22-rdf-syntax-ns#")),
            ]

        class Project(ComplexModel):
            __namespace__ = "http://usefulinc.com/ns/doap#"

            _type_info = [
                ('about', RdfAbout(Unicode, ns="http://www.w3.org/1999/02/22-rdf-syntax-ns#")),
                ('release', Release.customize(max_occurs=float('inf'))),
            ]

        class RdfService(ServiceBase):
            @rpc(Unicode, Unicode, _returns=Project)
            def some_call(ctx, a, b):
                pass

        Application([RdfService],
            tns='spynepi',
            in_protocol=Soap11(validator='lxml'),
            out_protocol=Soap11()
        )

        # if no exceptions while building the schema, no problem.

    def test_customized_simple_type_in_xml_attribute(self):
        class Product(ComplexModel):
            __namespace__ = 'some_ns'

            id = XmlAttribute(Uuid)
            edition = Unicode
            edition_id = XmlAttribute(Uuid, attribute_of='edition')

        class SomeService(ServiceBase):
            @rpc(Product, _returns=Product)
            def echo_product(ctx, product):
                logging.info('edition_id: %r', product.edition_id)
                return product

        Application([SomeService],
            tns='some_ns',
            in_protocol=Soap11(validator='lxml'),
            out_protocol=Soap11()
        )

        # if no exceptions while building the schema, no problem.

    def test_binary_encodings(self):
        class Product(ComplexModel):
            __namespace__ = 'some_ns'

            hex = ByteArray(encoding='hex')
            base64_1 = ByteArray(encoding='base64')
            base64_2 = ByteArray

        class SomeService(ServiceBase):
            @rpc(Product, _returns=Product)
            def echo_product(ctx, product):
                logging.info('edition_id: %r', product.edition_id)
                return product

        app = Application([SomeService],
            tns='some_ns',
            in_protocol=Soap11(validator='lxml'),
            out_protocol=Soap11()
        )

        _ns = {'xs': "http://www.w3.org/2001/XMLSchema"}
        xs = XmlSchema(app.interface)
        xs.build_interface_document()
        elt = xs.get_interface_document()['tns'].xpath(
                    '//xs:complexType[@name="Product"]',
                    namespaces=_ns)[0]

        assert elt.xpath('//xs:element[@name="base64_1"]/@type',
                                        namespaces=_ns)[0] == 'xs:base64Binary'
        assert elt.xpath('//xs:element[@name="base64_2"]/@type',
                                        namespaces=_ns)[0] == 'xs:base64Binary'
        assert elt.xpath('//xs:element[@name="hex"]/@type',
                                        namespaces=_ns)[0] == 'xs:hexBinary'


    def test_multilevel_customized_simple_type(self):
        class ExampleService(ServiceBase):
            __tns__ = 'http://xml.company.com/ns/example/'

            @rpc(Mandatory.Uuid, _returns=Unicode)
            def say_my_uuid(ctx, uuid):
                return 'Your UUID: %s' % uuid

        Application([ExampleService],
            tns='kickass.ns',
            in_protocol=Soap11(validator='lxml'),
            out_protocol=Soap11()
        )

        # if no exceptions while building the schema, no problem.
        # see: http://stackoverflow.com/questions/16042132/cannot-use-mandatory-uuid-or-other-pattern-related-must-be-type-as-rpc-argumen

    def test_any_tag(self):
        logging.basicConfig(level=logging.DEBUG)

        class SomeType(ComplexModel):
            __namespace__ = "zo"

            anything = AnyXml(schema_tag='{%s}any' % ns.xsd, namespace='##other',
                                                         process_contents='lax')

        docs = get_schema_documents([SomeType])
        print(etree.tostring(docs['tns'], pretty_print=True))
        any = docs['tns'].xpath('//xsd:any', namespaces={'xsd': ns.xsd})

        assert len(any) == 1
        assert any[0].attrib['namespace'] == '##other'
        assert any[0].attrib['processContents'] == 'lax'

    def test_xml_data(self):
        tns = 'kickass.ns'
        class ProductEdition(ComplexModel):
            __namespace__ = tns
            id = XmlAttribute(Uuid)
            name = XmlData(Unicode)

        class Product(ComplexModel):
            __namespace__ = tns
            id = XmlAttribute(Uuid)
            edition = ProductEdition
            sample = XmlAttribute(Unicode, attribute_of='edition')

        class ExampleService(ServiceBase):
            @rpc(Product, _returns=Product)
            def say_my_uuid(ctx, product):
                pass

        app = Application([ExampleService],
            tns='kickass.ns',
            in_protocol=Soap11(validator='lxml'),
            out_protocol=Soap11()
        )

        schema = XmlSchema(app.interface)
        schema.build_interface_document()

        doc = schema.get_interface_document()['tns']
        print etree.tostring(doc, pretty_print=True)

        assert len(doc.xpath(
                '/xs:schema/xs:complexType[@name="Product"]'
                                    '/xs:sequence/xs:element[@name="edition"]'
                '/xs:complexType/xs:simpleContent/xs:extension'
                                    '/xs:attribute[@name="id"]'
                ,namespaces=app.interface.nsmap)) == 1

    def test_subs(self):
        from lxml import etree
        from spyne.util.xml import get_schema_documents
        xpath = lambda o, x: o.xpath(x, namespaces={"xs": ns.xsd})

        m = {
            "s0": "aa",
            "s2": "cc",
            "s3": "dd",
        }

        class C(ComplexModel):
            __namespace__ = "aa"
            a = Integer
            b = Integer(sub_name="bb")
            c = Integer(sub_ns="cc")
            d = Integer(sub_ns="dd", sub_name="dd")

        elt = get_schema_documents([C], "aa")['tns']
        print etree.tostring(elt, pretty_print=True)

        seq, = xpath(elt, "xs:complexType/xs:sequence")

        assert len(seq) == 4
        assert len(xpath(seq, 'xs:element[@name="a"]')) == 1
        assert len(xpath(seq, 'xs:element[@name="bb"]')) == 1

        # TODO: this doesn't feel right.
        # check the spec to see whether it should it be prefixed.
        assert len(xpath(seq, 'xs:element[@name="{cc}c"]')) == 1
        assert len(xpath(seq, 'xs:element[@name="{dd}dd"]')) == 1


class TestXmlSchemaParser(unittest.TestCase):
    def test_simple(self):
        class SomeGuy(ComplexModel):
            __namespace__ = 'some_ns'

            id = Integer

        schema = get_schema_documents([SomeGuy], "some_ns")['tns']
        print etree.tostring(schema, pretty_print=True)

        objects = parse_schema(schema)
        print objects

        NewGuy = objects['some_ns'].types["SomeGuy"]
        assert NewGuy.get_type_name() == SomeGuy.get_type_name()
        assert NewGuy.get_namespace() == SomeGuy.get_namespace()
        assert dict(NewGuy._type_info) == dict(SomeGuy._type_info)

    def test_customized_type(self):
        class SomeGuy(ComplexModel):
            __namespace__ = 'some_ns'

            name = Unicode(2)

        schema = get_schema_documents([SomeGuy], "some_ns")['tns']
        print etree.tostring(schema, pretty_print=True)

        objects = parse_schema(schema)
        print objects

        NewGuy = objects['some_ns'].types["SomeGuy"]
        assert NewGuy._type_info['name'].Attributes.max_len == 2

    def test_attribute(self):
        class SomeGuy(ComplexModel):
            __namespace__ = 'some_ns'

            name = XmlAttribute(Unicode)

        schema = get_schema_documents([SomeGuy], "some_ns")['tns']
        print etree.tostring(schema, pretty_print=True)

        objects = parse_schema(schema)
        print objects

        NewGuy = objects['some_ns'].types["SomeGuy"]
        assert NewGuy._type_info['name'].Attributes.max_len == 2

if __name__ == '__main__':
    unittest.main()
