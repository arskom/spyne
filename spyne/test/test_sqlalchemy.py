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
from sqlalchemy.orm.mapper import Mapper

logging.basicConfig(level=logging.DEBUG)

from getpass import getuser
PSQL_CONN_STR = 'postgres://postgres:@localhost:5432/spyne_test_%s' % getuser()

import unittest
import sqlalchemy

from sqlalchemy.ext.declarative import declarative_base

from sqlalchemy import create_engine
from sqlalchemy import MetaData
from sqlalchemy import Column
from sqlalchemy import Table
from sqlalchemy import ForeignKey
from sqlalchemy.exc import IntegrityError

from sqlalchemy.orm import mapper
from sqlalchemy.orm import relationship
from sqlalchemy.orm import sessionmaker

from sqlalchemy.schema import UniqueConstraint

from sqlalchemy.exc import IntegrityError

from spyne.application import Application
from spyne.decorator import rpc
from spyne.model import XmlAttribute
from spyne.model import XmlData
from spyne.model import ComplexModel
from spyne.model.complex import xml
from spyne.model import Array
from spyne.model import Integer32
from spyne.model import Unicode
from spyne.model import Integer
from spyne.model import Enum
from spyne.model.table import TableModel
from spyne.protocol.http import HttpRpc
from spyne.protocol.soap import Soap11
from spyne.server.wsgi import WsgiApplication
from spyne.server.wsgi import WsgiMethodContext

#
# Deprecated Table Model Tests
#

