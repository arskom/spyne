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

from spyne.application import Application
from spyne.const import xml_ns as ns
from spyne.decorator import rpc
from spyne.model.binary import ByteArray
from spyne.model.complex import ComplexModel
from spyne.model.complex import XmlAttribute
from spyne.model.primitive import AnyXml
from spyne.model.primitive import Integer
from spyne.model.primitive import Mandatory
from spyne.model.primitive import Unicode
from spyne.model.primitive import Uuid
from spyne.protocol.soap import Soap11
from spyne.service import ServiceBase
from spyne.util.xml import get_schema_documents


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

        from lxml import etree

        docs = get_schema_documents([SomeType])
        print(etree.tostring(docs['tns'], pretty_print=True))
        any = docs['tns'].xpath('//xsd:any', namespaces={'xsd': ns.xsd})

        assert len(any) == 1
        assert any[0].attrib['namespace'] == '##other'
        assert any[0].attrib['processContents'] == 'lax'


if __name__ == '__main__':
    unittest.main()
