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
logging.basicConfig(level=logging.DEBUG)

from getpass import getuser
PSQL_CONN_STR = 'postgres://postgres:@localhost:5432/spyne_test_%s' % getuser()

import unittest
import sqlalchemy

from sqlalchemy import create_engine
from sqlalchemy import MetaData
from sqlalchemy import Column
from sqlalchemy import Table
from sqlalchemy.exc import IntegrityError

from sqlalchemy.orm import mapper
from sqlalchemy.orm import sessionmaker

from spyne.model import XmlAttribute, Decimal
from spyne.model import XmlData
from spyne.model import ComplexModel
from spyne.model import Array
from spyne.model import Integer32
from spyne.model import Unicode
from spyne.model import Integer
from spyne.model import Enum
from spyne.model import TTableModel

from spyne.model.complex import xml
from spyne.model.complex import table

TableModel = TTableModel()

class TestSqlAlchemySchema(unittest.TestCase):
    def setUp(self):
        logging.getLogger('sqlalchemy').setLevel(logging.DEBUG)

        self.engine = create_engine('sqlite:///:memory:')
        self.session = sessionmaker(bind=self.engine)()
        self.metadata = TableModel.Attributes.sqla_metadata = MetaData()
        self.metadata.bind = self.engine

    def test_schema(self):
        class SomeClass(TableModel):
            __tablename__ = 'some_class'
            __table_args__ = {"sqlite_autoincrement": True}

            id = Integer32(primary_key=True, autoincrement=False)
            s = Unicode(64, unique=True)
            i = Integer32(64, index=True)

        t = SomeClass.__table__
        self.metadata.create_all() # not needed, just nice to see.

        assert t.c.id.primary_key == True
        assert t.c.id.autoincrement == False
        indexes = list(t.indexes)
        indexes.sort(key=lambda idx: idx.columns)
        for idx in indexes:
            assert 'i' in idx.columns or 's' in idx.columns
            if 's' in idx.columns:
                assert idx.unique

    def test_nested_sql(self):
        class SomeOtherClass(TableModel):
            __tablename__ = 'some_other_class'
            __table_args__ = {"sqlite_autoincrement": True}

            id = Integer32(primary_key=True)
            s = Unicode(64)

        class SomeClass(TableModel):
            __tablename__ = 'some_class'
            __table_args__ = (
                {"sqlite_autoincrement": True},
            )

            id = Integer32(primary_key=True)
            o = SomeOtherClass.customize(store_as='table')

        self.metadata.create_all()

        soc = SomeOtherClass(s='ehe')
        sc = SomeClass(o=soc)

        self.session.add(sc)
        self.session.commit()
        self.session.close()

        sc_db = self.session.query(SomeClass).get(1)
        print sc_db
        assert sc_db.o.s == 'ehe'
        assert sc_db.o_id == 1

        sc_db.o = None
        self.session.commit()
        self.session.close()

        sc_db = self.session.query(SomeClass).get(1)
        assert sc_db.o == None
        assert sc_db.o_id == None

    def test_nested_sql_array_as_table(self):
        class SomeOtherClass(TableModel):
            __tablename__ = 'some_other_class'
            __table_args__ = {"sqlite_autoincrement": True}

            id = Integer32(primary_key=True)
            s = Unicode(64)

        class SomeClass(TableModel):
            __tablename__ = 'some_class'
            __table_args__ = {"sqlite_autoincrement": True}

            id = Integer32(primary_key=True)
            others = Array(SomeOtherClass, store_as='table')

        self.metadata.create_all()

        soc1 = SomeOtherClass(s='ehe1')
        soc2 = SomeOtherClass(s='ehe2')
        sc = SomeClass(others=[soc1, soc2])

        self.session.add(sc)
        self.session.commit()
        self.session.close()

        sc_db = self.session.query(SomeClass).get(1)

        assert sc_db.others[0].s == 'ehe1'
        assert sc_db.others[1].s == 'ehe2'

        self.session.close()

    def test_nested_sql_array_as_multi_table(self):
        class SomeOtherClass(TableModel):
            __tablename__ = 'some_other_class'
            __table_args__ = {"sqlite_autoincrement": True}

            id = Integer32(primary_key=True)
            s = Unicode(64)

        class SomeClass(TableModel):
            __tablename__ = 'some_class'
            __table_args__ = {"sqlite_autoincrement": True}

            id = Integer32(primary_key=True)
            others = Array(SomeOtherClass, store_as=table(multi=True))

        self.metadata.create_all()

        soc1 = SomeOtherClass(s='ehe1')
        soc2 = SomeOtherClass(s='ehe2')
        sc = SomeClass(others=[soc1, soc2])

        self.session.add(sc)
        self.session.commit()
        self.session.close()

        sc_db = self.session.query(SomeClass).get(1)

        assert sc_db.others[0].s == 'ehe1'
        assert sc_db.others[1].s == 'ehe2'

        self.session.close()

    def test_nested_sql_array_as_multi_table_with_backref(self):
        class SomeOtherClass(TableModel):
            __tablename__ = 'some_other_class'
            __table_args__ = {"sqlite_autoincrement": True}

            id = Integer32(primary_key=True)
            s = Unicode(64)

        class SomeClass(TableModel):
            __tablename__ = 'some_class'
            __table_args__ = {"sqlite_autoincrement": True}

            id = Integer32(primary_key=True)
            others = Array(SomeOtherClass, store_as=table(multi=True, backref='some_classes'))

        self.metadata.create_all()

        soc1 = SomeOtherClass(s='ehe1')
        soc2 = SomeOtherClass(s='ehe2')
        sc = SomeClass(others=[soc1, soc2])

        self.session.add(sc)
        self.session.commit()
        self.session.close()

        soc_db = self.session.query(SomeOtherClass).all()

        assert soc_db[0].some_classes[0].id == 1
        assert soc_db[1].some_classes[0].id == 1

        self.session.close()

    def test_nested_sql_array_as_xml(self):
        class SomeOtherClass(ComplexModel):
            id = Integer32
            s = Unicode(64)

        class SomeClass(TableModel):
            __tablename__ = 'some_class'
            __table_args__ = {"sqlite_autoincrement": True}

            id = Integer32(primary_key=True)
            others = Array(SomeOtherClass, store_as='xml')

        self.metadata.create_all()

        soc1 = SomeOtherClass(s='ehe1')
        soc2 = SomeOtherClass(s='ehe2')
        sc = SomeClass(others=[soc1, soc2])

        self.session.add(sc)
        self.session.commit()
        self.session.close()

        sc_db = self.session.query(SomeClass).get(1)

        assert sc_db.others[0].s == 'ehe1'
        assert sc_db.others[1].s == 'ehe2'

        self.session.close()

    def test_nested_sql_array_as_xml_no_ns(self):
        class SomeOtherClass(ComplexModel):
            id = Integer32
            s = Unicode(64)

        class SomeClass(TableModel):
            __tablename__ = 'some_class'
            __table_args__ = {"sqlite_autoincrement": True}

            id = Integer32(primary_key=True)
            others = Array(SomeOtherClass, store_as=xml(no_ns=True))

        self.metadata.create_all()

        soc1 = SomeOtherClass(s='ehe1')
        soc2 = SomeOtherClass(s='ehe2')
        sc = SomeClass(others=[soc1, soc2])

        self.session.add(sc)
        self.session.commit()
        self.session.close()

        sc_xml = self.session.connection().execute("select others from some_class") \
                                                               .fetchall()[0][0]

        from lxml import etree
        assert etree.fromstring(sc_xml).tag == 'SomeOtherClassArray'

        self.session.close()

    def test_inheritance(self):
        class SomeOtherClass(TableModel):
            __tablename__ = 'some_other_class'
            __table_args__ = {"sqlite_autoincrement": True}
            id = Integer32(primary_key=True)
            s = Unicode(64)

        class SomeClass(SomeOtherClass):
            numbers = Array(Integer32).store_as(xml(no_ns=True, root_tag='a'))

        self.metadata.create_all()

        sc = SomeClass(id=5, s='s', numbers=[1,2,3,4])

        self.session.add(sc)
        self.session.commit()
        self.session.close()

        sc_db = self.session.query(SomeClass).get(5)
        assert sc_db.numbers == [1, 2, 3, 4]
        self.session.close()

        sc_db = self.session.query(SomeOtherClass).get(5)
        assert sc_db.id == 5
        try:
            sc_db.numbers
        except AttributeError:
            pass
        else:
            raise Exception("must fail")

        self.session.close()

    def test_sqlalchemy_inheritance(self):
        # no spyne code is involved here.
        # this is just to test test the sqlalchemy behavior that we rely on.

        class Employee(object):
            def __init__(self, name):
                self.name = name
            def __repr__(self):
                return self.__class__.__name__ + " " + self.name

        class Manager(Employee):
            def __init__(self, name, manager_data):
                self.name = name
                self.manager_data = manager_data
            def __repr__(self):
                return (
                    self.__class__.__name__ + " " +
                    self.name + " " +  self.manager_data
                )

        class Engineer(Employee):
            def __init__(self, name, engineer_info):
                self.name = name
                self.engineer_info = engineer_info
            def __repr__(self):
                return (
                    self.__class__.__name__ + " " +
                    self.name + " " +  self.engineer_info
                )

        employees_table = Table('employees', self.metadata,
            Column('employee_id', sqlalchemy.Integer, primary_key=True),
            Column('name', sqlalchemy.String(50)),
            Column('manager_data', sqlalchemy.String(50)),
            Column('engineer_info', sqlalchemy.String(50)),
            Column('type', sqlalchemy.String(20), nullable=False)
        )

        employee_mapper = mapper(Employee, employees_table,
            polymorphic_on=employees_table.c.type, polymorphic_identity='employee')
        manager_mapper = mapper(Manager, inherits=employee_mapper,
                                            polymorphic_identity='manager')
        engineer_mapper = mapper(Engineer, inherits=employee_mapper,
                                            polymorphic_identity='engineer')

        self.metadata.create_all()

        manager = Manager('name', 'data')
        self.session.add(manager)
        self.session.commit()
        self.session.close()

        assert self.session.query(Employee).with_polymorphic('*').get(1).type == 'manager'

    def test_inheritance_polymorphic_with_non_nullables_in_subclasses(self):
        class SomeOtherClass(TableModel):
            __tablename__ = 'some_other_class'
            __table_args__ = {"sqlite_autoincrement": True} # this is sqlite-specific
            __mapper_args__ = (
                (),
                {'polymorphic_on': 't', 'polymorphic_identity': 1},
            )

            id = Integer32(primary_key=True)
            t = Integer32(nillable=False)
            s = Unicode(64, nillable=False)

        class SomeClass(SomeOtherClass):
            __mapper_args__ = (
                (),
                {'polymorphic_identity': 2},
            )

            i = Integer(nillable=False)

        self.metadata.create_all()

        assert SomeOtherClass.__table__.c.s.nullable == False

        # this should be nullable to let other classes be added.
        # spyne still checks this constraint when doing input validation.
        # spyne should generate a constraint to check this at database level as
        # well.
        assert SomeOtherClass.__table__.c.i.nullable == True

        soc = SomeOtherClass(s='s')
        self.session.add(soc)
        self.session.commit()
        soc_id = soc.id

        try:
            sc = SomeClass(i=5)
            self.session.add(sc)
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
        else:
            raise Exception("Must fail with IntegrityError.")

        sc2 = SomeClass(s='s') # this won't fail. should it?
        self.session.add(sc2)
        self.session.commit()

        self.session.expunge_all()

        assert self.session.query(SomeOtherClass).with_polymorphic('*').get(soc_id).t == 1
        self.session.close()

    def test_inheritance_polymorphic(self):
        class SomeOtherClass(TableModel):
            __tablename__ = 'some_class'
            __table_args__ = {"sqlite_autoincrement": True} # this is sqlite-specific
            __mapper_args__ = {'polymorphic_on': 't', 'polymorphic_identity': 1}

            id = Integer32(primary_key=True)
            s = Unicode(64)
            t = Integer32(nillable=False)

        class SomeClass(SomeOtherClass):
            __mapper_args__ = {'polymorphic_identity': 2}
            numbers = Array(Integer32).store_as(xml(no_ns=True, root_tag='a'))

        self.metadata.create_all()

        sc = SomeClass(id=5, s='s', numbers=[1,2,3,4])

        self.session.add(sc)
        self.session.commit()
        self.session.close()

        assert self.session.query(SomeOtherClass).with_polymorphic('*').get(5).t == 2
        self.session.close()

    def test_nested_sql_array_as_json(self):
        class SomeOtherClass(ComplexModel):
            id = Integer32
            s = Unicode(64)

        class SomeClass(TableModel):
            __tablename__ = 'some_class'
            __table_args__ = {"sqlite_autoincrement": True}

            id = Integer32(primary_key=True)
            others = Array(SomeOtherClass, store_as='json')

        self.metadata.create_all()

        soc1 = SomeOtherClass(s='ehe1')
        soc2 = SomeOtherClass(s='ehe2')
        sc = SomeClass(others=[soc1, soc2])

        self.session.add(sc)
        self.session.commit()
        self.session.close()

        sc_db = self.session.query(SomeClass).get(1)

        assert sc_db.others[0].s == 'ehe1'
        assert sc_db.others[1].s == 'ehe2'

        self.session.close()

    def test_modifiers(self):
        class SomeClass(TableModel):
            __tablename__ = 'some_class'
            __table_args__ = {"sqlite_autoincrement": True}

            i = XmlAttribute(Integer32(pk=True))
            s = XmlData(Unicode(64))

        self.metadata.create_all()
        self.session.add(SomeClass(s='s'))
        self.session.commit()
        self.session.expunge_all()

        ret = self.session.query(SomeClass).get(1)
        assert ret.i == 1 # redundant
        assert ret.s == 's'

    def test_default_ctor(self):
        class SomeOtherClass(ComplexModel):
            id = Integer32
            s = Unicode(64)

        class SomeClass(TableModel):
            __tablename__ = 'some_class'
            __table_args__ = {"sqlite_autoincrement": True}

            id = Integer32(primary_key=True)
            others = Array(SomeOtherClass, store_as='json')
            f = Unicode(32, default='uuu')

        self.metadata.create_all()
        self.session.add(SomeClass())
        self.session.commit()
        self.session.expunge_all()

        assert self.session.query(SomeClass).get(1).f == 'uuu'

    def test_default_ctor_with_sql_relationship(self):
        class SomeOtherClass(TableModel):
            __tablename__ = 'some_other_class'
            __table_args__ = {"sqlite_autoincrement": True}

            id = Integer32(primary_key=True)
            s = Unicode(64)

        class SomeClass(TableModel):
            __tablename__ = 'some_class'
            __table_args__ = (
                {"sqlite_autoincrement": True},
            )

            id = Integer32(primary_key=True)
            o = SomeOtherClass.customize(store_as='table')

        self.metadata.create_all()
        self.session.add(SomeClass())
        self.session.commit()

    def test_store_as_index(self):
        class SomeOtherClass(TableModel):
            __tablename__ = 'some_other_class'
            __table_args__ = {"sqlite_autoincrement": True}

            id = Integer32(primary_key=True)
            s = Unicode(64)

        class SomeClass(TableModel):
            __tablename__ = 'some_class'
            __table_args__ = (
                {"sqlite_autoincrement": True},
            )

            id = Integer32(primary_key=True)
            o = SomeOtherClass.customize(store_as='table', index='btree')

        self.metadata.create_all()
        idx, = SomeClass.__table__.indexes
        assert 'o_id' in idx.columns

    def test_scalar_collection(self):
        class SomeClass(TableModel):
            __tablename__ = 'some_class'

            id = Integer32(primary_key=True)
            values = Array(Unicode).store_as('table')

        self.metadata.create_all()

        self.session.add(SomeClass(id=1, values=['a', 'b', 'c']))
        self.session.commit()
        sc = self.session.query(SomeClass).get(1)
        assert sc.values == ['a', 'b', 'c']
        del sc

        sc = self.session.query(SomeClass).get(1)
        sc.values.append('d')
        self.session.commit()
        del sc
        sc = self.session.query(SomeClass).get(1)
        assert sc.values == ['a', 'b', 'c', 'd']

        sc = self.session.query(SomeClass).get(1)
        sc.values = sc.values[1:]
        self.session.commit()
        del sc
        sc = self.session.query(SomeClass).get(1)
        assert sc.values == ['b', 'c', 'd']

    def test_multiple_fk(self):
        class SomeChildClass(TableModel):
            __tablename__ = 'some_child_class'

            id = Integer32(primary_key=True)
            s = Unicode(64)
            i = Integer32

        class SomeClass(TableModel):
            __tablename__ = 'some_class'

            id = Integer32(primary_key=True)
            children = Array(SomeChildClass).store_as('table')
            mirror = SomeChildClass.store_as('table')

        self.metadata.create_all()

        children = [
            SomeChildClass(s='p', i=600),
            SomeChildClass(s='|', i=10),
            SomeChildClass(s='q', i=9),
        ]

        sc = SomeClass(children=children)
        self.session.add(sc)
        self.session.flush()
        sc.mirror = children[1]
        self.session.commit()
        del sc

        sc = self.session.query(SomeClass).get(1)
        assert ''.join([scc.s for scc in sc.children]) == 'p|q'
        assert     sum([scc.i for scc in sc.children]) ==  619

    def test_reflection(self):
        class SomeChildClass(TableModel):
            __tablename__ = 'some_child_class'

            id = Integer32(primary_key=True)
            s = Unicode(64)
            i = Integer32

        class SomeClass(TableModel):
            __tablename__ = 'some_class'

            id = Integer32(primary_key=True)
            children = Array(SomeChildClass).store_as('xml')
            mirror = SomeChildClass.store_as('json')

        metadata2 = MetaData()
        metadata2.bind = self.engine
        metadata2.reflect()

    def _test_sqlalchemy_remapping(self):
        class SomeTable(TableModel):
            __tablename__ = 'some_table'
            id = Integer32(pk=True)
            i = Integer32
            s = Unicode(32)

        class SomeTableSubset(TableModel):
            __table__ = SomeTable.__table__

            id = Integer32(pk=True) # sqla session doesn't work without pk
            i = Integer32

        class SomeTableOtherSubset(TableModel):
            __table__ = SomeTable.__table__
            _type_info = [(k,v) for k, v in SomeTable._type_info.items() if k in ('id', 's')]

        self.session.add(SomeTable(id=1,i=2,s='s'))
        self.session.commit()

        st = self.session.query(SomeTableSubset).get(1)
        sts = self.session.query(SomeTableOtherSubset).get(1)
        stos = self.session.query(SomeTableSubset).get(1)

        sts.i = 3
        sts.s = 'ss' # will not be flushed to db
        self.session.commit()

        assert st.s == 's'
        assert stos.i == 3

    def test_add_field_complex_existing_column(self):
        class C(TableModel):
            __tablename__ = "c"
            u = Unicode(pk=True)

        class D(TableModel):
            __tablename__ = "d"
            d = Integer32(pk=True)
            c = C.store_as('table')

        C.append_field('d', D.store_as('table'))
        assert C.Attributes.sqla_mapper.get_property('d').argument is D

    def test_add_field_complex_existing_column_2(self):
        class C(TableModel):
            __tablename__ = "c"
            id = Integer32(5, pk=True)

        # c already also produces c_id. this is undefined behaviour, one of them
        # gets ignored, whichever comes first.
        class D(TableModel):
            __tablename__ = "d"
            id = Integer32(pk=True)
            c = C.store_as('table')
            c_id = Integer32(15)

    def test_add_field_complex_new_column(self):
        class C(TableModel):
            __tablename__ = "c"
            u = Unicode(pk=True)

        class D(TableModel):
            __tablename__ = "d"
            id = Integer32(pk=True)

        C.append_field('d', D.store_as('table'))
        assert C.Attributes.sqla_mapper.get_property('d').argument is D
        assert isinstance(C.Attributes.sqla_table.c['d_id'].type, sqlalchemy.Integer)

    def test_add_field_array(self):
        class C(TableModel):
            __tablename__ = "c"
            id = Integer32(pk=True)

        class D(TableModel):
            __tablename__ = "d"
            id = Integer32(pk=True)

        C.append_field('d', Array(D).store_as('table'))
        assert C.Attributes.sqla_mapper.get_property('d').argument is D
        print repr(D.Attributes.sqla_table)
        assert isinstance(D.Attributes.sqla_table.c['c_id'].type, sqlalchemy.Integer)

    def test_add_field_array_many(self):
        class C(TableModel):
            __tablename__ = "c"
            id = Integer32(pk=True)

        class D(TableModel):
            __tablename__ = "d"
            id = Integer32(pk=True)

        C.append_field('d', Array(D).store_as(table(multi='c_d')))
        assert C.Attributes.sqla_mapper.get_property('d').argument is D
        rel_table = C.Attributes.sqla_metadata.tables['c_d']
        assert 'c_id' in rel_table.c
        assert 'd_id' in rel_table.c

class TestSqlAlchemySchemaWithPostgresql(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(PSQL_CONN_STR)
        self.session = sessionmaker(bind=self.engine)()
        self.metadata = TableModel.Attributes.sqla_metadata = MetaData()
        self.metadata.bind = self.engine

    def test_enum(self):
        table_name = "test_enum"
        self.engine.execute("drop table if exists %s" % table_name)

        enums = ('SUBSCRIBED', 'UNSUBSCRIBED', 'UNCONFIRMED')

        class SomeClass(TableModel):
            __tablename__ = table_name

            id = Integer32(primary_key=True)
            e = Enum(*enums, type_name='status_choices')

        logging.getLogger('sqlalchemy').setLevel(logging.DEBUG)
        self.metadata.create_all()
        logging.getLogger('sqlalchemy').setLevel(logging.CRITICAL)

        metadata2 = MetaData()
        metadata2.bind = self.engine
        metadata2.reflect()

        import sqlalchemy.dialects.postgresql.base
        t = metadata2.tables[table_name]
        assert 'e' in t.c
        assert isinstance(t.c.e.type, sqlalchemy.dialects.postgresql.base.ENUM)
        assert t.c.e.type.enums == enums


if __name__ == '__main__':
    unittest.main()