class TestSqlAlchemy(unittest.TestCase):
    def setUp(self):
        self.metadata = MetaData()
        self.DeclarativeBase = declarative_base(metadata=self.metadata)
        self.engine = create_engine('sqlite:///:memory:', echo=True)
        self.Session = sessionmaker(bind=self.engine)

    def tearDown(self):
        del self.metadata
        del self.DeclarativeBase
        del self.engine
        del self.Session

    def test_declarative(self):
        from sqlalchemy import Integer
        from sqlalchemy import String

        class DbObject(TableModel, self.DeclarativeBase):
            __tablename__ = 'db_object'

            id = Column(Integer, primary_key=True)
            s = Column(String)

        self.metadata.create_all(self.engine)

    def test_mapper(self):
        import sqlalchemy

        class User(self.DeclarativeBase):
            __tablename__ = 'user'

            id = Column(sqlalchemy.Integer, primary_key=True)
            name = Column(sqlalchemy.String(50))
            addresses = relationship("Address", backref="user")

        class Address(self.DeclarativeBase):
            __tablename__ = 'address'

            id = Column(sqlalchemy.Integer, primary_key=True)
            email = Column(sqlalchemy.String(50))
            user_id = Column(sqlalchemy.Integer, ForeignKey('user.id'))

        self.metadata.create_all(self.engine)

        import spyne.model.primitive

        class AddressDetail(ComplexModel):
            id = spyne.model.primitive.Integer
            user_name = spyne.model.primitive.String
            address = spyne.model.primitive.String

            @classmethod
            def mapper(cls, meta):
                user_t = meta.tables['user']
                address_t = meta.tables['address']

                cls._main_t = user_t.join(address_t)

                cls._properties = {
                    'id': address_t.c.id,
                    'user_name': user_t.c.name,
                    'address': address_t.c.email,
                }

                cls._mapper = mapper(cls, cls._main_t,
                    include_properties=cls._properties.values(),
                    properties=cls._properties,
                    primary_key=[address_t.c.id]
                )

        AddressDetail.mapper(self.metadata)

    def test_custom_mapper(self):
        class CustomMapper(Mapper):
            def __init__(self, class_, local_table, *args, **kwargs):
                super(CustomMapper, self).__init__(class_, local_table, *args,
                    **kwargs)

            # Do not configure primary keys to check that CustomerMapper is
            # actually used
            def _configure_pks(self):
                pass

        def custom_mapper(class_, local_table=None, *args, **params):
            return CustomMapper(class_, local_table, *args, **params)

        CustomDeclarativeBase = declarative_base(metadata=self.metadata,
                                                   mapper=custom_mapper)

        class User(CustomDeclarativeBase):
            __tablename__ = 'user'

            # CustomMapper should not fail because of no primary key
            name = Column(sqlalchemy.String(50))

        self.metadata.create_all(self.engine)

    def test_rpc(self):
        import sqlalchemy
        from sqlalchemy import sql

        class KeyValuePair(TableModel, self.DeclarativeBase):
            __tablename__ = 'key_value_store'
            __namespace__ = 'punk'

            key = Column(sqlalchemy.String(100), nullable=False, primary_key=True)
            value = Column(sqlalchemy.String, nullable=False)

        self.metadata.create_all(self.engine)

        import hashlib

        session = self.Session()

        for i in range(1, 10):
            key = str(i)
            m = hashlib.md5()
            m.update(key)
            value = m.hexdigest()

            session.add(KeyValuePair(key=key, value=value))

        session.commit()

        from spyne.service import ServiceBase
        from spyne.model.complex import Array
        from spyne.model.primitive import String

        class Service(ServiceBase):
            @rpc(String(max_occurs='unbounded'),
                    _returns=Array(KeyValuePair),
                    _in_variable_names={
                        'keys': 'key'
                    }
                )
            def get_values(ctx, keys):
                session = self.Session()

                return session.query(KeyValuePair).filter(sql.and_(
                    KeyValuePair.key.in_(keys)
                )).order_by(KeyValuePair.key)

        application = Application([Service],
            in_protocol=HttpRpc(),
            out_protocol=Soap11(),
            name='Service', tns='tns'
        )
        server = WsgiApplication(application)

        initial_ctx = WsgiMethodContext(server, {
            'REQUEST_METHOD': 'GET',
            'QUERY_STRING': 'key=1&key=2&key=3',
            'PATH_INFO': '/get_values',
            'SERVER_NAME': 'localhost',
        }, 'some-content-type')

        ctx, = server.generate_contexts(initial_ctx)
        server.get_in_object(ctx)
        server.get_out_object(ctx)
        server.get_out_string(ctx)

        i = 0
        for e in ctx.out_document[0][0][0]:
            i+=1
            key = str(i)
            m = hashlib.md5()
            m.update(key)
            value = m.hexdigest()

            _key = e.find('{%s}key' % KeyValuePair.get_namespace())
            _value = e.find('{%s}value' % KeyValuePair.get_namespace())

            print((_key, _key.text))
            print((_value, _value.text))

            self.assertEquals(_key.text, key)
            self.assertEquals(_value.text, value)

    def test_late_mapping(self):
        import sqlalchemy

        user_t = Table('user', self.metadata,
             Column('id', sqlalchemy.Integer, primary_key=True),
             Column('name',  sqlalchemy.String),
        )

        class User(TableModel, self.DeclarativeBase):
            __table__ = user_t

        self.assertEquals(User._type_info['id'].__type_name__, 'integer')
        self.assertEquals(User._type_info['name'].__type_name__, 'string')


    def test_default_ctor(self):
        import sqlalchemy

        class User1Mixin(object):
            id = Column(sqlalchemy.Integer, primary_key=True)
            name = Column(sqlalchemy.String(256))

        class User1(self.DeclarativeBase, TableModel, User1Mixin):
            __tablename__ = 'spyne_user1'

            mail = Column(sqlalchemy.String(256))

        u = User1(id=1, mail="a@b.com", name='dummy')

        assert u.id == 1
        assert u.mail == "a@b.com"
        assert u.name == "dummy"

        class User2Mixin(object):
            id = Column(sqlalchemy.Integer, primary_key=True)
            name = Column(sqlalchemy.String(256))

        class User2(TableModel, self.DeclarativeBase, User2Mixin):
            __tablename__ = 'spyne_user2'

            mail = Column(sqlalchemy.String(256))

        u = User2(id=1, mail="a@b.com", name='dummy')

        assert u.id == 1
        assert u.mail == "a@b.com"
        assert u.name == "dummy"

    def test_mixin_inheritance(self):
        import sqlalchemy

        class UserMixin(object):
            id = Column(sqlalchemy.Integer, primary_key=True)
            name = Column(sqlalchemy.String(256))

        class User(self.DeclarativeBase, TableModel, UserMixin):
            __tablename__ = 'spyne_user_mixin'

            mail = Column(sqlalchemy.String(256))

        assert 'mail' in User._type_info
        assert 'name' in User._type_info
        assert 'id' in User._type_info

    def test_same_table_inheritance(self):
        import sqlalchemy

        class User(self.DeclarativeBase, TableModel):
            __tablename__ = 'spyne_user_sti'

            id = Column(sqlalchemy.Integer, primary_key=True)
            name = Column(sqlalchemy.String(256))

        class UserMail(User):
            mail = Column(sqlalchemy.String(256))

        assert 'mail' in UserMail._type_info
        assert 'name' in UserMail._type_info
        assert 'id' in UserMail._type_info

    def test_relationship_array(self):
        import sqlalchemy
        class Permission(TableModel, self.DeclarativeBase):
            __tablename__ = 'spyne_user_permission'

            id = Column(sqlalchemy.Integer, primary_key=True)
            user_id = Column(sqlalchemy.Integer, ForeignKey("spyne_user.id"))


        class User(TableModel, self.DeclarativeBase):
            __tablename__ = 'spyne_user'

            id = Column(sqlalchemy.Integer, primary_key=True)
            permissions = relationship(Permission)

        class Address(self.DeclarativeBase, TableModel):
            __tablename__ = 'spyne_address'

            id = Column(sqlalchemy.Integer, primary_key=True)
            address = Column(sqlalchemy.String(256))
            user_id = Column(sqlalchemy.Integer, ForeignKey(User.id), nullable=False)
            user = relationship(User)

        assert 'permissions' in User._type_info
        assert issubclass(User._type_info['permissions'], Array)
        assert issubclass(User._type_info['permissions']._type_info.values()[0], Permission)

        #Address().user = None
        #User().permissions = None # This fails, and actually is supposed to fail.


