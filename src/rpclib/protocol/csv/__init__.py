
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

try:
    from cStringIO import StringIO
except ImportError: # Python 3
    from io import StringIO

from rpclib.protocol import ProtocolBase

def complex_to_csv(ctx):
    cls, = ctx.descriptor.out_message._type_info.values()

    queue = StringIO()
    writer = csv.writer(queue, dialect=csv.excel)

    serializer, = cls._type_info.values()

    type_info = getattr(serializer, '_type_info',
                                  {serializer.get_type_name(): serializer})

    keys = sorted(type_info.keys())

    if ctx.out_error is None and ctx.out_object is None:
        writer.writerow(['Error in generating the document'])
        for r in ctx.out_error.to_string_iterable(ctx.out_error):
            writer.writerow([r])

        yield queue.getvalue()
        queue.truncate(0)

    elif ctx.out_error is None:
        writer.writerow(keys)
        yield queue.getvalue()
        queue.truncate(0)

        if ctx.out_object[0] is not None:
            for v in ctx.out_object[0]:
                d = serializer.to_dict(v)
                row = [ ]
                for k in keys:
                    val = d.get(k, None)
                    if val:
                        val=val.encode('utf8')
                    row.append(val)

                writer.writerow(row)
                yield queue.getvalue()
                queue.truncate(0)

class OutCsv(ProtocolBase):
    mime_type = 'text/csv'

    def create_in_document(self, ctx):
        raise Exception("not supported")

    def serialize(self, ctx, message):
        assert message in (self.RESPONSE,)

        if ctx.out_object is None:
            ctx.out_object = []

        assert len(ctx.descriptor.out_message._type_info) == 1, """CSV Serializer
            supports functions with exactly one return type:
            %r""" % ctx.descriptor.out_message._type_info

        ctx.out_string = complex_to_csv(ctx)
        ctx.transport.resp_headers['Content-Disposition'] = (
                    'attachment; filename=%s.csv;' % ctx.descriptor.name)
