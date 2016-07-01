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

from __future__ import print_function

import pytz
import datetime
import unittest

from pprint import pprint

from lxml import etree

from base64 import b64encode
from decimal import Decimal as D

from spyne import Application, rpc, mrpc, ServiceBase, ByteArray, Array, \
    ComplexModel, SelfReference, XmlData, XmlAttribute, Unicode, DateTime, \
    Float, Integer, String
from spyne.const import xml_ns
from spyne.error import ResourceNotFoundError
from spyne.interface import Interface
from spyne.interface.wsdl import Wsdl11
from spyne.protocol import ProtocolBase
from spyne.protocol.soap import Soap11
from spyne.server.null import NullServer

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

        arr = Array(Person)
        arr.resolve_namespace(arr, __name__)
        element = etree.Element('test')
        XmlDocument().to_parent(None, arr, peeps, element, ns_test)
        element = element[0]

        self.assertEquals(4, len(element.getchildren()))

        peeps2 = XmlDocument().from_element(None, arr, element)
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

    def test_serialization_instance_on_subclass(self):
        test_values = {
            'x': [1, 2],
            'y': 38
        }
        instance = Y.get_serialization_instance(test_values)

        self.assertEqual(instance.x, [1, 2])
        self.assertEqual(instance.y, 38)


class SisMsg(ComplexModel):
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
        print(etree.tostring(element, pretty_print=True))
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
        assert d['c.i'] == 7
        assert d['c.s'] == 'b'

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

        assert d['c[0].i'] == 0
        assert d['c[0].s'] == 'b'
        assert d['c[1].i'] == 1
        assert d['c[1].s'] == 'bb'

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

        assert d['c[0].i'] == [0, 1]
        assert d['c[1].i'] == [0, 1, 2]

        assert len(d) == 2

    def test_array_nonwrapped(self):
        i = Array(Integer, wrapped=False)

        assert issubclass(i, Integer), i
        assert i.Attributes.max_occurs == D('infinity')


class TestSelfRefence(unittest.TestCase):
    def test_canonical_case(self):
        class TestSelfReference(ComplexModel):
            self_reference = SelfReference

        c = TestSelfReference._type_info['self_reference']
        c = c.__orig__ or c

        assert c is TestSelfReference

        class SoapService(ServiceBase):
            @rpc(_returns=TestSelfReference)
            def view_categories(ctx):
                pass

        Application([SoapService], 'service.soap')

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

        mmm = __name__ + '.SomeComplexModel.SomeComplexModel.member_method'
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

        mmm = __name__ + '.SomeComplexModel.SomeComplexModel.member_method'
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
        assert null.service['SomeComplexModel.SomeComplexModel.echo'](v) is v

    def test_order(self):
        class CM(ComplexModel):
            _type_info = [
                ('a', Integer),
                ('c', Integer(order=0))
            ]

        assert CM._type_info.keys() == ['c', 'a']


class TestDoc(unittest.TestCase):
    def test_parent_doc(self):
        class SomeComplexModel(ComplexModel):
            """Some docstring"""
            some_field = Unicode
            class Annotations(ComplexModel.Annotations):
                __use_parent_doc__ = True
        assert "Some docstring" == SomeComplexModel.get_documentation()

    def test_annotation(self):
        class SomeComplexModel(ComplexModel):
            """Some docstring"""
            class Annotations(ComplexModel.Annotations):
                doc = "Some annotations"

            some_field = Unicode
        assert "Some annotations" == SomeComplexModel.get_documentation()

    def test_no_parent_doc(self):
        class SomeComplexModel(ComplexModel):
            """Some docstring"""
            class Annotations(ComplexModel.Annotations):
                __use_parent_doc__ = False

            some_field = Unicode
        assert "" == SomeComplexModel.get_documentation()

    def test_parent_doc_customize(self):
        """Check that we keep the documentation when we use customize"""
        class SomeComplexModel(ComplexModel):
            """Some docstring"""
            some_field = Unicode
            class Annotations(ComplexModel.Annotations):
                __use_parent_doc__ = True
        assert "Some docstring" == SomeComplexModel.customize().get_documentation()


