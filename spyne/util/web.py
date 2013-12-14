
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

"""
An opinionated web framework built on top of Spyne, SQLAlchemy and Twisted.

If you're using this for anything serious, you're insane.
"""

from __future__ import absolute_import

import six

from spyne import BODY_STYLE_WRAPPED
from spyne.application import Application as AppBase
from spyne.const import MAX_STRING_FIELD_LENGTH
from spyne.const import MAX_ARRAY_ELEMENT_NUM
from spyne.error import Fault
from spyne.error import InternalError
from spyne.error import ResourceNotFoundError
from spyne.service import ServiceBase
from spyne.util import memoize
from spyne.util.email import email_exception
from spyne.model import Unicode
from spyne.model import Array
from spyne.model import ComplexModelBase

from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound

from twisted.python import log
from twisted.python.threadpool import ThreadPool
from twisted.internet import reactor
from twisted.internet.threads import deferToThreadPool


EXCEPTION_ADDRESS = None


try:
    import colorama
    colorama.init()

    from colorama.ansi import Fore
    from colorama.ansi import Style
    RED = Fore.RED + Style.BRIGHT
    GREEN = Fore.GREEN + Style.BRIGHT
    RESET = Style.RESET_ALL

except ImportError:
    RED = ""
    GREEN = ""
    RESET = ""


class ReaderServiceBase(ServiceBase):
    pass


class WriterServiceBase(ServiceBase):
    pass


def _on_method_call(ctx):
    ctx.udc = Context(ctx.app.db, ctx.app.Session)


def _on_method_context_closed(ctx):
    error = None
    if ctx.in_error is not None:
        error = ctx.in_error

    elif ctx.out_error is not None:
        error = ctx.out_error

    if error is None:
        om = ctx.descriptor.out_message
        if issubclass(om, ComplexModelBase):
            oo = ctx.out_object
            if len(om._type_info) == 0:
                oo = None

            elif len(om._type_info) == 1 and \
                              ctx.descriptor.body_style is BODY_STYLE_WRAPPED:
                om, = om._type_info.values()
                oo, = ctx.out_object

            else:
                oo = om.get_serialization_instance(ctx.out_object)

        log.msg('%s[OK]%s %r => %r' % (
                    GREEN, RESET,
                    log_repr(ctx.in_object, ctx.descriptor.in_message),
                    log_repr(oo, om),
                ))

    elif isinstance(error, Fault):
        log.msg('%s[CE]%s %r => %r' % (RED, RESET, ctx.in_object, error))
    else:
        log.msg('%s[UE]%s %r => %r' % (RED, RESET, ctx.in_object, error))

    if ctx.udc is not None:
        ctx.udc.close()


class Application(AppBase):
    def __init__(self, services, tns, name=None, in_protocol=None,
                 out_protocol=None, db=None):
        super(Application, self).__init__(services, tns, name, in_protocol, out_protocol)

        self.event_manager.add_listener("method_call", _on_method_call)
        self.event_manager.add_listener("method_context_closed",
                                                      _on_method_context_closed)

        self.db = db
        self.Session = sessionmaker(bind=db, expire_on_commit=False)

    def call_wrapper(self, ctx):
        try:
            return ctx.service_class.call_wrapper(ctx)

        except NoResultFound:
            raise ResourceNotFoundError(ctx.in_object)

        except Fault as e:
            log.err()
            raise

        except Exception as e:
            log.err()
            # This should not happen! Let the team know via email!
            if EXCEPTION_ADDRESS:
                email_exception(EXCEPTION_ADDRESS)
            raise InternalError(e)


def _user_callables(d):
    for k,v in d.items():
        if callable(v) and not k in ('__init__', '__metaclass__'):
            yield k,v


def _et(f):
    def _wrap(*args, **kwargs):
        self = args[0]

        try:
            retval = f(*args, **kwargs)
            self.session.expunge_all()
            return retval

        except NoResultFound:
            raise ResourceNotFoundError(self.ctx.in_object)

        except Fault as e:
            log.err()
            raise

        except Exception as e:
            log.err()
            # This should not happen! Let the team know via email!
            email_exception(EXCEPTION_ADDRESS)
            raise InternalError(e)
    return _wrap


class DBThreadPool(ThreadPool):
    def __init__(self, engine, verbose=False):
        if engine.dialect.name == 'sqlite':
            pool_size = 1

            ThreadPool.__init__(self, minthreads=1, maxthreads=1)
        else:
            ThreadPool.__init__(self)

        self.engine = engine
        reactor.callWhenRunning(self.start)

    def start(self):
        reactor.addSystemEventTrigger('during', 'shutdown', self.stop)
        ThreadPool.start(self)


class DalMeta(type(object)):
    def __new__(cls, cls_name, cls_bases, cls_dict):
        for k, v in _user_callables(cls_dict):
            def _w2(_user_callable):
                def _wrap(*args, **kwargs):
                    return deferToThreadPool(reactor, retval._pool, 
                                            _et(_user_callable), *args, **kwargs)
                return _wrap
            cls_dict[k] = _w2(v)

        retval = type(object).__new__(cls, cls_name, cls_bases, cls_dict)
        return retval

    @property
    def bind(self):
        return self._db

    @bind.setter
    def bind(self, what):
        self._db = what
        self._pool = DBThreadPool(what)


