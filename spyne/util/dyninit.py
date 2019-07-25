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

from spyne import D, Integer, ModelBase, Date, DateTime, IpAddress, Decimal, \
    Boolean
from spyne.protocol import ProtocolBase
from spyne.util import six
from spyne.util.cdict import cdict


BOOL_VALUES_BYTES_TRUE  = (b't', b'1', b'on', b'yes', b'true')
BOOL_VALUES_STR_TRUE    = (u't', u'1', u'on', u'yes', u'true')

BOOL_VALUES_BYTES_FALSE = (b'f', b'0', b'off', b'no', b'false')
BOOL_VALUES_STR_FALSE   = (u'f', u'0', u'off', u'no', u'false')

BOOL_VALUES_NONE = (None, '')


if six.PY2:
    bytes = str
else:
    unicode = str


_prot = ProtocolBase()

def _bool_from_int(i):
    if i in (0, 1):
        return i == 1
    raise ValueError(i)


def _bool_from_bytes(s):
    if s in BOOL_VALUES_NONE:
        return None

    s = s.strip()
    if s in BOOL_VALUES_NONE:
        return None
    s = s.lower()
    if s in BOOL_VALUES_BYTES_TRUE:
        return True
    if s in BOOL_VALUES_BYTES_FALSE:
        return False
    raise ValueError(s)


def _bool_from_str(s):
    if s in BOOL_VALUES_NONE:
        return None

    s = s.strip()
    if s in BOOL_VALUES_NONE:
        return None
    if s in BOOL_VALUES_STR_TRUE:
        return True
    if s in BOOL_VALUES_STR_FALSE:
        return False
    raise ValueError(s)


MAP = cdict({
    ModelBase: cdict({
        object: lambda _: _,
        bytes: lambda _: _.strip(),
        unicode: lambda _: _.strip(),
    }),

    Decimal: cdict({
        D: lambda d: d,
        int: lambda i: D(i),
        bytes: lambda s: None if s.strip() == '' else D(s.strip()),
        unicode: lambda s: None if s.strip() == u'' else D(s.strip()),
    }),

    Boolean: cdict({
        D: lambda d: _bool_from_int(int(d)),
        int: _bool_from_int,
        bytes: _bool_from_bytes,
        unicode: _bool_from_str,
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
