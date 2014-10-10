
from spyne import Integer, ModelBase
from spyne.util.cdict import cdict


MAP = cdict({
    ModelBase: cdict({object: lambda _:_, basestring: lambda _:_}),
    Integer: cdict({
        int: lambda _:_,
        basestring: lambda s: None if s == '' else int(s),
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
