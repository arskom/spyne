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

import unittest
import sqlalchemy

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm.mapper import Mapper

from sqlalchemy import create_engine
from sqlalchemy import MetaData
from sqlalchemy import Column
from sqlalchemy import Table
from sqlalchemy import ForeignKey

from sqlalchemy.orm import mapper
from sqlalchemy.orm import relationship
from sqlalchemy.orm import sessionmaker

from sqlalchemy.schema import UniqueConstraint

from spyne.application import Application
from spyne.decorator import rpc
from spyne.model import ComplexModel
from spyne.model import Array
from spyne.model import Unicode
from spyne.model import Integer
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

        class Address(self.DeclarativeBase):
            __tablename__ = 'address'

            id = Column(sqlalchemy.Integer, primary_key=True)
            email = Column(sqlalchemy.String(50))
            user_id = Column(sqlalchemy.Integer, ForeignKey('user.id'))

        class User(self.DeclarativeBase):
            __tablename__ = 'user'

            id = Column(sqlalchemy.Integer, primary_key=True)
            name = Column(sqlalchemy.String(50))
            addresses = relationship("Address", backref="user")

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


if __name__ == '__main__':
    unittest.main()
