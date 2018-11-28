# encoding: utf-8
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

from datetime import date, datetime

from spyne import D, Integer, ModelBase, Date, DateTime, IpAddress, Decimal
from spyne.protocol import ProtocolBase
from spyne.util import six
from spyne.util.cdict import cdict


if six.PY2:
    bytes = str
else:
    unicode = str


_prot = ProtocolBase()


MAP = cdict({
    ModelBase: cdict({
        object: lambda _: _,
        bytes: lambda _: _.strip(),
        unicode: lambda _: _.strip(),
    }),

    Decimal: cdict({
        D: lambda _: _,
        int: lambda _: D(_),
        bytes: lambda s: None if s.strip() == '' else D(s.strip()),
        unicode: lambda s: None if s.strip() == u'' else D(s.strip()),
    }),

    Integer: cdict({
        D: lambda _: _,
        int: lambda _: _,
        bytes: lambda s: None if s.strip() == '' else int(s.strip()),
        unicode: lambda s: None if s.strip() == u'' else int(s.strip()),
    }),

    Date: cdict({
        date: lambda _: _,
        datetime: lambda _: _.date(),
        object: lambda _:_,
        bytes: lambda s: None if s.strip() in ('', '0000-00-00')
                                   else _prot.date_from_unicode(Date, s.strip()),
        unicode: lambda s: None if s.strip() in (u'', u'0000-00-00')
                                   else _prot.date_from_unicode(Date, s.strip()),
    }),

    DateTime: cdict({
        date: lambda _: datetime(date.year, date.month, date.day),
        datetime: lambda _: _,
        object: lambda _:_,
        bytes: lambda s: None if s.strip() in ('', '0000-00-00 00:00:00')
                          else _prot.datetime_from_unicode(DateTime, s.strip()),
        unicode: lambda s: None if s.strip() in (u'', u'0000-00-00 00:00:00')
                          else _prot.datetime_from_unicode(DateTime, s.strip()),
    }),

    IpAddress: cdict({
        object: lambda _: _,
        bytes: lambda s: None if s.strip() == '' else s.strip(),
        unicode: lambda s: None if s.strip() == u'' else s.strip(),
    })
})


def dynamic_init(cls, **kwargs):
    fti = cls.get_flat_type_info(cls)
    retval = cls()

    for k, v in fti.items():
        if k in kwargs:
            subval = kwargs[k]
            t = MAP[v]
            setattr(retval, k, t[type(subval)](subval))

    return retval
