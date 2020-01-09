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

"""Use:

    curl http://localhost:9912/get_name_of_month?month=12

to use this service.
"""

host = '127.0.0.1'
port = 8000

import logging

from datetime import datetime

from spyne import Integer, Unicode, rpc, Service


class NameOfMonthService(Service):
    @rpc(Integer(ge=1, le=12), _returns=Unicode)
    def get_name_of_month(ctx, month):
        return datetime(2000, month, 1).strftime("%B")


from spyne.application import Application
from spyne.protocol.http import HttpRpc

rest = Application([NameOfMonthService],
        tns='spyne.examples.multiprot',
        in_protocol=HttpRpc(validator='soft'),
        out_protocol=HttpRpc()
    )

from spyne.server.wsgi import WsgiApplication
from wsgiref.simple_server import make_server

server = make_server(host, port, WsgiApplication(rest))

logging.basicConfig(level=logging.DEBUG)
logging.info("listening to http://%s:%d" % (host, port))

server.serve_forever()
