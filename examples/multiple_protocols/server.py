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
    http://localhost:9910/html/get_utc_time
    http://localhost:9910/rest/get_utc_time
    http://localhost:9910/soap/get_utc_time
    http://localhost:9910/png/get_utc_time
    http://localhost:9910/svg/get_utc_time
    http://localhost:9910/json/get_utc_time
    http://localhost:9910/jsoni/get_utc_time
    http://localhost:9910/jsonl/get_utc_time
    http://localhost:9910/jsonil/get_utc_time
    http://localhost:9910/mpo/get_utc_time
    http://localhost:9910/mpr/get_utc_time
    http://localhost:9910/yaml/get_utc_time

You need python bindings for librsvg for svg & png protocols.

    # debian/ubuntu
    apt-get install python-rsvg

    # gentoo
    emerge librsvg-python

along with every other otherwise optional Spyne dependency.
"""

import logging

from datetime import datetime

from protocol import PngClock
from protocol import SvgClock

from spyne import Application, rpc, srpc, DateTime, String, Service
from spyne.protocol.html import HtmlMicroFormat
from spyne.protocol.http import HttpPattern, HttpRpc
from spyne.protocol.json import JsonDocument
from spyne.protocol.msgpack import MessagePackDocument, MessagePackRpc
from spyne.protocol.soap import Soap11
from spyne.protocol.xml import XmlDocument
from spyne.protocol.yaml import YamlDocument
from spyne.util.wsgi_wrapper import WsgiMounter

tns = 'spyne.examples.multiple_protocols'
port = 9910
host = '127.0.0.1'


class MultiProtService(Service):
    @srpc(_returns=DateTime)
    def get_utc_time():
        return datetime.utcnow()


def Tsetprot(prot):
    def setprot(ctx):
        ctx.out_protocol = prot

    return setprot


class DynProtService(Service):
    protocols = {}

    @rpc(String(values=protocols.keys(), encoding='ascii'), _returns=DateTime,
        _patterns=[HttpPattern('/get_utc_time\\.<prot>')])
    def get_utc_time(ctx, prot):
        DynProtService.protocols[prot](ctx)

        return datetime.utcnow()


def main():
    rest = Application([MultiProtService], tns=tns,
        in_protocol=HttpRpc(), out_protocol=HttpRpc())

    xml = Application([MultiProtService], tns=tns,
        in_protocol=HttpRpc(), out_protocol=XmlDocument())

    soap = Application([MultiProtService], tns=tns,
        in_protocol=HttpRpc(), out_protocol=Soap11())

    html = Application([MultiProtService], tns=tns,
        in_protocol=HttpRpc(), out_protocol=HtmlMicroFormat())

    png = Application([MultiProtService], tns=tns,
        in_protocol=HttpRpc(), out_protocol=PngClock())

    svg = Application([MultiProtService], tns=tns,
        in_protocol=HttpRpc(), out_protocol=SvgClock())

    json = Application([MultiProtService], tns=tns,
        in_protocol=HttpRpc(), out_protocol=JsonDocument())

    jsoni = Application([MultiProtService], tns=tns,
        in_protocol=HttpRpc(), out_protocol=JsonDocument(ignore_wrappers=False))

    jsonl = Application([MultiProtService], tns=tns,
        in_protocol=HttpRpc(), out_protocol=JsonDocument(complex_as=list))

    jsonil = Application([MultiProtService], tns=tns,
        in_protocol=HttpRpc(),
        out_protocol=JsonDocument(ignore_wrappers=False, complex_as=list))

    msgpack_obj = Application([MultiProtService], tns=tns,
        in_protocol=HttpRpc(), out_protocol=MessagePackDocument())

    msgpack_rpc = Application([MultiProtService], tns=tns,
        in_protocol=HttpRpc(), out_protocol=MessagePackRpc())

    yaml = Application([MultiProtService], tns=tns,
        in_protocol=HttpRpc(), out_protocol=YamlDocument())

    dyn = Application([DynProtService], tns=tns,
        in_protocol=HttpRpc(validator='soft'), out_protocol=HttpRpc())

    DynProtService.protocols = {
        'json': Tsetprot(JsonDocument(dyn)),
        'xml': Tsetprot(XmlDocument(dyn)),
        'yaml': Tsetprot(YamlDocument(dyn)),
        'soap': Tsetprot(Soap11(dyn)),
        'html': Tsetprot(HtmlMicroFormat(dyn)),
        'png': Tsetprot(PngClock(dyn)),
        'svg': Tsetprot(SvgClock(dyn)),
        'msgpack': Tsetprot(MessagePackDocument(dyn)),
    }

    root = WsgiMounter({
        'rest': rest,
        'xml': xml,
        'soap': soap,
        'html': html,
        'png': png,
        'svg': svg,
        'json': json,
        'jsoni': jsoni,
        'jsonl': jsonl,
        'jsonil': jsonil,
        'mpo': msgpack_obj,
        'mpr': msgpack_rpc,
        'yaml': yaml,
        'dyn': dyn,
    })

    from wsgiref.simple_server import make_server
    server = make_server(host, port, root)

    logging.basicConfig(level=logging.DEBUG)
    logging.info("listening to http://%s:%d" % (host, port))
    logging.info("navigate to e.g. http://%s:%d/json/get_utc_time" %
                                                                   (host, port))
    logging.info("             or: http://%s:%d/xml/get_utc_time" %
                                                                   (host, port))

    return server.serve_forever()


if __name__ == '__main__':
    import sys

    sys.exit(main())
