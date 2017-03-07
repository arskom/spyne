# encoding: utf8
#
# Copyright © Anton Egorov <anton.egoroff@gmail.com>
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
from spyne.decorator import rpc
from spyne.model.complex import Iterable
from spyne.model.primitive import Integer, Unicode
from spyne.protocol.http import HttpRpc
from spyne.protocol.json import JsonDocument
from spyne.service import Service


class HelloWorldService(Service):
    @rpc(Unicode, Integer, _returns=Iterable(Unicode))
    def hello(ctx, name, times):
        name = name or ctx.udc.config['HELLO']
        for i in range(times):
            yield u'Hello, %s' % name


class UserDefinedContext(object):
    def __init__(self, flask_config):
        self.config = flask_config


def create_app(flask_app):
    '''Creates SOAP services application and distribute Flask config into
    user con defined context for each method call.
    '''
    application = Application(
        [HelloWorldService], 'spyne.examples.flask',
        # The input protocol is set as HttpRpc to make our service easy to call.
        in_protocol=HttpRpc(validator='soft'),
        out_protocol=JsonDocument(ignore_wrappers=True),
    )

    # Use `method_call` hook to pass flask config to each service method
    # context. But if you have any better ideas do it, make a pull request.
    # NOTE. I refuse idea to wrap each call into Flask application context
    # because in fact we inside Spyne app context, not the Flask one.
    def _flask_config_context(ctx):
        ctx.udc = UserDefinedContext(flask_app.config)
    application.event_manager.add_listener('method_call', _flask_config_context)

    return application
