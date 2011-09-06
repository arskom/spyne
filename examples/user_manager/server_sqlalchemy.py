#!/usr/bin/env python
# encoding: utf8
#
# rpclib - Copyright (C) Rpclib contributors
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
logging.getLogger('rpclib.protocol.soap._base').setLevel(logging.DEBUG)
logging.getLogger('sqlalchemy.engine.base.Engine').setLevel(logging.DEBUG)

import sqlalchemy

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from sqlalchemy import MetaData
from sqlalchemy import Column

from rpclib.application import Application
from rpclib.decorator import rpc
from rpclib.interface.wsdl import Wsdl11
from rpclib.protocol.soap import Soap11
from rpclib.model.complex import Iterable
from rpclib.model.primitive import Integer
from rpclib.model.table import TableSerializer
from rpclib.server.wsgi import WsgiApplication
from rpclib.service import ServiceBase

_user_database = create_engine('sqlite:///:memory:')
metadata = MetaData(bind=_user_database)
DeclarativeBase = declarative_base(metadata=metadata)
Session = sessionmaker(bind=_user_database)

#
# WARNING: You should NOT confuse sqlalchemy types with rpclib types. Whenever
# you see an rpclib service not starting due to some problem with __type_name__
# that's probably because you did not use an rpclib type where you had to (e.g.
# inside @rpc decorator)
#

class User(TableSerializer, DeclarativeBase):
    __namespace__ = 'rpclib.examples.user_manager'
    __tablename__ = 'rpclib_user'

    user_id = Column(sqlalchemy.Integer, primary_key=True)
    user_name = Column(sqlalchemy.String(256))
    first_name = Column(sqlalchemy.String(256))
    last_name = Column(sqlalchemy.String(256))

# this is the same as the above user object. Use this method of declaring
# objects for tables that have to be defined elsewhere.
class AlternativeUser(TableSerializer, DeclarativeBase):
    __namespace__ = 'rpclib.examples.user_manager'
    __table__ = User.__table__

class UserManagerService(ServiceBase):
    @rpc(User, _returns=Integer)
    def add_user(ctx, user):
        ctx.udc.session.add(user)
        ctx.udc.session.flush()

        return user.user_id

    @rpc(Integer, _returns=User)
    def get_user(ctx, user_id):
        return ctx.udc.session.query(User).filter_by(user_id=user_id).one()

    @rpc(User)
    def set_user(ctx, user):
        ctx.udc.session.merge(user)

    @rpc(Integer)
    def del_user(ctx, user_id):
        ctx.udc.session.query(User).filter_by(user_id=user_id).delete()

    @rpc(_returns=Iterable(AlternativeUser))
    def get_all_user(ctx):
        return ctx.udc.session.query(User)

class UserDefinedContext(object):
    def __init__(self):
        self.session = Session()

    def __del__(self):
        self.session.close()

def _on_method_call(ctx):
    ctx.udc = UserDefinedContext()

def _on_method_return_object(ctx):
    # we don't do this in UserDefinedContext.__del__ simply to be able to alert
    # the client in case the commit fails.
    ctx.udc.session.commit()

application = Application([UserManagerService], 'rpclib.examples.user_manager',
            interface=Wsdl11(), in_protocol=Soap11(), out_protocol=Soap11())

application.event_manager.add_listener('method_call', _on_method_call)
application.event_manager.add_listener('method_return_object', _on_method_return_object)

if __name__=='__main__':
    try:
        from wsgiref.simple_server import make_server
    except ImportError:
        print "Error: example server code requires Python >= 2.5"

    wsgi_app = WsgiApplication(application)
    server = make_server('127.0.0.1', 7789, wsgi_app)

    metadata.create_all()
    print "listening to http://127.0.0.1:7789"
    print "wsdl is at: http://localhost:7789/?wsdl"

    server.serve_forever()