class TestSpyne2Sqlalchemy(unittest.TestCase):
    def test_table(self):
        class SomeClass(ComplexModel):
            __metadata__ = MetaData()
            __tablename__ = 'some_class'

            i = Integer(primary_key=True)

        t = SomeClass.Attributes.sqla_table
        assert t.c['i'].type.__class__ is sqlalchemy.DECIMAL

    def test_table_args(self):
        class SomeClass(ComplexModel):
            __metadata__ = MetaData()
            __tablename__ = 'some_class'
            __table_args__ = (
                UniqueConstraint('j'),
            )

            i = Integer(primary_key=True)
            j = Unicode(64)

        t = SomeClass.Attributes.sqla_table
        assert isinstance(t.c['j'].type, sqlalchemy.Unicode)

        for c in t.constraints:
            if isinstance(c, UniqueConstraint):
                assert list(c.columns) == [t.c.j]
                break
        else:
            raise Exception("UniqueConstraint is missing.")

#
# New Table Model Tests
#

from spyne.model.complex import TTableModel
from spyne.model.complex import table

class NewTableModel:pass # prevents netbeans from whining about undefined base class.
NewTableModel = TTableModel()

class TestSqlAlchemySchema(unittest.TestCase):
    def setUp(self):
        import logging
        logging.getLogger('sqlalchemy').setLevel(logging.DEBUG)

    def test_schema(self):
        engine = create_engine('sqlite:///:memory:')
        session = sessionmaker(bind=engine)()
        metadata = NewTableModel.Attributes.sqla_metadata = MetaData()
        metadata.bind = engine

        class SomeClass(NewTableModel):
            __tablename__ = 'some_class'
            __table_args__ = {"sqlite_autoincrement": True}

            id = Integer32(primary_key=True, autoincrement=False)
            s = Unicode(64, unique=True)
            i = Integer32(64, index=True)

        t = SomeClass.__table__
        metadata.create_all() # not needed, just nice to see.

        assert t.c.id.primary_key == True
        assert t.c.id.autoincrement == False
        indexes = list(t.indexes)
        indexes.sort(key=lambda idx: idx.columns)
        for idx in indexes:
            assert 'i' in idx.columns or 's' in idx.columns
            if 's' in idx.columns:
                assert idx.unique


