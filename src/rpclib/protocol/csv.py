
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

from rpclib.protocol import Base

class OutCsv(Base):
    mime_type = 'text/csv'

    def create_in_document(self, ctx):
        raise Exception("not supported")

    def serialize(self, ctx):
        result_message_class = ctx.descriptor.out_message

        assert ctx.out_object != None
        assert len(result_message_class._type_info) == 1, """CSV Serializer
            supports functions with exactly one return type:
            %r""" % result_message_class._type_info

        # assign raw result to its wrapper, result_message
        out_type, = result_message_class._type_info.itervalues()

        ctx.out_string = out_type.to_csv(ctx.out_object)
