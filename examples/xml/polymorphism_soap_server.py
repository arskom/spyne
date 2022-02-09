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

import sys

from datetime import datetime
from spyne.protocol.soap import Soap11
from spyne.server.wsgi import WsgiApplication

from spyne.util.cherry import cherry_graft_and_start
from spyne import DateTime, Unicode, Integer, ComplexModel, rpc, Application, \
    Service


class A(ComplexModel):
    i = Integer


class B(A):
    s = Unicode


class C(A):
    d = DateTime


class SomeService(Service):
    @rpc(Unicode(values=['A', 'B', 'C']), _returns=A)
    def get_some_a(self, type_name):
        if type_name == 'A':
            return A(i=1)

        if type_name == 'B':
            return B(i=2, s='s')

        if type_name == 'C':
            return C(i=3, d=datetime.utcnow())


application = Application([SomeService], 'tns',
    in_protocol=Soap11(validator='lxml'),
    out_protocol=Soap11(polymorphic=True)
)

sys.exit(cherry_graft_and_start(WsgiApplication(application)))
