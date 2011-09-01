#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# rpclib - Copyright (C) 2009 Aaron Bickell, Jamie Kirkpatrick
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

from rpclib.application import Application
from rpclib.decorator import srpc
from rpclib.interface.wsdl import Wsdl11
from rpclib.protocol.soap import Soap11
from rpclib.service import ServiceBase
from rpclib.model.complex import Array
from rpclib.model.complex import ComplexModel
from rpclib.model.primitive import Integer
from rpclib.model.primitive import String
from rpclib.server.wsgi import WsgiApplication

'''
This example shows how to define and use complex structures
in rpclib.  This example uses an extremely simple in-memory
dictionary to store the User objects.
'''

user_database = {}
userid_seq = 1


class Permission(ComplexModel):
    __namespace__ = "permission"
    application = String
    feature = String

class User(ComplexModel):
    __namespace__ = "user"

    userid = Integer
    username = String
    firstname = String
    lastname = String
    permissions = Array(Permission)

class UserManager(ServiceBase):
    @srpc(User, _returns=Integer)
    def add_user(user):
        global user_database
        global userid_seq

        user.userid = userid_seq
        userid_seq = userid_seq+1
        user_database[user.userid] = user

        return user.userid

    @srpc(Integer, _returns=User)
    def get_user(userid):
        global user_database

        return user_database[userid]

    @srpc(User)
    def modify_user(user):
        global user_database

        user_database[user.userid] = user

    @srpc(Integer)
    def delete_user(userid):
        global user_database

        del user_database[userid]

    @srpc(_returns=Array(User))
    def list_users():
        global user_database

        return user_database.values()

if __name__=='__main__':
    try:
        from wsgiref.simple_server import make_server
    except ImportError:
        print "Error: example server code requires Python >= 2.5"

    application = Application([UserManager], 'rpclib.examples.complex',
                interface=Wsdl11(), in_protocol=Soap11(), out_protocol=Soap11())

    server = make_server('127.0.0.1', 7789, WsgiApplication(application))

    print "listening to http://127.0.0.1:7789"
    print "wsdl is at: http://localhost:7789/?wsdl"

    server.serve_forever()
