
#
# rpclib - Copyright (C) Rpclib contributors.
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301
#

import logging
logger = logging.getLogger(__name__)

import copy

from lxml import etree

from rpclib.protocol import ProtocolBase

clock = etree.fromstring(open('clock.svg','r').read())
ns = {'x': 'http://www.w3.org/2000/svg'}

class SvgClock(ProtocolBase):
    mime_type = 'image/svg+xml'

    def __init__(self, app=None, length=500):
        """Protocol that returns a PNG Clock picture based on a received datetime
        object.

        :param app: A rpclib.application.Application instance.
        :param length: The length of the edge of the produced square image, in pixels.
        """

        ProtocolBase.__init__(self, app, validator=None)

        self.length = length

    def serialize(self, ctx, message):
        """Uses ctx.out_object, ctx.out_header or ctx.out_error to set
        ctx.out_body_doc, ctx.out_header_doc and ctx.out_document.
        """

        assert message in (self.RESPONSE,)

        self.event_manager.fire_event('before_serialize', ctx)
        ctx.out_header_doc = None
        ctx.out_body_doc = copy.deepcopy(clock)

        ctx.out_body_doc.xpath("//x:flowPara[@id='date_text']", namespaces=ns)[0] \
                .text = '%04d-%02d-%02d' % (d.year, d.month, d.day)

        d = ctx.out_object[0]
        yelkovan_deg = d.minute * 360 / 60;
        akrep_deg = (d.hour % 12) * 360.0 / 12 + yelkovan_deg / 12;
        ctx.out_body_doc.xpath("//x:path[@id='akrep']", namespaces=ns)[0] \
            .attrib['transform'] += \
            ' rotate(%d, %d, %d)' % (akrep_deg, self.length /2, self.length / 2)
        ctx.out_body_doc.xpath("//x:path[@id='yelkovan']", namespaces=ns)[0] \
            .attrib['transform'] += \
            ' rotate(%d, %d, %d)' % (yelkovan_deg, self.length /2, self.length / 2)

        ctx.out_document = ctx.out_body_doc

        self.event_manager.fire_event('after_serialize', ctx)

    def create_out_string(self, ctx, charset=None):
        """Sets an iterable of string fragments to ctx.out_string"""

        ctx.out_string = [etree.tostring(ctx.out_document, pretty_print=True,
                                         encoding='utf8', xml_declaration=True)]

    def decompose_incoming_envelope(self, ctx, message):
        raise NotImplementedError("This is an output-only protocol.")
