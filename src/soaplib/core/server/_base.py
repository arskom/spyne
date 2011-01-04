
#
# soaplib - Copyright (C) Soaplib contributors.
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

"""A soap server that uses http as transport, and wsgi as bridge api"""

from lxml import etree

import logging
logger = logging.getLogger(__name__)

from soaplib.core.model.exception import Fault
from soaplib.core.model.primitive import string_encoding

HTTP_500 = '500 Internal server error'
HTTP_200 = '200 OK'
HTTP_405 = '405 Method Not Allowed'

class ValidationError(Fault):
    pass

class Base(object):
    transport = None

    def __init__(self, app):
        self.app = app
        self.app.transport = self.transport

    def get_in_object(self, ctx, in_string, in_string_charset=None):
        in_object = None
        root, xmlids = self.app.parse_xml_string(in_string, in_string_charset)

        try:
            in_object = self.app.deserialize_soap(ctx, self.app.IN_WRAPPER,
                                                                   root, xmlids)
        except Fault,e:
            ctx.in_error = e

        return in_object

    def get_out_object(self, ctx, in_object):
        out_object = self.app.process_request(ctx, in_object)

        if isinstance(out_object, Fault):
            ctx.out_error = out_object
        else:
            assert not isinstance(out_object, Exception)

        return out_object

    def get_out_string(self, ctx, out_object):
        out_xml = self.app.serialize_soap(ctx, self.app.OUT_WRAPPER, out_object)
        out_string = etree.tostring(out_xml, xml_declaration=True,
                                                       encoding=string_encoding)
        return out_string
