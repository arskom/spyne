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
logging.getLogger('spyne.protocol.xml').setLevel(logging.DEBUG)

from spyne.application import Application
from spyne.decorator import rpc
from spyne.interface.wsdl import Wsdl11
from spyne.protocol.soap import Soap11
from spyne.model.primitive import String
from spyne.model.primitive import Integer
from spyne.model.complex import Array
from spyne.model.complex import Iterable
from spyne.model.complex import ComplexModel
from spyne.server.wsgi import WsgiApplication
from spyne.service import ServiceBase

_user_database = {}
_user_id_seq = 1


class Permission(ComplexModel):
    __namespace__ = 'spyne.examples.user_manager'

    application = String
    operation = String


class User(ComplexModel):
    __namespace__ = 'spyne.examples.user_manager'

    user_id = Integer
    user_name = String
    first_name = String
    last_name = String
    email = String(pattern=r'[a-z0-9._%+-]+@[a-z0-9.-]+\.[A-Z]{2,4}')
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

application = Application([UserManagerService], 'spyne.examples.user_manager',
            interface=Wsdl11(), in_protocol=Soap11(), out_protocol=Soap11())

application.event_manager.add_listener('method_call', _on_method_call)

if __name__=='__main__':
    try:
        from wsgiref.simple_server import make_server
    except ImportError:
        logging.error("Error: example server code requires Python >= 2.5")

    server = make_server('127.0.0.1', 8000, WsgiApplication(application))

    logging.info("listening to http://127.0.0.1:8000")
    logging.info("wsdl is at: http://localhost:8000/?wsdl")

    server.serve_forever()
