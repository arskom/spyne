#!/usr/bin/env python
#encoding: utf8
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
import base64

from Cookie import SimpleCookie

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
from spyne.error import ResourceNotFoundError
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
                faultcode='Client.KeyError',
                faultstring='Value %r not found' % value
            )


class AuthenticationError(Fault):
    __namespace__ = 'spyne.examples.authentication'

    def __init__(self, user_name):
        # TODO: self.transport.http.resp_code = HTTP_401

        super(AuthenticationError, self).__init__(
                faultcode='Client.AuthenticationError',
                faultstring='Invalid authentication request for %r' % user_name
            )


class AuthorizationError(Fault):
    __namespace__ = 'spyne.examples.authentication'

    def __init__(self):
        # TODO: self.transport.http.resp_code = HTTP_401

        super(AuthorizationError, self).__init__(
                faultcode='Client.AuthorizationError',
                faultstring='You are not authorized to access this resource.'
            )

class UnauthenticatedError(Fault):
    __namespace__ = 'spyne.examples.authentication'

    def __init__(self):
        super(UnauthenticatedError, self).__init__(
                faultcode='Client.UnauthenticatedError',
                faultstring='This resource can only be accessed after authentication.'
            )

class SpyneDict(dict):
    def __getitem__(self, key):
        try:
            return dict.__getitem__(self, key)
        except KeyError:
            raise PublicKeyError(key)


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


class UserService(Service):
    __tns__ = 'spyne.examples.authentication'

    @rpc(Mandatory.String, Mandatory.String, _returns=None,
                                                    _throws=AuthenticationError)
    def authenticate(ctx, user_name, password):
        password_hash = user_db.get(user_name, None)

        if password_hash is None:
           raise AuthenticationError(user_name)

        if bcrypt.hashpw(password, password_hash) != password_hash:
           raise AuthenticationError(user_name)

        session_id = (user_name, '%x' % random.randint(1<<128, (1<<132)-1))
        session_db.add(session_id)

        cookie = SimpleCookie()
        cookie["session-id"] = base64.urlsafe_b64encode(str(session_id[0]) + "\0" + str(session_id[1]))
        cookie["session-id"]["max-age"] = 3600
        header_name, header_value = cookie.output().split(":", 1)
        ctx.transport.resp_headers[header_name] = header_value.strip()
        from pprint import pprint
        pprint(ctx.transport.resp_headers)


    @rpc(Mandatory.String, _throws=PublicKeyError, _returns=Preferences)
    def get_preferences(ctx, user_name):
        # Only allow access to the users own preferences.
        if user_name != ctx.udc:
            raise AuthorizationError()

        retval = preferences_db[user_name]

        return retval

def _on_method_call(ctx):
    if ctx.descriptor.name == "authenticate":
        # No checking of session cookie for call to authenticate
        return

    cookie = SimpleCookie()
    http_cookie = ctx.transport.req_env.get("HTTP_COOKIE")
    if http_cookie:
        cookie.load(http_cookie)
    if "session-id" not in cookie:
        raise UnauthenticatedError()
    session_cookie = cookie["session-id"].value
    session_id = tuple(base64.urlsafe_b64decode(session_cookie).split("\0", 1))
    if not session_id in session_db:
        raise AuthenticationError(session_id[0])
    ctx.udc = session_id[0]     # user name


UserService.event_manager.add_listener('method_call', _on_method_call)

if __name__=='__main__':
    from spyne.util.wsgi_wrapper import run_twisted

    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger('spyne.protocol.xml').setLevel(logging.DEBUG)
    logging.getLogger('twisted').setLevel(logging.DEBUG)

    application = Application([UserService],
        tns='spyne.examples.authentication',
        in_protocol=Soap11(validator='lxml'),
        out_protocol=Soap11()
    )

    twisted_apps = [
        (WsgiApplication(application), 'app'),
    ]

    sys.exit(run_twisted(twisted_apps, 8000))
