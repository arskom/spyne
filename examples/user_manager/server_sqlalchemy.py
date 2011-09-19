#!/usr/bin/env python
# encoding: utf8
#
# Copyright © Burak Arslan <burak at arskom dot com dot tr>,
#             Arskom Ltd. http://www.arskom.com.tr
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#    1. Redistributions of source code must retain the above copyright notice,
#       this list of conditions and the following disclaimer.
#    2. Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#    3. Neither the name of the owner nor the names of its contributors may be
#       used to endorse or promote products derived from this software without
#       specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER BE LIABLE FOR ANY DIRECT,
# INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY
# OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE,
# EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
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
from rpclib.model.table import TableModel
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

class User(TableModel, DeclarativeBase):
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
