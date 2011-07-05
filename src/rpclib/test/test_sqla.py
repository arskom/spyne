#!/usr/bin/env python
#
# rpclib - Copyright (C) Rpclib contributors.
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

from rpclib.application import Application
from rpclib.decorator import rpc
from rpclib.interface.wsdl import Wsdl11
from rpclib.model.table import TableSerializer
from rpclib.model.complex import ComplexModel
from rpclib.model.complex import Array
from rpclib.protocol.http import HttpRpc
from rpclib.protocol.soap import Soap11
from rpclib.server.null import NullServer
from rpclib.service import ServiceBase

from sqlalchemy.ext.declarative import declarative_base

from sqlalchemy import create_engine
from sqlalchemy import MetaData
from sqlalchemy import Column
from sqlalchemy import Table
from sqlalchemy import ForeignKey

from sqlalchemy.orm import mapper
from sqlalchemy.orm import relationship
from sqlalchemy.orm import sessionmaker

class TestSqlAlchemy(unittest.TestCase):
    def set_up(self):
        self.metadata = MetaData()
        self.DeclarativeBase = declarative_base(metadata=self.metadata)
        self.engine = create_engine('sqlite:///:memory:', echo=True)
        self.Session = sessionmaker(bind=self.engine)

    setUp=set_up

    def test_declarative(self):
        from sqlalchemy import Integer
        from sqlalchemy import String

        class DbObject(TableSerializer,self.DeclarativeBase):
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

        import rpclib.model.primitive

        class AddressDetail(ComplexModel):
            id = rpclib.model.primitive.Integer
            user_name = rpclib.model.primitive.String
            address = rpclib.model.primitive.String

            @classmethod
            def mapper(cls, meta):
                user_t = meta.tables['user']
                address_t = meta.tables['address']

                cls._main_t = user_t.join(address_t)

                cls._properties = {
                    'id' : address_t.c.id,
                    'user_name' : user_t.c.name,
                    'address' : address_t.c.email,
                }

                cls._mapper = mapper(cls, cls._main_t,
                    include_properties=cls._properties.values(),
                    properties=cls._properties,
                    primary_key=[address_t.c.id]
                )

        AddressDetail.mapper(self.metadata)

    #def test_serialize(self):
    #    raise Exception("Test Something!")

    #def test_deserialize(self):
    #    raise Exception("Test Something!")

    def test_rpc(self):
        import sqlalchemy
        from sqlalchemy import sql

        class KeyValuePair(TableSerializer, self.DeclarativeBase):
            __tablename__ = 'key_value_store'
            __namespace__ = 'punk'

            key = Column(sqlalchemy.String(100), nullable=False, primary_key=True)
            value = Column(sqlalchemy.String, nullable=False)

        self.metadata.create_all(self.engine)

        import hashlib

        session = self.Session()

        for i in xrange(1,10):
            key = str(i)
            m = hashlib.md5()
            m.update(key)
            value = m.hexdigest()

            session.add(KeyValuePair(key=key, value=value))

        session.commit()

        from rpclib.service import ServiceBase
        from rpclib.model.complex import Array
        from rpclib.model.primitive import String

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
            interface_class=Wsdl11,
            in_protocol_class=HttpRpc,
            out_protocol_class=Soap11,
            name='Service', tns='tns'
        )

        from rpclib.server.wsgi import WsgiMethodContext

        ctx = WsgiMethodContext(application,{
            'QUERY_STRING': 'key=1&key=2&key=3',
            'PATH_INFO': '/get_values',
        }, 'some-content-type')

        from rpclib.server import ServerBase

        server = ServerBase(application)
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

            print _key, _key.text
            print _value, _value.text

            self.assertEquals(_key.text, key)
            self.assertEquals(_value.text, value)

    def test_late_mapping(self):
        import sqlalchemy

        user_t = Table('user', self.metadata,
             Column('id', sqlalchemy.Integer, primary_key=True),
             Column('name',  sqlalchemy.String),
        )

        class User(TableSerializer, self.DeclarativeBase):
            __table__ = user_t

        self.assertEquals(User._type_info['id'].__type_name__, 'integer')
        self.assertEquals(User._type_info['name'].__type_name__, 'string')

if __name__ == '__main__':
    unittest.main()
