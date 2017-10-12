
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
        int: lambda _: D(_),
        bytes: lambda s: None if s.strip() == '' else D(s.strip()),
        unicode: lambda s: None if s.strip() == u'' else D(s.strip()),
    }),

    Integer: cdict({
        int: lambda _: _,
        bytes: lambda s: None if s.strip() == '' else int(s.strip()),
        unicode: lambda s: None if s.strip() == u'' else int(s.strip()),
    }),

    Date: cdict({
        object: lambda _:_,
        bytes: lambda s: None if s.strip() in ('', '0000-00-00')
                                   else _prot.date_from_string(Date, s.strip()),
        unicode: lambda s: None if s.strip() in (u'', u'0000-00-00')
                                   else _prot.date_from_string(Date, s.strip()),
    }),

    DateTime: cdict({
        object: lambda _:_,
        bytes: lambda s: None if s.strip() in ('', '0000-00-00 00:00:00')
                           else _prot.datetime_from_string(DateTime, s.strip()),
        unicode: lambda s: None if s.strip() in (u'', u'0000-00-00 00:00:00')
                           else _prot.datetime_from_string(DateTime, s.strip()),
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
