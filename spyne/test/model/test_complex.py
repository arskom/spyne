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

import pytz
import datetime
import unittest

from pprint import pprint

from lxml import etree

from base64 import b64encode

from spyne import Application
from spyne import rpc
from spyne import mrpc
from spyne import ServiceBase
from spyne.const import xml_ns
from spyne.error import ResourceNotFoundError
from spyne.interface import Interface
from spyne.interface.wsdl import Wsdl11
from spyne.protocol import ProtocolBase
from spyne.protocol.soap import Soap11
from spyne.server.null import NullServer
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

class DeclareOrder_name(ComplexModel.customize(declare_order='name')):
    field3 = Integer()
    field1 = Integer()
    field2 = Integer()

class DeclareOrder_declare(ComplexModel.customize(declare_order='declared')):
    field3 = Integer()
    field1 = Integer()
    field2 = Integer()

class TestComplexModel(unittest.TestCase):
    def test_add_field(self):
        class C(ComplexModel):
            u = Unicode
        C.append_field('i', Integer)
        assert C._type_info['i'] is Integer

    def test_insert_field(self):
        class C(ComplexModel):
            u = Unicode
        C.insert_field(0, 'i', Integer)
        assert C._type_info.keys() == ['i', 'u']

    def test_variants(self):
        class C(ComplexModel):
            u = Unicode
        CC = C.customize(child_attrs=dict(u=dict(min_len=5)))
        print(dict(C.Attributes._variants.items()))
        r, = C.Attributes._variants
        assert r is CC
        assert CC.Attributes.parent_variant is C
        C.append_field('i', Integer)
        assert C._type_info['i'] is Integer
        assert CC._type_info['i'] is Integer

    def test_child_customization(self):
        class C(ComplexModel):
            u = Unicode
        CC = C.customize(child_attrs=dict(u=dict(min_len=5)))
        assert CC._type_info['u'].Attributes.min_len == 5
        assert C._type_info['u'].Attributes.min_len != 5

    def test_delayed_child_customization_append(self):
        class C(ComplexModel):
            u = Unicode
        CC = C.customize(child_attrs=dict(i=dict(ge=5)))
        CC.append_field('i', Integer)
        assert CC._type_info['i'].Attributes.ge == 5
        assert not 'i' in C._type_info

    def test_delayed_child_customization_insert(self):
        class C(ComplexModel):
            u = Unicode
        CC = C.customize(child_attrs=dict(i=dict(ge=5)))
        CC.insert_field(1, 'i', Integer)
        assert CC._type_info['i'].Attributes.ge == 5
        assert not 'i' in C._type_info

    def test_array_customization(self):
        CC = Array(Unicode).customize(
            serializer_attrs=dict(min_len=5), punks='roll',
        )
        assert CC.Attributes.punks == 'roll'
        assert CC._type_info[0].Attributes.min_len == 5

    def test_array_customization_complex(self):
        class C(ComplexModel):
            u = Unicode

        CC = Array(C).customize(
            punks='roll',
            serializer_attrs=dict(bidik=True)
        )
        assert CC.Attributes.punks == 'roll'
        assert CC._type_info[0].Attributes.bidik == True

    def test_simple_class(self):
        a = Address()
        a.street = '123 happy way'
        a.city = 'badtown'
        a.zip = 32
        a.lattitude = 4.3
        a.longitude = 88.0

        element = etree.Element('test')
        XmlDocument().to_parent(None, Address, a, element, ns_test)
        element = element[0]
        self.assertEquals(5, len(element.getchildren()))

        a.since = datetime.datetime(year=2011, month=12, day=31, tzinfo=pytz.utc)
        element = etree.Element('test')
        XmlDocument().to_parent(None, Address, a, element, ns_test)
        element = element[0]
        self.assertEquals(6, len(element.getchildren()))

        r = XmlDocument().from_element(None, Address, element)

        self.assertEquals(a.street, r.street)
        self.assertEquals(a.city, r.city)
        self.assertEquals(a.zip, r.zip)
        self.assertEquals(a.lattitude, r.lattitude)
        self.assertEquals(a.longitude, r.longitude)
        self.assertEquals(a.since, r.since)

    def test_nested_class(self): # FIXME: this test is incomplete
        p = Person()
        element = etree.Element('test')
        XmlDocument().to_parent(None, Person, p, element, ns_test)
        element = element[0]

        self.assertEquals(None, p.name)
        self.assertEquals(None, p.birthdate)
        self.assertEquals(None, p.age)
        self.assertEquals(None, p.addresses)

    def test_class_array(self):
        peeps = []
        names = ['bob', 'jim', 'peabody', 'mumblesleeves']
        dob = datetime.datetime(1979, 1, 1, tzinfo=pytz.utc)
        for name in names:
            a = Person()
            a.name = name
            a.birthdate = dob
            a.age = 27
            peeps.append(a)

        type = Array(Person)
        type.resolve_namespace(type, __name__)

        element = etree.Element('test')

        XmlDocument().to_parent(None, type, peeps, element, ns_test)
        element = element[0]

        self.assertEquals(4, len(element.getchildren()))

        peeps2 = XmlDocument().from_element(None, type, element)
        for i in range(0, 4):
            self.assertEquals(peeps2[i].name, names[i])
            self.assertEquals(peeps2[i].birthdate, dob)

    def test_array_member_name(self):
        print(Array(String, member_name="punk")._type_info)
        assert 'punk' in Array(String, member_name="punk")._type_info

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
        XmlDocument().to_parent(None, type, peeps, element, ns_test)
        element = element[0]

        self.assertEquals(4, len(element.getchildren()))

        peeps2 = XmlDocument().from_element(None, type, element)
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
        XmlDocument().to_parent(None, Level1, l, element, ns_test)
        element = element[0]
        l1 = XmlDocument().from_element(None, Level1, element)

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

    def test_declare_order(self):
        self.assertEquals(["field1", "field2", "field3"], list(DeclareOrder_name._type_info))
        self.assertEquals(["field3", "field1", "field2"], list(DeclareOrder_declare._type_info))


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
        XmlDocument().to_parent(None, X, x, element, 'tns')
        msg = element[0]
        r = XmlDocument().from_element(None, X, msg)
        self.assertEqual(r.x, [1, 2])

    def test_y_fromxml(self):
        x = X()
        x.x = [1, 2]
        element = etree.Element('test')
        XmlDocument().to_parent(None, X, x, element, 'tns')
        msg = element[0]
        r = XmlDocument().from_element(None, Y, msg)
        self.assertEqual(r.x, [1, 2])

    def test_y_toxml(self):
        y = Y()
        y.x = [1, 2]
        y.y = 38
        element = etree.Element('test')
        XmlDocument().to_parent(None, Y, y, element, 'tns')
        msg = element[0]
        r = XmlDocument().from_element(None, Y, msg)


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
        Soap11().to_parent(None, PacketNonAttribute, gg, element, gg.get_namespace())

        element = element[0]
        #print etree.tostring(element, pretty_print=True)
        data = element.find('{%s}Data' % gg.get_namespace()).text
        self.assertEquals(data, b64string)
        s1 = Soap11().from_element(None, PacketNonAttribute, element)
        assert s1.Data[0] == test_string

    def test_b64_attribute(self):
        class PacketAttribute(ComplexModel):
            __namespace__ = 'myns'
            Data = XmlAttribute(ByteArray, use='required')

        test_string = 'yo test data'
        b64string = b64encode(test_string)
        gg = PacketAttribute(Data=test_string)

        element = etree.Element('test')
        Soap11().to_parent(None, PacketAttribute, gg, element, gg.get_namespace())

        element = element[0]
        #print etree.tostring(element, pretty_print=True)
        self.assertEquals(element.attrib['Data'], b64string)

        s1 = Soap11().from_element(None, PacketAttribute, element)
        assert s1.Data[0] == test_string

    def test_customized_type(self):
        class SomeClass(ComplexModel):
            a = XmlAttribute(Integer(ge=4))
        class SomeService(ServiceBase):
            @rpc(SomeClass)
            def some_call(ctx, some_class):
                pass
        app = Application([SomeService], 'some_tns')


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

        pprint(sti)
        assert "i" in sti
        assert sti["i"].path == ('i',)
        assert sti["i"].type is Integer
        assert sti["s"].parent is CCM
        assert "s" in sti
        assert sti["s"].path == ('s',)
        assert sti["s"].type is String
        assert sti["s"].parent is CCM

        assert "c.i" in sti
        assert sti["c.i"].path == ('c','i')
        assert sti["c.i"].type is Integer
        assert sti["c.i"].parent is CM
        assert "c.s" in sti
        assert sti["c.s"].path == ('c','s')
        assert sti["c.s"].type is String
        assert sti["c.s"].parent is CM

    def test_simple_type_info_conflicts(self):
        class CM(ComplexModel):
            i = Integer
            s = String

        class CCM(ComplexModel):
            c = CM
            c_i = Float

        try:
            CCM.get_simple_type_info(CCM, hier_delim='_')
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
        print(d)

        assert d['c[0]_i'] == 0
        assert d['c[0]_s'] == 'b'
        assert d['c[1]_i'] == 1
        assert d['c[1]_s'] == 'bb'

        assert len(d) == 4

    def test_array_none(self):
        class CM(ComplexModel):
            i = Integer
            s = String

        class CCM(ComplexModel):
            c = Array(CM)

        val = CCM()

        d = SimpleDictDocument().object_to_simple_dict(CCM, val)
        print(d)

        assert len(d) == 0

    def test_array_nested(self):
        class CM(ComplexModel):
            i = Array(Integer)

        class CCM(ComplexModel):
            c = Array(CM)

        val = CCM(c=[CM(i=range(i)) for i in range(2, 4)])

        d = SimpleDictDocument().object_to_simple_dict(CCM, val)
        pprint(d)

        assert d['c[0]_i'] == [0,1]
        assert d['c[1]_i'] == [0,1,2]

        assert len(d) == 2


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

    def test_ctor_args_2(self):
        class Category(ComplexModel):
            children = Array(Unicode)

        class BetterCategory(Category):
            sub_category = Unicode

        v = BetterCategory(children=['a','b'], sub_category='aaa')

        assert v.children == ['a', 'b']
        assert v.sub_category == 'aaa'


