import os
import unittest

from soaplib.model.clazz import ClassSerializer
from soaplib.model.primitive import String

from soaplib.util.xsd_gen import XSDGenerator


class SimpleModel(ClassSerializer):

    __namespace__ = "SimpleModel"
    text = String


class NestedModel(ClassSerializer):

    __namespace__ = "NestedModel"
    text = String
    simple_model = SimpleModel


class DoubleNestedModel(ClassSerializer):

    __namespace__ = "DoubleNestedModel"
    some_text = String
    nested = NestedModel


class TestXsdGen(unittest.TestCase):

    def setUp(self):
        self.simple_xsd = '''<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"
 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
 xmlns:xop="http://www.w3.org/2004/08/xop/include" xmlns:s2="SimpleModel"
 targetNamespace="SimpleModel" elementFormDefault="qualified"><xs:element
 name="SimpleModel" type="s2:SimpleModel"/><xs:complexType
 name="SimpleModel"><xs:sequence><xs:element name="text" type="xs:string"
 minOccurs="0" nillable="true"/></xs:sequence></xs:complexType></xs:schema>'''

        self.nested_xsd = '''<xs:schema xmlns:s3="NestedModel"
 xmlns:xs="http://www.w3.org/2001/XMLSchema"
 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
 xmlns:xop="http://www.w3.org/2004/08/xop/include" xmlns:s4="SimpleModel"
 targetNamespace="NestedModel" elementFormDefault="qualified"><xs:import
 namespace="SimpleModel" schemaLocation="s4.xsd"/><xs:element name="NestedModel"
 type="s3:NestedModel"/><xs:complexType name="NestedModel"><xs:sequence><xs:element
 name="text" type="xs:string" minOccurs="0" nillable="true"/><xs:element
 name="simple_model" type="s4:SimpleModel" minOccurs="0"
 nillable="true"/></xs:sequence></xs:complexType></xs:schema>'''

        self.double_nested_xsd = '''<xs:schema
 xmlns:xop="http://www.w3.org/2004/08/xop/include" xmlns:s6="SimpleModel"
 xmlns:s5="NestedModel" xmlns:s4="DoubleNestedModel"
 xmlns:xs="http://www.w3.org/2001/XMLSchema"
 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
 targetNamespace="DoubleNestedModel" elementFormDefault="qualified"><xs:import
 namespace="NestedModel" schemaLocation="s5.xsd"/><xs:element
 name="DoubleNestedModel" type="s4:DoubleNestedModel"/><xs:complexType
 name="DoubleNestedModel"><xs:sequence><xs:element name="some_text"
 type="xs:string" minOccurs="0" nillable="true"/><xs:element name="nested"
 type="s5:NestedModel" minOccurs="0" nillable="true"/></xs:sequence></xs:complexType></xs:schema>'''

        self.xsd_gen = XSDGenerator()

    def test_simple_xsd(self):
        simple_xsd = self.xsd_gen.build_stand_alone_xsd(SimpleModel,
                                                        pretty_print=False)
        self.assertEquals(self.simple_xsd.replace(os.linesep,''), simple_xsd)

    def test_nested_xsd(self):
        nested_xsd = self.xsd_gen.build_stand_alone_xsd(NestedModel,
                                                        pretty_print=False)
        self.assertEquals(self.nested_xsd.replace(os.linesep,''), nested_xsd)

    def test_double_nested_xsd(self):
        double_xsd = self.xsd_gen.build_stand_alone_xsd(DoubleNestedModel,
                                                        pretty_print=False)
        self.assertEquals(self.double_nested_xsd.replace(os.linesep,''),
                          double_xsd)


