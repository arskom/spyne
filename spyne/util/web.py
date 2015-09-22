
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

from inspect import isclass

from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound

from spyne import BODY_STYLE_WRAPPED, rpc, Any, AnyDict, NATIVE_MAP
from spyne.util import six
from spyne.application import Application as AppBase
from spyne.const import MAX_STRING_FIELD_LENGTH, MAX_FIELD_NUM
from spyne.const import MAX_ARRAY_ELEMENT_NUM
from spyne.error import Fault
from spyne.error import InternalError
from spyne.error import ResourceNotFoundError
from spyne.service import ServiceBase
from spyne.util import memoize
from spyne.util.email import email_exception
from spyne.model import Mandatory as M, UnsignedInteger32, PushBase, Iterable, \
    ModelBase, File
from spyne.model import Unicode
from spyne.model import Array
from spyne.model import ComplexModelBase
from spyne.store.relational import PGFileJson


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


class ReaderServiceBase(ServiceBase):
    pass


class WriterServiceBase(ServiceBase):
    pass


def log_repr(obj, cls=None, given_len=None, parent=None, from_array=False, tags=None):
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

    if cls is None:
        cls = obj.__class__

    if cls in (list, tuple):
        cls = Array(Any)

    if cls is dict:
        cls = AnyDict

    if cls in NATIVE_MAP:
        cls = NATIVE_MAP[cls]

    if hasattr(obj, '__class__') and issubclass(obj.__class__, cls):
        cls = obj.__class__

    if hasattr(cls, 'Attributes') and not cls.Attributes.logged:
        return "%s(...)" % cls.get_type_name()

    if issubclass(cls, File) and isinstance(obj, File.Value):
        cls = obj.__class__

    if cls.Attributes.logged == 'len':
        l = '?'
        try:
            if isinstance(obj, (list, tuple)):
                l = str(sum([len(o) for o in obj]))
            else:
                l = str(len(obj))
        except TypeError:
            if given_len is not None:
                l = str(given_len)

        return "<len=%s>" % l

    if issubclass(cls, Array):
        cls, = cls._type_info.values()

    if (cls.Attributes.max_occurs > 1) and not from_array:
        if id(obj) in tags:
            return "%s(...)" % obj.__class__.__name__
        tags.add(id(obj))

        retval = []
        subcls = cls
        if issubclass(cls, Array):
            subcls, = cls._type_info.values()

        if isinstance(obj, PushBase):
            retval = '[<PushData>]'

        else:
            for i, o in enumerate(obj):
                if i >= MAX_ARRAY_ELEMENT_NUM:
                    retval.append("(...)")
                    break

                retval.append(log_repr(o, subcls, from_array=True, tags=tags))

            retval = "[%s]" % (', '.join(retval))

    elif issubclass(cls, ComplexModelBase):
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

            try:
                v = getattr(obj, k, None)
            except (AttributeError, KeyError):
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

    elif issubclass(cls, Unicode) and isinstance(obj, six.string_types):
        if len(obj) > MAX_STRING_FIELD_LENGTH:
            return '%r(...)' % obj[:MAX_STRING_FIELD_LENGTH]

        else:
            return repr(obj)

    elif issubclass(cls, File) and isinstance(obj, PGFileJson.FileData):
        retval = log_repr(obj, PGFileJson.FileData, tags=tags)

    else:
        retval = repr(obj)

        if len(retval) > MAX_STRING_FIELD_LENGTH:
            retval = retval[:MAX_STRING_FIELD_LENGTH] + "(...)"

    return retval


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
