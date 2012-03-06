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
"""


import logging

from datetime import datetime

from rpclib.application import Application
from rpclib.decorator import srpc
from rpclib.interface.wsdl import Wsdl11
from rpclib.service import ServiceBase
from rpclib.util.wsgi_wrapper import WsgiMounter

from rpclib.model.primitive import DateTime

from rpclib.protocol.xml import XmlObject
from rpclib.protocol.soap import Soap11
from rpclib.protocol.http import HttpRpc
from rpclib.protocol.html import HtmlMicroFormat

from protocol import PngClock
from protocol import SvgClock


class HelloWorldService(ServiceBase):
    @srpc(_returns=DateTime)
    def get_utc_time():
        return datetime.utcnow()

if __name__ == '__main__':
    from wsgiref.simple_server import make_server

    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger('rpclib.protocol.xml').setLevel(logging.DEBUG)

    rest = Application([HelloWorldService],
            tns='rpclib.examples.multiple_protocols',
            interface=Wsdl11(), in_protocol=HttpRpc(), out_protocol=HttpRpc())

    xml = Application([HelloWorldService],
            tns='rpclib.examples.multiple_protocols',
            interface=Wsdl11(), in_protocol=HttpRpc(), out_protocol=XmlObject())

    soap = Application([HelloWorldService],
            tns='rpclib.examples.multiple_protocols',
            interface=Wsdl11(), in_protocol=HttpRpc(), out_protocol=Soap11())

    html = Application([HelloWorldService],
            tns='rpclib.examples.multiple_protocols',
            interface=Wsdl11(), in_protocol=HttpRpc(), out_protocol=HtmlMicroFormat())

    png = Application([HelloWorldService],
            tns='rpclib.examples.multiple_protocols',
            interface=Wsdl11(), in_protocol=HttpRpc(), out_protocol=PngClock())

    svg = Application([HelloWorldService],
            tns='rpclib.examples.multiple_protocols',
            interface=Wsdl11(), in_protocol=HttpRpc(), out_protocol=SvgClock())


    root = WsgiMounter({
        'rest': rest,
        'xml': xml,
        'soap': soap,
        'html': html,
        'png': png,
        'svg': svg,
    })

    server = make_server('127.0.0.1', 9910, root)

    logging.info("listening to http://127.0.0.1:7789")
    logging.info("wsdl is at: http://localhost:7789/?wsdl")

    server.serve_forever()
