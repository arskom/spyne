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

from spyne.application import Application
from spyne.decorator import srpc
from spyne.interface.wsdl import Wsdl11
from spyne.protocol.soap import Soap11
from spyne.service import ServiceBase
from spyne.model.complex import Array
from spyne.model.complex import ComplexModel
from spyne.model.primitive import Integer
from spyne.model.primitive import String
from spyne.server.wsgi import WsgiApplication

'''
This example shows how to define and use complex structures
in spyne.  This example uses an extremely simple in-memory
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
        print("Error: example server code requires Python >= 2.5")

    application = Application([UserManager], 'spyne.examples.complex',
                interface=Wsdl11(), in_protocol=Soap11(), out_protocol=Soap11())

    server = make_server('127.0.0.1', 7789, WsgiApplication(application))

    print("listening to http://127.0.0.1:7789")
    print("wsdl is at: http://localhost:7789/?wsdl")

    server.serve_forever()
