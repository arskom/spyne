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
import random
import sys

# bcrypt seems to be among the latest consensus around cryptograpic circles on
# storing passwords.
# You need the package from http://code.google.com/p/py-bcrypt/
# You can install it by running easy_install py-bcrypt.
try:
    import bcrypt
except ImportError:
    print('easy_install --user py-bcrypt to get it.')
    raise

from spyne.application import Application
from spyne.decorator import rpc
from spyne.error import ArgumentError
from spyne.model.complex import ComplexModel
from spyne.model.fault import Fault
from spyne.model.primitive import Mandatory
from spyne.model.primitive import String
from spyne.protocol.soap import Soap11
from spyne.server.wsgi import WsgiApplication
from spyne.service import Service


class PublicKeyError(Fault):
    __namespace__ = 'spyne.examples.authentication'

    def __init__(self, value):
        super(PublicKeyError, self).__init__(
                                       faultstring='Value %r not found' % value)


class AuthenticationError(Fault):
    __namespace__ = 'spyne.examples.authentication'

    def __init__(self, user_name):
        # TODO: self.transport.http.resp_code = HTTP_401

        super(AuthenticationError, self).__init__(
                faultcode='Client.AuthenticationError',
                faultstring='Invalid authentication request for %r' % user_name)


class AuthorizationError(Fault):
    __namespace__ = 'spyne.examples.authentication'

    def __init__(self):
        # TODO: self.transport.http.resp_code = HTTP_401

        super(AuthorizationError, self).__init__(
                   faultcode='Client.AuthorizationError',
                   faultstring='You are not authozied to access this resource.')


class SpyneDict(dict):
    def __getitem__(self, key):
        try:
            return dict.__getitem__(self, key)
        except KeyError:
            raise PublicKeyError(key)


class RequestHeader(ComplexModel):
    __namespace__ = 'spyne.examples.authentication'

    session_id = Mandatory.String
    user_name = Mandatory.String


class Preferences(ComplexModel):
    __namespace__ = 'spyne.examples.authentication'

    language = String(max_len=2)
    time_zone = String


user_db = {
    'neo': bcrypt.hashpw('Wh1teR@bbit', bcrypt.gensalt()),
}

session_db = set()

preferences_db = SpyneDict({
    'neo': Preferences(language='en', time_zone='Underground/Zion'),
    'smith': Preferences(language='xx', time_zone='Matrix/Core'),
})


class AuthenticationService(Service):
    __tns__ = 'spyne.examples.authentication'

    @rpc(Mandatory.String, Mandatory.String, _returns=String,
                                                    _throws=AuthenticationError)
    def authenticate(ctx, user_name, password):
        password_hash = user_db.get(user_name, None)

        if password_hash is None:
            raise AuthenticationError(user_name)

        if bcrypt.hashpw(password, password_hash) == password_hash:
            session_id = (user_name,
                                '%x' % random.randint(1 << 124, (1 << 128) - 1))
            session_db.add(session_id)

        else:
            raise AuthenticationError(user_name)

        return session_id[1]


class UserService(Service):
    __tns__ = 'spyne.examples.authentication'
    __in_header__ = RequestHeader

    @rpc(Mandatory.String, _throws=PublicKeyError, _returns=Preferences)
    def get_preferences(ctx, user_name):
        if user_name == 'smith':
            raise AuthorizationError()

        retval = preferences_db[user_name]

        return retval


def _on_method_call(ctx):
    if ctx.in_object is None:
        raise ArgumentError("RequestHeader is null")
    if not (ctx.in_header.user_name, ctx.in_header.session_id) in session_db:
        raise AuthenticationError(ctx.in_object.user_name)


UserService.event_manager.add_listener('method_call', _on_method_call)

if __name__ == '__main__':
    from spyne.util.wsgi_wrapper import run_twisted

    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger('spyne.protocol.xml').setLevel(logging.DEBUG)
    logging.getLogger('twisted').setLevel(logging.DEBUG)

    application = Application([AuthenticationService, UserService],
        tns='spyne.examples.authentication',
        in_protocol=Soap11(validator='lxml'),
        out_protocol=Soap11()
    )

    twisted_apps = [
        (WsgiApplication(application), 'app'),
    ]

    sys.exit(run_twisted(twisted_apps, 8000))