class DalBase(object):
    __metaclass__ = DalMeta

    _db = None
    _pool = None

    def __init__(self, ctx):
        self.ctx = ctx
        self.session = ctx.udc.session
        if ctx.udc.session is None:
            self.session = ctx.udc.session = ctx.udc.Session()


class Context(object):
    def __init__(self, db, Session=None):
        self.db = db
        self.Session = Session
        self.rd = None
        self.ru = None
        self.session = None

    def close(self):
        if self.session is not None:
            self.session.close()


def log_repr(obj, cls=None, given_len=None):
    """Use this function if you want to echo a ComplexModel subclass. It will
    limit output size of the String types, making your logs smaller.
    """

    if obj is None:
        return 'None'

    if cls is None:
        cls = obj.__class__

    if issubclass(cls, Array) or cls.Attributes.max_occurs > 1:
        if not cls.Attributes.logged:
            retval = "%s(...)" % cls.get_type_name()

        else:
            retval = []
            if issubclass(cls, Array):
                cls, = cls._type_info.values()

            if not cls.Attributes.logged:
                retval.append("%s (...)" % cls.get_type_name())

            elif cls.Attributes.logged == 'len':
                l = '?'

                try:
                    l = str(len(obj))
                except TypeError as e:
                    if given_len is not None:
                        l = str(given_len)
                if issubclass(cls, ComplexModelBase):
                    retval.append("%s[%s] (...)" % (cls.get_type_name(), l))
                else:
                    retval.append("[%s] (...)" % l)

            else:
                for i,o in enumerate(obj):
                    retval.append(_log_repr_obj(o, cls))

                    if i > MAX_ARRAY_ELEMENT_NUM:
                        retval.append("(...)")
                        break

            if issubclass(cls, ComplexModelBase):
                retval = "%s([%s])" % (cls.get_type_name(), ', '.join(retval))
            else:
                retval = "[%s]" % ', '.join(retval)

    elif issubclass(cls, ComplexModelBase):
        if cls.Attributes.logged:
            retval = _log_repr_obj(obj, cls)
        else:
            retval = "%s(...)" % cls.get_type_name()

    else:
        retval = repr(obj)

        if len(retval) > MAX_STRING_FIELD_LENGTH:
            retval = retval[:MAX_STRING_FIELD_LENGTH] + "(...)"

    return retval


def _log_repr_obj(obj, cls):
    if not issubclass(cls, ComplexModelBase):
        return _log_repr_any(obj, cls)

    retval = []
    for k, t in cls.get_flat_type_info(cls).items():
        v = getattr(obj, k, None)
        if v is not None and t.Attributes.logged:
            retval.append(_log_repr_any(v, t, k))

    return "%s(%s)" % (cls.get_type_name(), ', '.join(retval))


def _log_repr_any(obj, cls, k=None):
    if issubclass(cls, Unicode) and isinstance(obj, six.string_types) and \
                                                len(obj) > MAX_STRING_FIELD_LENGTH:
        if k is None:
            return '%r(...)' % (obj[:MAX_STRING_FIELD_LENGTH])
        else:
            return '%s=%r(...)' % (k, obj[:MAX_STRING_FIELD_LENGTH])
    else:
        if k is None:
            return repr(obj)
        else:
            return '%s=%r' % (k, obj)


@memoize
def TReaderService(T, T_name):
    class ReaderService(ReaderServiceBase):
        @rpc(M(UnsignedInteger32), _returns=T,
                    _in_message_name='get_%s' % T_name,
                    _in_variable_names={'obj_id': "%s_id" % T_name})
        def get(ctx, obj_id):
            return ctx.udc.session.query(T).filter_by(id=obj_id).one()

        @rpc(_returns=Iterable(T),
                    _in_message_name='get_all_%s' % T_name)
        def get_all(ctx):
            return ctx.udc.session.query(T).order_by(T.id)

    return ReaderService


@memoize
def TWriterService(T, T_name, put_not_found='raise'):
    assert put_not_found in ('raise', 'fix')

    if put_not_found == 'raise':
        def put_not_found(obj):
            raise ResourceNotFoundError('%s.id=%d' % (T_name, obj.id))

    elif put_not_found == 'fix':
        def put_not_found(obj):
            obj.id = None

    class WriterService(WriterServiceBase):
        @rpc(M(T), _returns=UnsignedInteger32,
                    _in_message_name='put_%s' % T_name,
                    _in_variable_names={'obj': T_name})
        def put(ctx, obj):
            if obj.id is None:
                ctx.udc.session.add(obj)
                ctx.udc.session.flush() # so that we get the obj.id value

            else:
                if ctx.udc.session.query(T).get(obj.id) is None:
                    # this is to prevent the client from setting the primary key
                    # of a new object instead of the database's own primary-key
                    # generator.
                    # Instead of raising an exception, you can also choose to
                    # ignore the primary key set by the client by silently doing
                    # obj.id = None in order to have the database assign the
                    # primary key the traditional way.
                    put_not_found(obj.id)

                else:
                    ctx.udc.session.merge(obj)

            return obj.id

        @rpc(M(UnsignedInteger32),
                    _in_message_name='del_%s' % T_name,
                    _in_variable_names={'obj_id': '%s_id' % T_name})
        def del_(ctx, obj_id):
            count = ctx.udc.session.query(T).filter_by(id=obj_id).count()
            if count == 0:
                raise ResourceNotFoundError(obj_id)

            ctx.udc.session.query(T).filter_by(id=obj_id).delete()

    return WriterService
