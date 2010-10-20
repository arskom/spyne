#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# soaplib - Copyright (C) 2009 Aaron Bickell, Jamie Kirkpatrick
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

from soaplib.server.wsgi import Application
from soaplib.service import rpc
from soaplib.service import DefinitionBase
from soaplib.model.primitive import String, Integer

from soaplib.model.clazz import ClassSerializer, Array

'''
This example shows how to define and use complex structures
in soaplib.  This example uses an extremely simple in-memory
dictionary to store the User objects.
'''

user_database = {}
userid_seq = 1


class Permission(ClassSerializer):
    __namespace__ = "permission"
    application = String
    feature = String

class User(ClassSerializer):
    __namespace__ = "user"
    userid = Integer
    username = String
    firstname = String
    lastname = String
    permissions = Array(Permission)

class UserManager(DefinitionBase):
    @rpc(User, _returns=Integer)
    def add_user(self, user):
        global user_database
        global userid_seq

        user.userid = userid_seq
        userid_seq = userid_seq+1
        user_database[user.userid] = user

        return user.userid

    @rpc(Integer, _returns=User)
    def get_user(self, userid):
        global user_database

        return user_database[userid]

    @rpc(User)
    def modify_user(self, user):
        global user_database

        user_database[user.userid] = user

    @rpc(Integer)
    def delete_user(self, userid):
        global user_database

        del user_database[userid]

    @rpc(_returns=Array(User))
    def list_users(self):
        global user_database

        return [v for k, v in user_database.items()]

if __name__=='__main__':
    try:
        from wsgiref.simple_server import make_server
        server = make_server('localhost', 7789, Application([UserManager], 'tns'))
        server.serve_forever()
    except ImportError:
        print "Error: example server code requires Python >= 2.5"
