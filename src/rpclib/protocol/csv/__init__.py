
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

import csv

from cStringIO import StringIO

from rpclib.protocol import ProtocolBase

def complex_to_csv(cls, values):
    queue = StringIO()
    writer = csv.writer(queue, dialect=csv.excel)

    serializer, = cls._type_info.values()

    type_info = getattr(serializer, '_type_info',
                                  {serializer.get_type_name(): serializer})

    keys = type_info.keys()
    keys.sort()

    writer.writerow(keys)
    yield queue.getvalue()
    queue.truncate(0)

    if values is not None:
        for v in values:
            d = serializer.to_dict(v)
            writer.writerow([d.get(k, None) for k in keys])
            yield queue.getvalue()
            queue.truncate(0)

class OutCsv(ProtocolBase):
    mime_type = 'text/csv'

    def create_in_document(self, ctx):
        raise Exception("not supported")

    def serialize(self, ctx):
        result_message_class = ctx.descriptor.out_message

        if ctx.out_object is None:
            ctx.out_object = []

        assert len(result_message_class._type_info) == 1, """CSV Serializer
            supports functions with exactly one return type:
            %r""" % result_message_class._type_info

        # assign raw result to its wrapper, result_message
        out_type, = result_message_class._type_info.itervalues()

        ctx.out_string = complex_to_csv(out_type, ctx.out_object)
