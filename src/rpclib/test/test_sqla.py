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

import unittest

from rpclib.model.table import TableSerializer
from rpclib.model.complex import ComplexModel

from sqlalchemy.ext.declarative import declarative_base

from sqlalchemy import create_engine
from sqlalchemy import MetaData
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import ForeignKey

from sqlalchemy.orm import mapper
from sqlalchemy.orm import relationship

import logging
logging.basicConfig(level=logging.DEBUG)

class TestSqlAlchemy(unittest.TestCase):
    def set_up(self):
        self.metadata = MetaData()
        self.DeclarativeBase = declarative_base(metadata=self.metadata)
        self.engine = create_engine('sqlite:///:memory:', echo=True)

    setUp=set_up

    def test_declarative(self):
        class DbObject(TableSerializer,self.DeclarativeBase):
            __tablename__ = 'db_object'

            id = Column(Integer, primary_key=True)
            s = Column(String)

        self.metadata.create_all(self.engine)

    def test_mapper(self):
        class User(TableSerializer,self.DeclarativeBase):
            __tablename__ = 'user'

            id = Column(Integer, primary_key=True)
            name = Column(String(50))
            addresses = relationship("Address", backref="user")

        class Address(TableSerializer,self.DeclarativeBase):
            __tablename__ = 'address'

            id = Column(Integer, primary_key=True)
            email = Column(String(50))
            user_id = Column(Integer, ForeignKey('user.id'))

        self.metadata.create_all(self.engine)

        class AddressDetail(ComplexModel):
            id = Integer
            user_name = String
            address = String

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
                    include_properties=cls._properties.keys(),
                    properties=cls._properties,
                    primary_key=[address_t.c.id]
                )

        AddressDetail.mapper(self.metadata)

    def test_serialize(self):
        raise Exception("Test Something!")

    def test_deserialize(self):
        raise Exception("Test Something!")

if __name__ == '__main__':
    unittest.main()
