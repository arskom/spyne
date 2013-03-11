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

"""This is a gallery of protocols. Visit the following urls in a browser to get
the same information in different protocols.:

    http://localhost:9910/xml/get_utc_time
    http://localhost:9910/svg/get_utc_time
    http://localhost:9910/html/get_utc_time
    http://localhost:9910/rest/get_utc_time
    http://localhost:9910/soap/get_utc_time
    http://localhost:9910/png/get_utc_time
    http://localhost:9910/svg/get_utc_time
    http://localhost:9910/json0/get_utc_time
    http://localhost:9910/json1/get_utc_time
    http://localhost:9910/json2/get_utc_time
    http://localhost:9910/mpo/get_utc_time
    http://localhost:9910/mprpc/get_utc_time
"""


import logging

from datetime import datetime

from spyne.application import Application
from spyne.decorator import srpc
from spyne.service import ServiceBase
from spyne.util.wsgi_wrapper import WsgiMounter

from spyne.model.primitive import DateTime

from spyne.protocol.xml import XmlDocument
from spyne.protocol.soap import Soap11
from spyne.protocol.http import HttpRpc
from spyne.protocol.html import HtmlMicroFormat
from spyne.protocol.json import JsonDocument
from spyne.protocol.msgpack import MessagePackDocument
from spyne.protocol.msgpack import MessagePackRpc
from spyne.protocol.yaml import YamlDocument

from protocol import PngClock
from protocol import SvgClock

tns = 'spyne.examples.multiple_protocols'
port = 9910
host = '127.0.0.1'

class HelloWorldService(ServiceBase):
    @srpc(_returns=DateTime)
    def get_utc_time():
        return datetime.utcnow()

if __name__ == '__main__':
    rest = Application([HelloWorldService], tns=tns,
            in_protocol=HttpRpc(), out_protocol=HttpRpc())

    xml = Application([HelloWorldService], tns=tns,
            in_protocol=HttpRpc(), out_protocol=XmlDocument())

    soap = Application([HelloWorldService], tns=tns,
            in_protocol=HttpRpc(), out_protocol=Soap11())

    html = Application([HelloWorldService], tns=tns,
            in_protocol=HttpRpc(), out_protocol=HtmlMicroFormat())

    png = Application([HelloWorldService], tns=tns,
            in_protocol=HttpRpc(), out_protocol=PngClock())

    svg = Application([HelloWorldService], tns=tns,
            in_protocol=HttpRpc(), out_protocol=SvgClock())

    json0 = Application([HelloWorldService], tns=tns,
            in_protocol=HttpRpc(), out_protocol=JsonDocument())

    json1 = Application([HelloWorldService], tns=tns,
            in_protocol=HttpRpc(), out_protocol=JsonDocument(skip_depth=1))

    json2 = Application([HelloWorldService], tns=tns,
            in_protocol=HttpRpc(), out_protocol=JsonDocument(skip_depth=2))

    json22 = Application([HelloWorldService], tns=tns,
            in_protocol=HttpRpc(), out_protocol=JsonDocument(skip_depth=22))

    msgpack_doc = Application([HelloWorldService], tns=tns,
            in_protocol=HttpRpc(), out_protocol=MessagePackDocument())

    msgpack_rpc = Application([HelloWorldService], tns=tns,
            in_protocol=HttpRpc(), out_protocol=MessagePackRpc())

    yaml = Application([HelloWorldService], tns=tns,
            in_protocol=HttpRpc(), out_protocol=YamlDocument())

    root = WsgiMounter({
        'rest': rest,
        'xml': xml,
        'soap': soap,
        'html': html,
        'png': png,
        'svg': svg,
        'json': json0,
        'json0': json0,
        'json1': json1,
        'json2': json2,
        'json22': json22,
        'mpd': msgpack_doc,
        'mprpc': msgpack_rpc,
        'yaml': yaml,
    })

    from wsgiref.simple_server import make_server
    server = make_server(host, port, root)

    logging.basicConfig(level=logging.DEBUG)
    logging.info("listening to http://%s:%d" % (host, port))
    logging.info("navigate to e.g. http://%s:%d/json2/get_utc_time" % (host, port))
    logging.info("navigate to e.g. http://%s:%d/xml/get_utc_time" % (host, port))

    server.serve_forever()
