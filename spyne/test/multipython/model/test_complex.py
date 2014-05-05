# coding: utf-8
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


"""Complex model tests runnable on different Python implementations."""

import unittest

from spyne.model.complex import (ComplexModel, ComplexModelMeta,
                                 ComplexModelBase, Array)
from spyne.model.primitive import Unicode, Integer, String
from spyne.util.six import add_metaclass


class DeclareOrder_declare(ComplexModel.customize(declare_order='declared')):
    field3 = Integer
    field1 = Integer
    field2 = Integer


class MyComplexModelMeta(ComplexModelMeta):
    """Custom complex model metaclass."""

    def __new__(mcs, name, bases, attrs):
        attrs['new_field'] = Unicode
        attrs['field1'] = Unicode
        new_cls = super(MyComplexModelMeta, mcs).__new__(mcs, name, bases,
                                                         attrs)
        return new_cls


@add_metaclass(MyComplexModelMeta)
class MyComplexModel(ComplexModelBase):
    """Custom complex model class."""
    class Attributes(ComplexModelBase.Attributes):
        declare_order = 'declared'


class MyModelWithDeclaredOrder(MyComplexModel):
    """Test model for complex model with custom metaclass."""
    class Attributes(MyComplexModel.Attributes):
        declare_order = 'declared'

    field3 = Integer
    field1 = Integer
    field2 = Integer


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

    def test_array_member_name(self):
        print(Array(String, member_name="punk")._type_info)
        assert 'punk' in Array(String, member_name="punk")._type_info

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
        self.assertEquals(["field3", "field1", "field2"],
                          list(DeclareOrder_declare._type_info))
        self.assertEquals(["field3", "field1", "field2", "new_field"],
                          list(MyModelWithDeclaredOrder._type_info))


if __name__ == '__main__':
    import sys
    sys.exit(unittest.main())
