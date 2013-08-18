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

import datetime
import unittest

from pprint import pprint

from lxml import etree

from base64 import b64encode

from spyne import Application
from spyne import rpc
from spyne import ServiceBase
from spyne.const import xml_ns
from spyne.interface import Interface
from spyne.interface.wsdl import Wsdl11
from spyne.protocol import ProtocolBase
from spyne.protocol.soap import Soap11
from spyne.model import ByteArray
from spyne.model import Array
from spyne.model import ComplexModel
from spyne.model import SelfReference
from spyne.model import XmlData
from spyne.model import XmlAttribute
from spyne.model import Unicode
from spyne.model import DateTime
from spyne.model import Float
from spyne.model import Integer
from spyne.model import String

from spyne.protocol.dictdoc import SimpleDictDocument
from spyne.protocol.xml import XmlDocument

from spyne.test import FakeApp

ns_test = 'test_namespace'

class Address(ComplexModel):
    street = String
    city = String
    zip = Integer
    since = DateTime
    lattitude = Float
    longitude = Float

Address.resolve_namespace(Address, __name__)

class Person(ComplexModel):
    name = String
    birthdate = DateTime
    age = Integer
    addresses = Array(Address)
    titles = Array(String)

Person.resolve_namespace(Person, __name__)

class Employee(Person):
    employee_id = Integer
    salary = Float

Employee.resolve_namespace(Employee, __name__)

class Level2(ComplexModel):
    arg1 = String
    arg2 = Float

Level2.resolve_namespace(Level2, __name__)

class Level3(ComplexModel):
    arg1 = Integer

Level3.resolve_namespace(Level3, __name__)

class Level4(ComplexModel):
    arg1 = String

Level4.resolve_namespace(Level4, __name__)

class Level1(ComplexModel):
    level2 = Level2
    level3 = Array(Level3)
    level4 = Array(Level4)

Level1.resolve_namespace(Level1, __name__)

