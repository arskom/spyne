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


'''
This example shows how to override the variable names for fun and profit.
This is very useful for situations that require the use of variable names
that are python keywords like, from, import, return, etc.
'''


import logging

from spyne.application import Application
from spyne.decorator import srpc
from spyne.protocol.soap import Soap11
from spyne.service import ServiceBase
from spyne.model.primitive import String
from spyne.model.complex import ComplexModel
from spyne.server.wsgi import WsgiApplication

from spyne.util.odict import odict


class SomeClass(ComplexModel):
    _type_info = odict([
        ('and', String),
        ('or', String),
    ])


class EmailManager(ServiceBase):
    @srpc(String, String, String, _returns=String,
        _in_variable_names={'from_': 'from'},
        _out_variable_name='return')
    def send_email(to, from_, message):
        # do email sending here
        return repr((to, from_, message, 'sent!'))

if __name__=='__main__':
    from wsgiref.simple_server import make_server

    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger('spyne.protocol.xml').setLevel(logging.DEBUG)

    application = Application([EmailManager], 'spyne.examples.events',
                                    in_protocol=Soap11(), out_protocol=Soap11())

    server = make_server('127.0.0.1', 8000, WsgiApplication(application))

    logging.info("listening to http://127.0.0.1:8000")
    logging.info("wsdl is at: http://localhost:8000/?wsdl")

    server.serve_forever()
