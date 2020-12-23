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

from pprint import pformat

from spyne.util.six.moves.http_cookies import SimpleCookie

# bcrypt seems to be among the latest consensus around cryptograpic circles on
# storing passwords.
# You need the package from http://code.google.com/p/py-bcrypt/
# You can install it by running easy_install py-bcrypt.
try:
    import bcrypt
except ImportError:
    print('easy_install --user py-bcrypt to get it.')
    raise

from spyne import Unicode, Application, rpc, Service
from spyne import M, ComplexModel, Fault, String
from spyne import ResourceNotFoundError
from spyne.protocol.soap import Soap11
from spyne.server.wsgi import WsgiApplication


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
    'neo': bcrypt.hashpw(b'Wh1teR@bbit', bcrypt.gensalt()),
}

session_db = set()

preferences_db = SpyneDict({
    'neo': Preferences(language='en', time_zone='Underground/Zion'),
    'smith': Preferences(language='xx', time_zone='Matrix/Core'),
})


class Encoding:
    SESSION_ID = 'ascii'
    USER_NAME = PASSWORD = CREDENTIALS = 'utf8'


class UserService(Service):
    __tns__ = 'spyne.examples.authentication'

    @rpc(M(Unicode), M(Unicode),  _throws=AuthenticationError)
    def authenticate(ctx, user_name, password):
        ENC_C = Encoding.CREDENTIALS
        ENC_SID = Encoding.SESSION_ID

        password_hash = user_db.get(user_name, None)

        if password_hash is None:
           raise AuthenticationError(user_name)

        password_b = password.encode(ENC_C)
        if bcrypt.hashpw(password_b, password_hash) != password_hash:
           raise AuthenticationError(user_name)

        session_id = '%x' % (random.randint(1<<128, (1<<132)-1))
        session_key = (
            user_name.encode(ENC_C),
            session_id.encode(ENC_SID),
        )
        session_db.add(session_key)

        cookie = SimpleCookie()
        cookie["session-id"] = \
            base64.urlsafe_b64encode(b"\0".join(session_key)) \
                .decode('ascii')  # find out how to do urlsafe_b64encodestring

        cookie["session-id"]["max-age"] = 3600
        header_name, header_value = cookie.output().split(":", 1)
        ctx.transport.resp_headers[header_name] = header_value.strip()

        logging.debug("Response headers: %s", pformat(ctx.transport.resp_headers))


    @rpc(M(String), _throws=PublicKeyError, _returns=Preferences)
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

    logging.debug("Request headers: %s", pformat(ctx.transport.req_env))

    cookie = SimpleCookie()
    http_cookie = ctx.transport.req_env.get("HTTP_COOKIE")
    if http_cookie:
        cookie.load(http_cookie)

    if "session-id" not in cookie:
        raise UnauthenticatedError()

    session_cookie = cookie["session-id"].value

    user_name, session_id = base64.urlsafe_b64decode(session_cookie) \
        .split(b"\0", 1)

    session_id = tuple(base64.urlsafe_b64decode(session_cookie).split(b"\0", 1))
    if not session_id in session_db:
        raise AuthenticationError(session_id[0])

    ctx.udc = session_id[0].decode(Encoding.USER_NAME)


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

    wsgi_app = WsgiApplication(application)
    wsgi_app.doc.wsdl11.xsl_href = "wsdl-viewer.xsl"

    twisted_apps = [
        (wsgi_app, b'app'),
    ]

    sys.exit(run_twisted(twisted_apps, 8000))