class TestComplexModel(unittest.TestCase):

    def test_simple_class(self):
        a = Address()
        a.street = '123 happy way'
        a.city = 'badtown'
        a.zip = 32
        a.lattitude = 4.3
        a.longitude = 88.0

        element = etree.Element('test')
        XmlDocument().to_parent_element(Address, a, ns_test, element)
        element = element[0]
        self.assertEquals(5, len(element.getchildren()))

        a.since = datetime.datetime(year=2011, month=12, day=31)
        element = etree.Element('test')
        XmlDocument().to_parent_element(Address, a, ns_test, element)
        element = element[0]
        self.assertEquals(6, len(element.getchildren()))

        r = XmlDocument().from_element(Address, element)

        self.assertEquals(a.street, r.street)
        self.assertEquals(a.city, r.city)
        self.assertEquals(a.zip, r.zip)
        self.assertEquals(a.lattitude, r.lattitude)
        self.assertEquals(a.longitude, r.longitude)
        self.assertEquals(a.since, r.since)

    def test_nested_class(self): # FIXME: this test is incomplete
        p = Person()
        element = etree.Element('test')
        XmlDocument().to_parent_element(Person, p, ns_test, element)
        element = element[0]

        self.assertEquals(None, p.name)
        self.assertEquals(None, p.birthdate)
        self.assertEquals(None, p.age)
        self.assertEquals(None, p.addresses)

    def test_class_array(self):
        peeps = []
        names = ['bob', 'jim', 'peabody', 'mumblesleeves']
        dob = datetime.datetime(1979, 1, 1)
        for name in names:
            a = Person()
            a.name = name
            a.birthdate = dob
            a.age = 27
            peeps.append(a)

        type = Array(Person)
        type.resolve_namespace(type, __name__)

        element = etree.Element('test')

        XmlDocument().to_parent_element(type, peeps, ns_test, element)
        element = element[0]

        self.assertEquals(4, len(element.getchildren()))

        peeps2 = XmlDocument().from_element(type, element)
        for i in range(0, 4):
            self.assertEquals(peeps2[i].name, names[i])
            self.assertEquals(peeps2[i].birthdate, dob)

    def test_class_nested_array(self):
        peeps = []
        names = ['bob', 'jim', 'peabody', 'mumblesleves']

        for name in names:
            a = Person()
            a.name = name
            a.birthdate = datetime.datetime(1979, 1, 1)
            a.age = 27
            a.addresses = []

            for i in range(0, 25):
                addr = Address()
                addr.street = '555 downtown'
                addr.city = 'funkytown'
                a.addresses.append(addr)
            peeps.append(a)

        type = Array(Person)
        type.resolve_namespace(type, __name__)
        element = etree.Element('test')
        XmlDocument().to_parent_element(type, peeps, ns_test, element)
        element = element[0]

        self.assertEquals(4, len(element.getchildren()))

        peeps2 = XmlDocument().from_element(type, element)
        for peep in peeps2:
            self.assertEquals(27, peep.age)
            self.assertEquals(25, len(peep.addresses))
            self.assertEquals('funkytown', peep.addresses[18].city)

    def test_complex_class(self):
        l = Level1()
        l.level2 = Level2()
        l.level2.arg1 = 'abcd'
        l.level2.arg2 = 1.444
        l.level3 = []
        l.level4 = []

        for i in range(0, 100):
            a = Level3()
            a.arg1 = i
            l.level3.append(a)

        for i in range(0, 4):
            a = Level4()
            a.arg1 = str(i)
            l.level4.append(a)

        element = etree.Element('test')
        XmlDocument().to_parent_element(Level1, l, ns_test, element)
        element = element[0]
        l1 = XmlDocument().from_element(Level1, element)

        self.assertEquals(l1.level2.arg1, l.level2.arg1)
        self.assertEquals(l1.level2.arg2, l.level2.arg2)
        self.assertEquals(len(l1.level4), len(l.level4))
        self.assertEquals(100, len(l.level3))

    def test_customize(self):
        class Base(ComplexModel):
            class Attributes(ComplexModel.Attributes):
                prop1 = 3
                prop2 = 6

        Base2 = Base.customize(prop1=4)

        self.assertNotEquals(Base.Attributes.prop1, Base2.Attributes.prop1)
        self.assertEquals(Base.Attributes.prop2, Base2.Attributes.prop2)

        class Derived(Base):
            class Attributes(Base.Attributes):
                prop3 = 9
                prop4 = 12

        Derived2 = Derived.customize(prop1=5, prop3=12)

        self.assertEquals(Base.Attributes.prop1, 3)
        self.assertEquals(Base2.Attributes.prop1, 4)

        self.assertEquals(Derived.Attributes.prop1, 3)
        self.assertEquals(Derived2.Attributes.prop1, 5)

        self.assertNotEquals(Derived.Attributes.prop3, Derived2.Attributes.prop3)
        self.assertEquals(Derived.Attributes.prop4, Derived2.Attributes.prop4)

        Derived3 = Derived.customize(prop3=12)
        Base.prop1 = 4

        # changes made to bases propagate, unless overridden
        self.assertEquals(Derived.Attributes.prop1, Base.Attributes.prop1)
        self.assertNotEquals(Derived2.Attributes.prop1, Base.Attributes.prop1)
        self.assertEquals(Derived3.Attributes.prop1, Base.Attributes.prop1)



class X(ComplexModel):
    __namespace__ = 'tns'
    x = Integer(nillable=True, max_occurs='unbounded')

class Y(X):
    __namespace__ = 'tns'
    y = Integer

class TestIncompleteInput(unittest.TestCase):
    def test_x(self):
        x = X()
        x.x = [1, 2]
        element = etree.Element('test')
        XmlDocument().to_parent_element(X, x, 'tns', element)
        msg = element[0]
        r = XmlDocument().from_element(X, msg)
        self.assertEqual(r.x, [1, 2])

    def test_y_fromxml(self):
        x = X()
        x.x = [1, 2]
        element = etree.Element('test')
        XmlDocument().to_parent_element(X, x, 'tns', element)
        msg = element[0]
        r = XmlDocument().from_element(Y, msg)
        self.assertEqual(r.x, [1, 2])

    def test_y_toxml(self):
        y = Y()
        y.x = [1, 2]
        y.y = 38
        element = etree.Element('test')
        XmlDocument().to_parent_element(Y, y, 'tns', element)
        msg = element[0]
        r = XmlDocument().from_element(Y, msg)


class SisMsg(ComplexModel):
    """Container with metadata for Jiva integration messages
    carried in the MQ payload.
    """
    data_source = String(nillable=False, min_occurs=1, max_occurs=1, max_len=50)
    direction = String(nillable=False, min_occurs=1, max_occurs=1, max_len=50)
    interface_name = String(nillable=False, min_occurs=1, max_occurs=1, max_len=50)
    crt_dt = DateTime(nillable=False)