class TestSqlAlchemyNested(unittest.TestCase):
    def setUp(self):
        import logging
        logging.getLogger('sqlalchemy').setLevel(logging.DEBUG)

    def test_nested_sql(self):
        engine = create_engine('sqlite:///:memory:')
        session = sessionmaker(bind=engine)()
        metadata = NewTableModel.Attributes.sqla_metadata = MetaData()
        metadata.bind = engine

        class SomeOtherClass(NewTableModel):
            __tablename__ = 'some_other_class'
            __table_args__ = {"sqlite_autoincrement": True}

            id = Integer32(primary_key=True)
            s = Unicode(64)

        class SomeClass(NewTableModel):
            __tablename__ = 'some_class'
            __table_args__ = (
                {"sqlite_autoincrement": True},
            )

            id = Integer32(primary_key=True)
            o = SomeOtherClass.customize(store_as='table')

        metadata.create_all()

        soc = SomeOtherClass(s='ehe')
        sc = SomeClass(o=soc)

        session.add(sc)
        session.commit()
        session.close()

        sc_db = session.query(SomeClass).get(1)
        print sc_db
        assert sc_db.o.s == 'ehe'
        assert sc_db.o_id == 1

        sc_db.o = None
        session.commit()
        session.close()

        sc_db = session.query(SomeClass).get(1)
        assert sc_db.o == None
        assert sc_db.o_id == None

    def test_nested_sql_array_as_table(self):
        engine = create_engine('sqlite:///:memory:')
        session = sessionmaker(bind=engine)()
        metadata = NewTableModel.Attributes.sqla_metadata = MetaData()
        metadata.bind = engine

        class SomeOtherClass(NewTableModel):
            __tablename__ = 'some_other_class'
            __table_args__ = {"sqlite_autoincrement": True}

            id = Integer32(primary_key=True)
            s = Unicode(64)

        class SomeClass(NewTableModel):
            __tablename__ = 'some_class'
            __table_args__ = {"sqlite_autoincrement": True}

            id = Integer32(primary_key=True)
            others = Array(SomeOtherClass, store_as='table')

        metadata.create_all()

        soc1 = SomeOtherClass(s='ehe1')
        soc2 = SomeOtherClass(s='ehe2')
        sc = SomeClass(others=[soc1, soc2])

        session.add(sc)
        session.commit()
        session.close()

        sc_db = session.query(SomeClass).get(1)

        assert sc_db.others[0].s == 'ehe1'
        assert sc_db.others[1].s == 'ehe2'

        session.close()

    def test_nested_sql_array_as_multi_table(self):
        engine = create_engine('sqlite:///:memory:')
        session = sessionmaker(bind=engine)()
        metadata = NewTableModel.Attributes.sqla_metadata = MetaData()
        metadata.bind = engine

        class SomeOtherClass(NewTableModel):
            __tablename__ = 'some_other_class'
            __table_args__ = {"sqlite_autoincrement": True}

            id = Integer32(primary_key=True)
            s = Unicode(64)

        class SomeClass(NewTableModel):
            __tablename__ = 'some_class'
            __table_args__ = {"sqlite_autoincrement": True}

            id = Integer32(primary_key=True)
            others = Array(SomeOtherClass, store_as=table(multi=True))

        metadata.create_all()

        soc1 = SomeOtherClass(s='ehe1')
        soc2 = SomeOtherClass(s='ehe2')
        sc = SomeClass(others=[soc1, soc2])

        session.add(sc)
        session.commit()
        session.close()

        sc_db = session.query(SomeClass).get(1)

        assert sc_db.others[0].s == 'ehe1'
        assert sc_db.others[1].s == 'ehe2'

        session.close()

    def test_nested_sql_array_as_multi_table_with_backref(self):
        engine = create_engine('sqlite:///:memory:')
        session = sessionmaker(bind=engine)()
        metadata = NewTableModel.Attributes.sqla_metadata = MetaData()
        metadata.bind = engine

        class SomeOtherClass(NewTableModel):
            __tablename__ = 'some_other_class'
            __table_args__ = {"sqlite_autoincrement": True}

            id = Integer32(primary_key=True)
            s = Unicode(64)

        class SomeClass(NewTableModel):
            __tablename__ = 'some_class'
            __table_args__ = {"sqlite_autoincrement": True}

            id = Integer32(primary_key=True)
            others = Array(SomeOtherClass, store_as=table(multi=True, backref='some_classes'))

        metadata.create_all()

        soc1 = SomeOtherClass(s='ehe1')
        soc2 = SomeOtherClass(s='ehe2')
        sc = SomeClass(others=[soc1, soc2])

        session.add(sc)
        session.commit()
        session.close()

        soc_db = session.query(SomeOtherClass).all()

        assert soc_db[0].some_classes[0].id == 1
        assert soc_db[1].some_classes[0].id == 1

        session.close()

    def test_nested_sql_array_as_xml(self):
        engine = create_engine('sqlite:///:memory:')
        session = sessionmaker(bind=engine)()
        metadata = NewTableModel.Attributes.sqla_metadata = MetaData()
        metadata.bind = engine

        class SomeOtherClass(ComplexModel):
            id = Integer32
            s = Unicode(64)

        class SomeClass(NewTableModel):
            __tablename__ = 'some_class'
            __table_args__ = {"sqlite_autoincrement": True}

            id = Integer32(primary_key=True)
            others = Array(SomeOtherClass, store_as='xml')

        metadata.create_all()

        soc1 = SomeOtherClass(s='ehe1')
        soc2 = SomeOtherClass(s='ehe2')
        sc = SomeClass(others=[soc1, soc2])

        session.add(sc)
        session.commit()
        session.close()

        sc_db = session.query(SomeClass).get(1)

        assert sc_db.others[0].s == 'ehe1'
        assert sc_db.others[1].s == 'ehe2'

        session.close()

    def test_nested_sql_array_as_xml_no_ns(self):
        engine = create_engine('sqlite:///:memory:')
        session = sessionmaker(bind=engine)()
        metadata = NewTableModel.Attributes.sqla_metadata = MetaData()
        metadata.bind = engine

        class SomeOtherClass(ComplexModel):
            id = Integer32
            s = Unicode(64)

        class SomeClass(NewTableModel):
            __tablename__ = 'some_class'
            __table_args__ = {"sqlite_autoincrement": True}

            id = Integer32(primary_key=True)
            others = Array(SomeOtherClass, store_as=xml(no_ns=True))

        metadata.create_all()

        soc1 = SomeOtherClass(s='ehe1')
        soc2 = SomeOtherClass(s='ehe2')
        sc = SomeClass(others=[soc1, soc2])

        session.add(sc)
        session.commit()
        session.close()

        sc_xml = session.connection().execute("select others from some_class") \
                                                               .fetchall()[0][0]

        from lxml import etree
        assert etree.fromstring(sc_xml).tag == 'SomeOtherClassArray'

        session.close()

    def test_inheritance(self):
        engine = create_engine('sqlite:///:memory:')
        session = sessionmaker(bind=engine)()
        metadata = NewTableModel.Attributes.sqla_metadata = MetaData(bind=engine)

        class SomeOtherClass(NewTableModel):
            __tablename__ = 'some_other_class'
            __table_args__ = {"sqlite_autoincrement": True}
            id = Integer32(primary_key=True)
            s = Unicode(64)

        class SomeClass(SomeOtherClass):
            numbers = Array(Integer32).store_as(xml(no_ns=True, root_tag='a'))

        metadata.create_all()

        sc = SomeClass(id=5, s='s', numbers=[1,2,3,4])

        session.add(sc)
        session.commit()
        session.close()

        sc_db = session.query(SomeClass).get(5)
        assert sc_db.numbers == [1, 2, 3, 4]
        session.close()

        sc_db = session.query(SomeOtherClass).get(5)
        assert sc_db.id == 5
        try:
            sc_db.numbers
        except AttributeError:
            pass
        else:
            raise Exception("must fail")

        session.close()

    def test_sqlalchemy_inheritance(self):
        # no spyne code is involved here.
        # this is just to test test the sqlalchemy behavior that we rely on.
        engine = create_engine('sqlite:///:memory:')
        session = sessionmaker(bind=engine)()
        metadata = MetaData(bind=engine)

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

        employees_table = Table('employees', metadata,
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

        metadata.create_all()

        manager = Manager('name', 'data')
        session.add(manager)
        session.commit()
        session.close()

        assert session.query(Employee).with_polymorphic('*').get(1).type == 'manager'

    def test_inheritance_polymorphic_with_non_nullables_in_subclasses(self):
        engine = create_engine('sqlite:///:memory:')
        session = sessionmaker(bind=engine)()
        metadata = NewTableModel.Attributes.sqla_metadata = MetaData(bind=engine)

        class SomeOtherClass(NewTableModel):
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

        metadata.create_all()

        assert SomeOtherClass.__table__.c.s.nullable == False

        # this should be nullable to let other classes be added.
        # spyne still checks this constraint when doing input validation.
        # should spyne generate a trigger to check this at database level as well?
        assert SomeOtherClass.__table__.c.i.nullable == True

        soc = SomeOtherClass(s='s')
        session.add(soc)
        session.commit()
        soc_id = soc.id

        try:
            sc = SomeClass(i=5)
            session.add(sc)
            session.commit()
        except IntegrityError:
            session.rollback()
        else:
            raise Exception("Must fail with IntegrityError.")

        sc2 = SomeClass(s='s') # this won't fail. should it?
        session.add(sc2)
        session.commit()

        session.expunge_all()

        session.query(SomeOtherClass).with_polymorphic('*').get(soc_id).t == 1
        session.close()

    def test_inheritance_polymorphic(self):
        engine = create_engine('sqlite:///:memory:')
        session = sessionmaker(bind=engine)()
        metadata = NewTableModel.Attributes.sqla_metadata = MetaData(bind=engine)

        class SomeOtherClass(NewTableModel):
            __tablename__ = 'some_class'
            __table_args__ = {"sqlite_autoincrement": True} # this is sqlite-specific
            __mapper_args__ = {'polymorphic_on': 't', 'polymorphic_identity': 1}

            id = Integer32(primary_key=True)
            s = Unicode(64)
            t = Integer32(nillable=False)

        class SomeClass(SomeOtherClass):
            __mapper_args__ = {'polymorphic_identity': 2}
            numbers = Array(Integer32).store_as(xml(no_ns=True, root_tag='a'))

        metadata.create_all()

        sc = SomeClass(id=5, s='s', numbers=[1,2,3,4])

        session.add(sc)
        session.commit()
        session.close()

        session.query(SomeOtherClass).with_polymorphic('*').get(5).t == 1
        session.close()

    def test_nested_sql_array_as_json(self):
        engine = create_engine('sqlite:///:memory:')
        session = sessionmaker(bind=engine)()
        metadata = NewTableModel.Attributes.sqla_metadata = MetaData()
        metadata.bind = engine

        class SomeOtherClass(ComplexModel):
            id = Integer32
            s = Unicode(64)

        class SomeClass(NewTableModel):
            __tablename__ = 'some_class'
            __table_args__ = {"sqlite_autoincrement": True}

            id = Integer32(primary_key=True)
            others = Array(SomeOtherClass, store_as='json')

        metadata.create_all()

        soc1 = SomeOtherClass(s='ehe1')
        soc2 = SomeOtherClass(s='ehe2')
        sc = SomeClass(others=[soc1, soc2])

        session.add(sc)
        session.commit()
        session.close()

        sc_db = session.query(SomeClass).get(1)

        assert sc_db.others[0].s == 'ehe1'
        assert sc_db.others[1].s == 'ehe2'

        session.close()

    def test_modifiers(self):
        engine = create_engine('sqlite:///:memory:')
        session = sessionmaker(bind=engine)()
        metadata = NewTableModel.Attributes.sqla_metadata = MetaData()
        metadata.bind = engine

        class SomeClass(NewTableModel):
            __tablename__ = 'some_class'
            __table_args__ = {"sqlite_autoincrement": True}

            i = XmlAttribute(Integer32(pk=True))
            s = XmlData(Unicode(64))

        metadata.create_all()
        session.add(SomeClass(s='s'))
        session.commit()
        session.expunge_all()

        ret = session.query(SomeClass).get(1)
        assert ret.i == 1 # redundant
        assert ret.s == 's'

    def test_default_ctor(self):
        engine = create_engine('sqlite:///:memory:')
        session = sessionmaker(bind=engine)()
        metadata = NewTableModel.Attributes.sqla_metadata = MetaData()
        metadata.bind = engine

        class SomeOtherClass(ComplexModel):
            id = Integer32
            s = Unicode(64)

        class SomeClass(NewTableModel):
            __tablename__ = 'some_class'
            __table_args__ = {"sqlite_autoincrement": True}

            id = Integer32(primary_key=True)
            others = Array(SomeOtherClass, store_as='json')
            f = Unicode(32, default='uuu')

        metadata.create_all()
        session.add(SomeClass())
        session.commit()
        session.expunge_all()

        assert session.query(SomeClass).get(1).f == 'uuu'

    def test_default_ctor_with_sql_relationship(self):
        engine = create_engine('sqlite:///:memory:')
        session = sessionmaker(bind=engine)()
        metadata = NewTableModel.Attributes.sqla_metadata = MetaData()
        metadata.bind = engine

        class SomeOtherClass(NewTableModel):
            __tablename__ = 'some_other_class'
            __table_args__ = {"sqlite_autoincrement": True}

            id = Integer32(primary_key=True)
            s = Unicode(64)

        class SomeClass(NewTableModel):
            __tablename__ = 'some_class'
            __table_args__ = (
                {"sqlite_autoincrement": True},
            )

            id = Integer32(primary_key=True)
            o = SomeOtherClass.customize(store_as='table')

        metadata.create_all()
        session.add(SomeClass())
        session.commit()

    def test_scalar_collection(self):
        engine = create_engine('sqlite:///:memory:')
        session = sessionmaker(bind=engine)()
        metadata = NewTableModel.Attributes.sqla_metadata = MetaData()
        metadata.bind = engine

        class SomeClass(NewTableModel):
            __tablename__ = 'some_class'

            id = Integer32(primary_key=True)
            values = Array(Unicode).store_as('table')

        metadata.create_all()

        session.add(SomeClass(id=1, values=['a', 'b', 'c']))
        session.commit()
        sc = session.query(SomeClass).get(1)
        assert sc.values == ['a', 'b', 'c']
        del sc

        sc = session.query(SomeClass).get(1)
        sc.values.append('d')
        session.commit()
        del sc
        sc = session.query(SomeClass).get(1)
        assert sc.values == ['a', 'b', 'c', 'd']

        sc = session.query(SomeClass).get(1)
        sc.values = sc.values[1:]
        session.commit()
        del sc
        sc = session.query(SomeClass).get(1)
        assert sc.values == ['b', 'c', 'd']

    def test_multiple_fk(self):
        engine = create_engine('sqlite:///:memory:')
        session = sessionmaker(bind=engine)()
        metadata = NewTableModel.Attributes.sqla_metadata = MetaData()
        metadata.bind = engine

        class SomeChildClass(NewTableModel):
            __tablename__ = 'some_child_class'

            id = Integer32(primary_key=True)
            s = Unicode(64)
            i = Integer32

        class SomeClass(NewTableModel):
            __tablename__ = 'some_class'

            id = Integer32(primary_key=True)
            children = Array(SomeChildClass).store_as('table')
            mirror = SomeChildClass.store_as('table')

        metadata.create_all()

        children = [
            SomeChildClass(s='p', i=600),
            SomeChildClass(s='|', i=10),
            SomeChildClass(s='q', i=9),
        ]

        sc = SomeClass(children=children)
        session.add(sc)
        session.flush()
        sc.mirror = children[1]
        session.commit()
        del sc

        sc = session.query(SomeClass).get(1)
        assert ''.join([scc.s for scc in sc.children]) == 'p|q'
        assert     sum([scc.i for scc in sc.children]) ==  619

    def test_reflection(self):
        engine = create_engine('sqlite:///:memory:')
        session = sessionmaker(bind=engine)()
        metadata = NewTableModel.Attributes.sqla_metadata = MetaData()
        metadata.bind = engine

        class SomeChildClass(NewTableModel):
            __tablename__ = 'some_child_class'

            id = Integer32(primary_key=True)
            s = Unicode(64)
            i = Integer32

        class SomeClass(NewTableModel):
            __tablename__ = 'some_class'

            id = Integer32(primary_key=True)
            children = Array(SomeChildClass).store_as('xml')
            mirror = SomeChildClass.store_as('json')

        metadata2 = MetaData()
        metadata2.bind = engine
        metadata2.reflect()


class TestSqlAlchemySchemaWithPostgresql(unittest.TestCase):
    def test_enum(self):
        table_name = "test_enum"
        enums = ('SUBSCRIBED', 'UNSUBSCRIBED', 'UNCONFIRMED')

        engine = create_engine(PSQL_CONN_STR)
        engine.execute("drop table if exists %s" % table_name)
        session = sessionmaker(bind=engine)()
        metadata = NewTableModel.Attributes.sqla_metadata = MetaData()
        metadata.bind = engine

        class SomeClass(NewTableModel):
            __tablename__ = table_name

            id = Integer32(primary_key=True)
            e = Enum(*enums, type_name='status_choices')

        logging.getLogger('sqlalchemy').setLevel(logging.DEBUG)
        metadata.create_all()
        logging.getLogger('sqlalchemy').setLevel(logging.CRITICAL)

        metadata2 = MetaData()
        metadata2.bind = engine
        metadata2.reflect()

        import sqlalchemy.dialects.postgresql.base
        t = metadata2.tables[table_name]
        assert 'e' in t.c
        assert isinstance(t.c.e.type, sqlalchemy.dialects.postgresql.base.ENUM)
        assert t.c.e.type.enums == enums


if __name__ == '__main__':
    unittest.main()