class TestMemberRpc(unittest.TestCase):
    def test_simple(self):
        class SomeComplexModel(ComplexModel):
            @mrpc()
            def put(self, ctx):
                return "PUNK!!!"

        methods = SomeComplexModel.Attributes.methods
        print(methods)
        assert 'put' in methods

    def test_simple_customize(self):
        class SomeComplexModel(ComplexModel):
            @mrpc()
            def put(self, ctx):
                return "PUNK!!!"

        methods = SomeComplexModel.customize(zart='zurt').Attributes.methods
        print(methods)
        assert 'put' in methods

    def test_simple_with_fields(self):
        class SomeComplexModel(ComplexModel):
            a = Integer
            @mrpc()
            def put(self, ctx):
                return "PUNK!!!"

        methods = SomeComplexModel.Attributes.methods
        print(methods)
        assert 'put' in methods

    def test_simple_with_explicit_fields(self):
        class SomeComplexModel(ComplexModel):
            _type_info = [('a', Integer)]
            @mrpc()
            def put(self, ctx):
                return "PUNK!!!"

        methods = SomeComplexModel.Attributes.methods
        print(methods)
        assert 'put' in methods

    def test_native_call(self):
        v = 'whatever'

        class SomeComplexModel(ComplexModel):
            @mrpc()
            def put(self, ctx):
                return v

        assert SomeComplexModel().put(None) == v

    def test_interface(self):
        class SomeComplexModel(ComplexModel):
            @mrpc()
            def member_method(self, ctx):
                pass

        methods = SomeComplexModel.Attributes.methods
        print(methods)
        assert 'member_method' in methods

        class SomeService(ServiceBase):
            @rpc(_returns=SomeComplexModel)
            def service_method(ctx):
                return SomeComplexModel()

        app = Application([SomeService], 'some_ns')

        mmm = __name__ + '.SomeComplexModel.member_method'
        assert mmm in app.interface.method_id_map

    def test_interface_mult(self):
        class SomeComplexModel(ComplexModel):
            @mrpc()
            def member_method(self, ctx):
                pass

        methods = SomeComplexModel.Attributes.methods
        print(methods)
        assert 'member_method' in methods

        class SomeService(ServiceBase):
            @rpc(_returns=SomeComplexModel)
            def service_method(ctx):
                return SomeComplexModel()

            @rpc(_returns=SomeComplexModel.customize(type_name='zon'))
            def service_method_2(ctx):
                return SomeComplexModel()

        app = Application([SomeService], 'some_ns')

        mmm = __name__ + '.SomeComplexModel.member_method'
        assert mmm in app.interface.method_id_map

    def test_remote_call_error(self):
        from spyne import mrpc
        v = 'deger'

        class SomeComplexModel(ComplexModel):
            @mrpc(_returns=SelfReference)
            def put(self, ctx):
                return v

        class SomeService(ServiceBase):
            @rpc(_returns=SomeComplexModel)
            def get(ctx):
                return SomeComplexModel()

        null = NullServer(Application([SomeService], tns='some_tns'))

        try:
            null.service.put()
        except ResourceNotFoundError:
            pass
        else:
            raise Exception("Must fail with: \"Requested resource "
                "'{spyne.test.model.test_complex}SomeComplexModel' not found\"")

    def test_signature(self):
        class SomeComplexModel(ComplexModel):
            @mrpc()
            def member_method(self, ctx):
                pass

        methods = SomeComplexModel.Attributes.methods

        # we use __orig__ because implicit classes are .customize(validate_freq=False)'d
        assert methods['member_method'].in_message._type_info[0].__orig__ is SomeComplexModel

    def test_self_reference(self):
        from spyne import mrpc

        class SomeComplexModel(ComplexModel):
            @mrpc(_returns=SelfReference)
            def method(self, ctx):
                pass

        methods = SomeComplexModel.Attributes.methods
        assert methods['method'].out_message._type_info[0] is SomeComplexModel

    def test_remote_call_success(self):
        from spyne import mrpc

        class SomeComplexModel(ComplexModel):
            i = Integer
            @mrpc(_returns=SelfReference)
            def echo(self, ctx):
                return self

        class SomeService(ServiceBase):
            @rpc(_returns=SomeComplexModel)
            def get(ctx):
                return SomeComplexModel()

        null = NullServer(Application([SomeService], tns='some_tns'))
        v = SomeComplexModel(i=5)
        assert null.service.echo(v) is v


if __name__ == '__main__':
    unittest.main()