class EncExtractXs(ComplexModel):
    __min_occurs__ = 1
    __max_occurs__ = 1
    mbr_idn = Integer(nillable=False, min_occurs=1, max_occurs=1, max_len=18)
    enc_idn = Integer(nillable=False, min_occurs=1, max_occurs=1, max_len=18)
    hist_idn = Integer(nillable=False, min_occurs=1, max_occurs=1, max_len=18)


class EncExtractSisMsg(SisMsg):
    """Message indicating a Jiva episode needs to be extracted.

    Desirable API: Will it work?
    >>> msg = XmlDocument().from_element(EncExtractSisMsg, raw_xml)
    >>> msg.body.mbr_idn
    """
    body = EncExtractXs


class TestXmlAttribute(unittest.TestCase):
    def assertIsNotNone(self, obj, msg=None):
        """Stolen from Python 2.7 stdlib."""

        if obj is None:
            standardMsg = 'unexpectedly None'
            self.fail(self._formatMessage(msg, standardMsg))

    def test_add_to_schema(self):
        class CM(ComplexModel):
            i = Integer
            s = String
            a = XmlAttribute(String)

        app = FakeApp()
        app.tns = 'tns'
        CM.resolve_namespace(CM, app.tns)
        interface = Interface(app)
        interface.add_class(CM)

        wsdl = Wsdl11(interface)
        wsdl.build_interface_document('http://a-aaaa.com')
        pref = CM.get_namespace_prefix(interface)
        type_def = wsdl.get_schema_info(pref).types[CM.get_type_name()]
        attribute_def = type_def.find('{%s}attribute' % xml_ns.xsd)
        print(etree.tostring(type_def, pretty_print=True))

        self.assertIsNotNone(attribute_def)
        self.assertEqual(attribute_def.get('name'), 'a')
        self.assertEqual(attribute_def.get('type'), CM.a.type.get_type_name_ns(interface))

    def test_b64_non_attribute(self):
        class PacketNonAttribute(ComplexModel):
            __namespace__ = 'myns'
            Data = ByteArray

        test_string = 'yo test data'
        b64string = b64encode(test_string)

        gg = PacketNonAttribute(Data=test_string)

        element = etree.Element('test')
        Soap11().to_parent_element(PacketNonAttribute, gg, gg.get_namespace(), element)

        element = element[0]
        #print etree.tostring(element, pretty_print=True)
        data = element.find('{%s}Data' % gg.get_namespace()).text
        self.assertEquals(data, b64string)
        s1 = Soap11().from_element(PacketNonAttribute, element)
        assert s1.Data[0] == test_string

    def test_b64_attribute(self):
        class PacketAttribute(ComplexModel):
            __namespace__ = 'myns'
            Data = XmlAttribute(ByteArray, use='required')

        test_string = 'yo test data'
        b64string = b64encode(test_string)
        gg = PacketAttribute(Data=test_string)

        element = etree.Element('test')
        Soap11().to_parent_element(PacketAttribute, gg, gg.get_namespace(), element)

        element = element[0]
        #print etree.tostring(element, pretty_print=True)
        self.assertEquals(element.attrib['Data'], b64string)

        s1 = Soap11().from_element(PacketAttribute, element)
        assert s1.Data[0] == test_string


class TestSimpleTypeRestrictions(unittest.TestCase):
    def test_simple_type_info(self):
        class CM(ComplexModel):
            i = Integer
            s = String

        class CCM(ComplexModel):
            c = CM
            i = Integer
            s = String

        sti = CCM.get_simple_type_info(CCM)
        assert "i" in sti
        assert sti["i"].path == ('i',)
        assert sti["i"].type is Integer
        assert sti["s"].parent is None
        assert "s" in sti
        assert sti["s"].path == ('s',)
        assert sti["s"].type is String
        assert sti["s"].parent is None

        assert "c_i" in sti
        assert sti["c_i"].path == ('c','i')
        assert sti["c_i"].type is Integer
        assert sti["c_i"].parent is CCM
        assert "c_s" in sti
        assert sti["c_s"].path == ('c','s')
        assert sti["c_s"].type is String
        assert sti["c_s"].parent is CCM

    def test_simple_type_info_conflicts(self):
        class CM(ComplexModel):
            i = Integer
            s = String

        class CCM(ComplexModel):
            c = CM
            c_i = Float

        try:
            CCM.get_simple_type_info(CCM)
        except ValueError:
            pass
        else:
            raise Exception("must fail")

