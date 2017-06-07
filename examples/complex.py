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


"""
This example shows how to define and use complex structures
in spyne.  This example uses an extremely simple in-memory
dictionary to store the User objects.
"""

import logging
import random

from spyne import Application, rpc, Array, ComplexModel, Integer, String, \
    Service, ResourceNotFoundError
from spyne.protocol.http import HttpRpc
from spyne.protocol.xml import XmlDocument
from spyne.server.wsgi import WsgiApplication

user_database = {}
userid_seq = 1
chars = [chr(i) for i in range(ord('a'), ord('z'))]


def randchars(n):
    return ''.join(random.choice(chars) for _ in range(n))


class Permission(ComplexModel):
    __namespace__ = "permission"

    app = String(values=['library', 'delivery', 'accounting'])
    perms = String(min_occurs=1, max_occurs=2, values=['read', 'write'])


class User(ComplexModel):
    __namespace__ = "user"

    userid = Integer
    username = String
    firstname = String
    lastname = String
    permissions = Array(Permission)


# add superuser to the 'database'

all_permissions = (
    Permission(app='library', perms=['read', 'write']),
    Permission(app='delivery', perms=['read', 'write']),
    Permission(app='accounting', perms=['read', 'write']),
)


def randperms(n):
    for p in random.sample(all_permissions, n):
        yield Permission(app=p.app,
            perms=random.sample(p.perms, random.randint(1, 2)))


user_database[0] = User(
    userid=0,
    username='root',
    firstname='Super',
    lastname='User',
    permissions=all_permissions
)


def add_user(user):
    global user_database
    global userid_seq

    user.userid = userid_seq
    userid_seq = userid_seq + 1
    user_database[user.userid] = user


class UserManager(Service):
    @rpc(User, _returns=Integer)
    def add_user(ctx, user):
        add_user(user)
        return user.userid

    @rpc(_returns=User)
    def super_user(ctx):
        return user_database[0]

    @rpc(_returns=User)
    def random_user(ctx):
        retval = User(
            username=randchars(random.randrange(3, 12)),
            firstname=randchars(random.randrange(3, 12)).title(),
            lastname=randchars(random.randrange(3, 12)).title(),
            permissions=randperms(random.randint(1, len(all_permissions)))
        )

        add_user(retval)

        return retval

    @rpc(Integer, _returns=User)
    def get_user(ctx, userid):
        global user_database

        # If you rely on dict lookup raising KeyError here, you'll return an
        # internal error to the client, which tells the client that there's
        # something wrong in the server. However in this case, KeyError means
        # invalid request, so it's best to return a client error.

        # For the HttpRpc case, internal error is 500 whereas
        # ResourceNotFoundError is 404.
        if not (userid in user_database):
            raise ResourceNotFoundError(userid)

        return user_database[userid]

    @rpc(User)
    def modify_user(ctx, user):
        global user_database

        if not (user.userid in user_database):
            raise ResourceNotFoundError(user.userid)

        user_database[user.userid] = user

    @rpc(Integer)
    def delete_user(ctx, userid):
        global user_database

        if not (userid in user_database):
            raise ResourceNotFoundError(userid)

        del user_database[userid]

    @rpc(_returns=Array(User))
    def list_users(ctx):
        global user_database

        return user_database.values()


if __name__ == '__main__':
    from wsgiref.simple_server import make_server

    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger('spyne.protocol.xml').setLevel(logging.DEBUG)

    application = Application([UserManager], 'spyne.examples.complex',
                              in_protocol=HttpRpc(), out_protocol=XmlDocument())

    server = make_server('127.0.0.1', 8000, WsgiApplication(application))

    logging.info("listening to http://127.0.0.1:8000")
    logging.info("wsdl is at: http://localhost:8000/?wsdl")

    server.serve_forever()