class TestCustomize(unittest.TestCase):
    def test_base_class(self):
        class A(ComplexModel):
            s = Unicode

        assert A.customize().__extends__ is None

        class B(A):
            i = Integer

        assert B.__orig__ is None

        B2 = B.customize()

        assert B2.__orig__ is B
        assert B2.__extends__ is A

        B3 = B2.customize()

        assert B3.__orig__ is B
        assert B3.__extends__ is A

    def test_noop(self):
        class A(ComplexModel):
            s = Unicode

        assert A.get_flat_type_info(A)['s'].Attributes.max_len == D('inf')

    def test_cust_simple(self):
        # simple types are different from complex ones for __extends__ handling.
        # simple types set __orig__ and __extends__ on customization.
        # complex types set __orig__ but not extend.
        # for complex types, __extend__ is set only on explicit inheritance

        t = Unicode(max_len=10)

        assert t.Attributes.max_len == 10
        assert t.__extends__ is Unicode
        assert t.__orig__ is Unicode

    def test_cust_simple_again(self):
        t = Unicode(max_len=10)
        t2 = t(min_len=5)

        assert t2.Attributes.max_len == 10
        assert t2.Attributes.min_len == 5
        assert t2.__extends__ is t
        assert t2.__orig__ is Unicode

    def test_cust_complex(self):
        class A(ComplexModel):
            s = Unicode

        A2 = A.customize(
            child_attrs=dict(
                s=dict(
                    max_len=10
                )
            )
        )

        assert A2.get_flat_type_info(A2)['s'].Attributes.max_len == 10

    def test_cust_base_class(self):
        class A(ComplexModel):
            s = Unicode

        class B(A):
            i = Integer

        B2 = B.customize(
            child_attrs=dict(
                s=dict(
                    max_len=10,
                ),
            ),
        )

        assert B2.get_flat_type_info(B2)['s'].Attributes.max_len == 10

    def test_cust_again_base_class(self):
        class A(ComplexModel):
            s = Unicode

        A2 = A.customize()
        try:
            class B(A2):
                i = Integer
        except AssertionError:
            pass
        else:
            raise Exception("must fail")

    def test_cust_array(self):
        A = Array(Unicode)

        assert A.__orig__ is Array
        assert A.__extends__ is None
        assert issubclass(A, Array)

    def test_cust_array_again(self):
        A = Array(Unicode)

        A = A.customize(foo='bar')

        assert A.Attributes.foo == 'bar'
        assert A.__orig__ is Array
        assert A.__extends__ is None
        assert issubclass(A, Array)

    def test_cust_array_serializer(self):
        A = Array(Unicode)

        A = A.customize(
            serializer_attrs=dict(
                max_len=10,
            ),
        )

        serializer, = A._type_info.values()

        assert serializer.Attributes.max_len == 10
        assert serializer.__orig__ is Unicode
        assert issubclass(serializer, Unicode)

    def test_cust_sub_array(self):
        """vanilla class is passed as base"""
        class A(ComplexModel):
            s = Array(Unicode)

        d = dict(
            child_attrs=dict(
                s=dict(
                    serializer_attrs=dict(
                        max_len=10,
                    ),
                ),
            ),
        )

        A2 = A.customize(**d)

        ser, = A2._type_info['s']._type_info.values()
        assert ser.Attributes.max_len == 10

        class B(A):
            i = Integer

        B2 = B.customize(**d)

        b2_fti = B2.get_flat_type_info(B2)
        ser, = b2_fti['s']._type_info.values()

        assert ser.Attributes.max_len == 10

    def test_cust_side_effect(self):
        class A(ComplexModel):
            s = Unicode
            i = Integer

        class B(A):
            d = DateTime

        B2 = B.customize(child_attrs=dict(s=dict(max_len=10)))
        assert B2.get_flat_type_info(B2)['s'].Attributes.max_len == 10

        B3 = B2.customize(child_attrs=dict(d=dict(format="%y")))
        assert B3.get_flat_type_info(B3)['s'].Attributes.max_len == 10


    def test_complex_type_name_clashes(self):
        class TestComplexModel(ComplexModel):
            attr1 = String

        TestComplexModel1 = TestComplexModel

        class TestComplexModel(ComplexModel):
            attr2 = String

        TestComplexModel2 = TestComplexModel

        class TestService(ServiceBase):
            @rpc(TestComplexModel1)
            def test1(ctx, obj):
                pass

            @rpc(TestComplexModel2)
            def test2(ctx, obj):
                pass

        try:
            Application([TestService], 'tns')
        except Exception as e:
            print(e)
        else:
            raise Exception("must fail with: "
                "ValueError: classes "
                    "<class 'spyne.test.model.test_complex.TestComplexModel'> "
                    "and "
                    "<class 'spyne.test.model.test_complex.TestComplexModel'> "
                    "have conflicting names.")


if __name__ == '__main__':
    unittest.main()
