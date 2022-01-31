
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
Some code dump from some time ago.

If you're using this for anything serious, you're insane.
"""

from __future__ import absolute_import

import logging
logger = logging.getLogger(__name__)

from inspect import isclass

from spyne import rpc, Any, AnyDict, NATIVE_MAP, M, Array, ComplexModelBase, \
    UnsignedInteger32, PushBase, Iterable, ModelBase, File, Service, \
    ResourceNotFoundError, Unicode

from spyne.const import MAX_ARRAY_ELEMENT_NUM, MAX_DICT_ELEMENT_NUM, \
    MAX_STRING_FIELD_LENGTH, MAX_FIELD_NUM

try:
    from spyne.store.relational.document import FileData
    from sqlalchemy.orm.exc import DetachedInstanceError
except ImportError:
    # these are used just for isinstance checks. so we just set it to an
    # anonymous value
    FileData = type('__hidden', (object, ), {})
    DetachedInstanceError = type('__hidden', (Exception, ), {})

from spyne.util import memoize, six

EXCEPTION_ADDRESS = None


try:
    from colorama.ansi import Fore
    from colorama.ansi import Style
    RED = Fore.RED + Style.BRIGHT
    GREEN = Fore.GREEN + Style.BRIGHT
    RESET = Style.RESET_ALL

except ImportError:
    RED = ""
    GREEN = ""
    RESET = ""


class ReaderService(Service):
    pass


class WriterService(Service):
    pass


def log_repr(obj, cls=None, given_len=None, parent=None, from_array=False,
                                                          tags=None, prot=None):
    """Use this function if you want to serialize a ComplexModelBase instance to
    logs. It will:

        * Limit size of the String types
        * Limit size of Array types
        * Not try to iterate on iterators, push data, etc.
    """

    if tags is None:
        tags = set()

    if obj is None:
        return 'None'

    objcls = None
    if hasattr(obj, '__class__'):
        objcls = obj.__class__

    if objcls in (list, tuple):
        objcls = Array(Any)

    elif objcls is dict:
        objcls = AnyDict

    elif objcls in NATIVE_MAP:
        objcls = NATIVE_MAP[objcls]

    if objcls is not None and (cls is None or issubclass(objcls, cls)):
        cls = objcls

    cls_attrs = None
    logged = None

    if hasattr(cls, 'Attributes'):
        # init cls_attrs
        if prot is None:
            cls_attrs = cls.Attributes
        else:
            cls_attrs = prot.get_cls_attrs(cls)

        # init logged
        logged = cls_attrs.logged
        if not logged:
            return "%s(...)" % cls.get_type_name()

        if logged == '...':
            return "(...)"

    if logged == 'len':
        l = '?'
        try:
            if isinstance(obj, (list, tuple)):
                l = str(sum([len(o) for o in obj]))

            else:
                l = str(len(obj))
        except (TypeError, ValueError):
            if given_len is not None:
                l = str(given_len)

        return "<len=%s>" % l

    if callable(logged):
        try:
            return cls_attrs.logged(obj)
        except Exception as e:
            logger.error("Exception %r in log_repr transformer ignored", e)
            logger.exception(e)
            pass

    if issubclass(cls, AnyDict) or isinstance(obj, dict):
        retval = []

        if isinstance(obj, dict):
            if logged == 'full':
                for i, (k, v) in enumerate(obj.items()):
                    retval.append('%r: %r' % (k, v))

            elif logged == 'keys':
                for i, k in enumerate(obj.keys()):
                    if i >= MAX_DICT_ELEMENT_NUM:
                        retval.append("(...)")
                        break

                    retval.append('%r: (...)' % (k,))

            elif logged == 'values':
                for i, v in enumerate(obj.values()):
                    if i >= MAX_DICT_ELEMENT_NUM:
                        retval.append("(...)")
                        break

                    retval.append('(...): %s' % (log_repr(v, tags=tags),))

            elif logged == 'keys-full':
                for k in obj.keys():
                    retval.append('%r: (...)' % (k,))

            elif logged == 'values-full':
                for v in obj.values():
                    retval.append('(...): %r' % (v,))

            elif logged is True:  # default behaviour
                for i, (k, v) in enumerate(obj.items()):
                    if i >= MAX_DICT_ELEMENT_NUM:
                        retval.append("(...)")
                        break

                    retval.append('%r: %s' % (k,
                                              log_repr(v, parent=k, tags=tags)))
            elif logged is None:
                return "(...)"

            else:
                raise ValueError("Invalid value logged=%r", logged)

            return "{%s}" % ', '.join(retval)

        else:
            if logged in ('full', 'keys-full', 'values-full'):
                retval = [repr(s) for s in obj]

            else:
                for i, v in enumerate(obj):
                    if i >= MAX_DICT_ELEMENT_NUM:
                        retval.append("(...)")
                        break

                    retval.append(log_repr(v, tags=tags))

            return "[%s]" % ', '.join(retval)

    if ( issubclass(cls, Array)
                     or (cls_attrs is not None and cls_attrs.max_occurs > 1) ) \
            and not from_array:

        if id(obj) in tags:
            return "%s(...)" % obj.__class__.__name__

        tags.add(id(obj))

        retval = []

        subcls = cls
        if issubclass(cls, Array):
            subcls, = cls._type_info.values()

        if isinstance(obj, PushBase):
            return '[<PushData>]'

        if logged is None:
            logged = cls_attrs.logged

        for i, o in enumerate(obj):
            if logged != 'full' and i >= MAX_ARRAY_ELEMENT_NUM:
                retval.append("(...)")
                break

            retval.append(log_repr(o, subcls, from_array=True, tags=tags))

        return "[%s]" % (', '.join(retval))

    if issubclass(cls, ComplexModelBase):
        if id(obj) in tags:
            return "%s(...)" % obj.__class__.__name__

        tags.add(id(obj))

        retval = []
        i = 0

        for k, t in cls.get_flat_type_info(cls).items():
            if i >= MAX_FIELD_NUM:
                retval.append("(...)")
                break

            if not t.Attributes.logged:
                continue

            if logged == '...':
                retval.append("%s=(...)" % k)
                continue

            try:
                v = getattr(obj, k, None)
            except (AttributeError, KeyError, DetachedInstanceError):
                v = None

            # HACK!: sometimes non-db attributes restored from database don't
            # get properly reinitialized.
            if isclass(v) and issubclass(v, ModelBase):
                continue

            polymap = t.Attributes.polymap
            if polymap is not None:
                t = polymap.get(v.__class__, t)

            if v is not None:
                retval.append("%s=%s" % (k, log_repr(v, t, parent=k, tags=tags)))
                i += 1

        return "%s(%s)" % (cls.get_type_name(), ', '.join(retval))

    if issubclass(cls, Unicode) and isinstance(obj, six.string_types):
        if len(obj) > MAX_STRING_FIELD_LENGTH:
            return '%r(...)' % obj[:MAX_STRING_FIELD_LENGTH]

        return repr(obj)

    if issubclass(cls, File) and isinstance(obj, File.Value):
        cls = obj.__class__

    if issubclass(cls, File) and isinstance(obj, FileData):
        return log_repr(obj, FileData, tags=tags)

    retval = repr(obj)

    if len(retval) > MAX_STRING_FIELD_LENGTH:
        retval = retval[:MAX_STRING_FIELD_LENGTH] + "(...)"

    return retval


def TReaderService(T, T_name):
    class ReaderService(ReaderService):
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


def TWriterService(T, T_name, put_not_found='raise'):
    assert put_not_found in ('raise', 'fix')

    if put_not_found == 'raise':
        def put_not_found(obj):
            raise ResourceNotFoundError('%s.id=%d' % (T_name, obj.id))

    elif put_not_found == 'fix':
        def put_not_found(obj):
            obj.id = None

    class WriterService(WriterService):
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
