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

from rpclib.application import Application
from rpclib.decorator import rpc
from rpclib.interface.wsdl import Wsdl11
from rpclib.protocol.soap import Soap11
from rpclib.model.primitive import String
from rpclib.model.primitive import Integer
from rpclib.model.complex import Array
from rpclib.model.complex import Iterable
from rpclib.model.complex import ComplexModel
from rpclib.server.wsgi import WsgiApplication
from rpclib.service import ServiceBase

_user_database = {}
_user_id_seq = 1

class Permission(ComplexModel):
    __namespace__ = 'rpclib.examples.user_manager'

    application = String
    operation = String

class User(ComplexModel):
    __namespace__ = 'rpclib.examples.user_manager'

    user_id = Integer
    user_name = String
    first_name = String
    last_name = String
    permissions = Array(Permission)

class UserManagerService(ServiceBase):
    @rpc(User, _returns=Integer)
    def add_user(ctx, user):
        user.user_id = ctx.udc.get_next_user_id()
        ctx.udc.users[user.user_id] = user

        return user.user_id

    @rpc(Integer, _returns=User)
    def get_user(ctx, user_id):
        return ctx.udc.users[user_id]

    @rpc(User)
    def set_user(ctx, user):
        ctx.udc.users[user.user_id] = user

    @rpc(Integer)
    def del_user(ctx, user_id):
        del ctx.udc.users[user_id]

    @rpc(_returns=Iterable(User))
    def get_all_user(ctx):
        return ctx.udc.users.itervalues()

class UserDefinedContext(object):
    def __init__(self):
        self.users = _user_database

    @staticmethod
    def get_next_user_id():
        global _user_id_seq

        _user_id_seq += 1

        return _user_id_seq

def _on_method_call(ctx):
    ctx.udc = UserDefinedContext()

application = Application([UserManagerService], 'rpclib.examples.user_manager',
            interface=Wsdl11(), in_protocol=Soap11(), out_protocol=Soap11())

application.event_manager.add_listener('method_call', _on_method_call)

if __name__=='__main__':
    try:
        from wsgiref.simple_server import make_server
    except ImportError:
        print "Error: example server code requires Python >= 2.5"

    server = make_server('127.0.0.1', 7789, WsgiApplication(application))

    print "listening to http://127.0.0.1:7789"
    print "wsdl is at: http://localhost:7789/?wsdl"

    server.serve_forever()
