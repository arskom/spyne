
#
# spyne - Copyright (C) Spyne contributors.
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

"""The ``spyne.protocol.csv`` package contains the Csv output protocol.

This protocol is here merely for illustration purposes. While it is in a
somewhat working state, it is not that easy to use. Expect a revamp in the
coming versions.
"""

from __future__ import absolute_import

import logging
logger = logging.getLogger(__name__)

import csv

from spyne import ComplexModelBase
from spyne.util import six
from spyne.protocol.dictdoc import HierDictDocument

if six.PY2:
    from StringIO import StringIO
else:
    from io import StringIO


def _complex_to_csv(prot, ctx):
    cls, = ctx.descriptor.out_message._type_info.values()

    queue = StringIO()

    serializer, = cls._type_info.values()

    if issubclass(serializer, ComplexModelBase):
        type_info = serializer.get_flat_type_info(serializer)
        keys = [k for k, _ in prot.sort_fields(serializer)]

    else:
        type_info = {serializer.get_type_name(): serializer}
        keys = list(type_info.keys())

    if ctx.out_error is not None:
        writer = csv.writer(queue, dialect=csv.excel)
        writer.writerow(['Error in generating the document'])
        if ctx.out_error is not None:
            for r in ctx.out_error.to_bytes_iterable(ctx.out_error):
                writer.writerow([r])

        yield queue.getvalue()
        queue.truncate(0)

    else:
        writer = csv.DictWriter(queue, dialect=csv.excel, fieldnames=keys)
        if prot.header:
            titles = {}
            for k in keys:
                v = type_info[k]
                titles[k] = prot.trc(v, ctx.locale, k)

            writer.writerow(titles)

        yield queue.getvalue()
        queue.truncate(0)

        if ctx.out_object[0] is not None:
            for v in ctx.out_object[0]:
                d = prot._to_dict_value(serializer, v, set())
                if six.PY2:
                    for k in d:
                        if isinstance(d[k], unicode):
                            d[k] = d[k].encode('utf8')

                writer.writerow(d)
                yval = queue.getvalue()
                yield yval
                queue.truncate(0)


class Csv(HierDictDocument):
    mime_type = 'text/csv'
    text_based = True

    type = set(HierDictDocument.type)
    type.add('csv')

    def __init__(self, app=None, validator=None, mime_type=None,
            ignore_uncap=False, ignore_wrappers=True, complex_as=dict,
            ordered=False, polymorphic=False, header=True):

        super(Csv, self).__init__(app=app, validator=validator,
                        mime_type=mime_type, ignore_uncap=ignore_uncap,
                        ignore_wrappers=ignore_wrappers, complex_as=complex_as,
                        ordered=ordered, polymorphic=polymorphic)

        self.header = header

    def create_in_document(self, ctx):
        raise NotImplementedError()

    def serialize(self, ctx, message):
        assert message in (self.RESPONSE, )

        if ctx.out_object is None:
            ctx.out_object = []

        assert len(ctx.descriptor.out_message._type_info) == 1, \
            "CSV Serializer supports functions with exactly one return type: " \
            "%r" % ctx.descriptor.out_message._type_info

    def create_out_string(self, ctx):
        ctx.out_string = _complex_to_csv(self, ctx)
        if 'http' in ctx.transport.type:
            ctx.transport.resp_headers['Content-Disposition'] = (
                           'attachment; filename=%s.csv;' % ctx.descriptor.name)

    def any_uri_to_unicode(self, cls, value, **_):
        if isinstance(value, cls.Value):
            value = value.text
        return super(Csv, self).any_uri_to_unicode(cls, value, **_)
