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

import logging
logger = logging.getLogger(__name__)

import copy

from lxml import etree

from spyne.protocol import ProtocolBase
from spyne.model.primitive import DateTime

clock = etree.fromstring(open('clock.svg','r').read())
ns = {'x': 'http://www.w3.org/2000/svg'}

class SvgClock(ProtocolBase):
    mime_type = 'image/svg+xml'

    def __init__(self, app=None):
        super(SvgClock, self).__init__(app, validator=None)

        self.length = 500 # if you change this, you should re-scale the svg file
                          # as well.

    def serialize(self, ctx, message):
        """Uses a datetime.datetime instance inside ctx.out_object[0] to set
        ctx.out_document to an lxml.etree._Element instance.
        """

        # this is an output-only protocol
        assert message in (self.RESPONSE,)

        # this protocol can only handle DateTime types.
        return_type = ctx.descriptor.out_message._type_info[0]

        assert issubclass(return_type, DateTime), \
               "This protocol only supports functions with %r as return " \
               "type" % DateTime

        # Finally, start serialization.
        self.event_manager.fire_event('before_serialize', ctx)

        ctx.out_header_doc = None
        ctx.out_body_doc = copy.deepcopy(clock)

        d = ctx.out_object[0] # this has to be a datetime.datetime instance.

        # set the current date
        ctx.out_body_doc.xpath("//x:tspan[@id='date_text']", namespaces=ns)[0] \
                .text = '%04d-%02d-%02d' % (d.year, d.month, d.day)

        minute_hand = d.minute * 360 / 60;
        hour_hand = (d.hour % 12) * 360.0 / 12 + minute_hand / 12;
        ctx.out_body_doc.xpath("//x:path[@id='akrep']", namespaces=ns)[0] \
            .attrib['transform'] += \
            ' rotate(%d, %d, %d)' % (hour_hand, self.length /2, self.length / 2)
        ctx.out_body_doc.xpath("//x:path[@id='yelkovan']", namespaces=ns)[0] \
            .attrib['transform'] += \
            ' rotate(%d, %d, %d)' % (minute_hand, self.length /2, self.length /2)

        ctx.out_document = ctx.out_body_doc

        self.event_manager.fire_event('after_serialize', ctx)

    def create_out_string(self, ctx, charset=None):
        """Sets an iterable of string fragments to ctx.out_string"""

        ctx.out_string = [etree.tostring(ctx.out_document, pretty_print=True,
                                         encoding='utf8', xml_declaration=True)]

    def decompose_incoming_envelope(self, ctx, message):
        raise NotImplementedError("This is an output-only protocol.")

class PngClock(SvgClock):
    mime_type = 'image/png'

    def create_out_string(self, ctx, charset=None):
        """Sets an iterable of string fragments to ctx.out_string"""

        import rsvg
        from gtk import gdk

        h = rsvg.Handle()
        h.write(etree.tostring(ctx.out_document))
        h.close()

        pixbuf = h.get_pixbuf()

        ctx.out_string = []

        def cb(buf, data=None):
            ctx.out_string.append(buf)
            return True

        pixbuf.save_to_callback(cb, 'png')