class TestFlatDict(unittest.TestCase):
    def test_basic(self):
        class CM(ComplexModel):
            i = Integer
            s = String

        class CCM(ComplexModel):
            c = CM
            i = Integer
            s = String

        val = CCM(i=5, s='a', c=CM(i=7, s='b'))

        d = SimpleDictDocument().object_to_simple_dict(CCM, val)

        assert d['i'] == 5
        assert d['s'] == 'a'
        assert d['c_i'] == 7
        assert d['c_s'] == 'b'

        assert len(d) == 4

    def test_array_not_none(self):
        class CM(ComplexModel):
            i = Integer
            s = String

        class CCM(ComplexModel):
            c = Array(CM)

        val = CCM(c=[CM(i=i, s='b'*(i+1)) for i in range(2)])

        d = SimpleDictDocument().object_to_simple_dict(CCM, val)
        print d

        assert d['c_[0]_i'] == 0
        assert d['c_[0]_s'] == 'b'
        assert d['c_[1]_i'] == 1
        assert d['c_[1]_s'] == 'bb'

        assert len(d) == 4

    def test_array_none(self):
        class CM(ComplexModel):
            i = Integer
            s = String

        class CCM(ComplexModel):
            c = Array(CM)

        val = CCM()

        d = SimpleDictDocument().object_to_simple_dict(CCM, val)
        print d

        assert len(d) == 0

    def test_array_nested(self):
        class CM(ComplexModel):
            i = Array(Integer)

        class CCM(ComplexModel):
            c = Array(CM)

        val = CCM(c=[CM(i=range(i)) for i in range(2, 4) ])

        d = SimpleDictDocument().object_to_simple_dict(CCM, val)
        pprint(d)

        assert d['c_[0]_i_[0]'] == 0
        assert d['c_[0]_i_[1]'] == 1
        assert d['c_[1]_i_[0]'] == 0
        assert d['c_[1]_i_[1]'] == 1
        assert d['c_[1]_i_[2]'] == 2

        assert len(d) == len(range(2)) + len(range(3))


class TestSelfRefence(unittest.TestCase):
    def test_canonical_case(self):
        class TestSelfReference(ComplexModel):
            self_reference = SelfReference

        assert (TestSelfReference._type_info['self_reference'] is TestSelfReference)

        class SoapService(ServiceBase):
            @rpc(_returns=TestSelfReference)
            def view_categories(ctx):
                pass

        Application([SoapService], 'service.soap',
                            in_protocol=ProtocolBase(),
                            out_protocol=ProtocolBase())

    def test_self_referential_array_workaround(self):
        from spyne.util.dictdoc import get_object_as_dict
        class Category(ComplexModel):
            id = Integer(min_occurs=1, max_occurs=1, nillable=False)

        Category._type_info['children'] = Array(Category)

        parent = Category()
        parent.children = [Category(id=0), Category(id=1)]

        d = get_object_as_dict(parent, Category)
        pprint(d)
        assert d['children'][0]['id'] == 0
        assert d['children'][1]['id'] == 1

        class SoapService(ServiceBase):
            @rpc(_returns=Category)
            def view_categories(ctx):
                pass

        Application([SoapService], 'service.soap',
                            in_protocol=ProtocolBase(),
                            out_protocol=ProtocolBase())

    def test_canonical_array(self):
        class Category(ComplexModel):
            id = Integer(min_occurs=1, max_occurs=1, nillable=False)
            children = Array(SelfReference)

        parent = Category()
        parent.children = [Category(id=1), Category(id=2)]

        sr, = Category._type_info['children']._type_info.values()
        assert issubclass(sr, Category)

    def test_array_type_name(self):
        assert Array(String, type_name='punk').__type_name__ == 'punk'

    def test_ctor_kwargs(self):
        class Category(ComplexModel):
            id = Integer(min_occurs=1, max_occurs=1, nillable=False)
            children = Array(Unicode)

        v = Category(id=5, children=['a','b'])

        assert v.id == 5
        assert v.children == ['a', 'b']

    def test_ctor_args(self):
        class Category(ComplexModel):
            id = XmlData(Integer(min_occurs=1, max_occurs=1, nillable=False))
            children = Array(Unicode)

        v = Category(id=5, children=['a','b'])

        assert v.id == 5
        assert v.children == ['a', 'b']

        v = Category(5, children=['a','b'])

        assert v.id == 5
        assert v.children == ['a', 'b']


if __name__ == '__main__':
    unittest.main()
