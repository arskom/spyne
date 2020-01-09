
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

from __future__ import print_function

import logging
logger = logging.getLogger(__name__)

from datetime import datetime
from weakref import WeakKeyDictionary

from spyne import ProtocolContext, EventManager
from spyne.const import DEFAULT_LOCALE
from spyne.model import Array
from spyne.error import ResourceNotFoundError
from spyne.util import DefaultAttrDict
from spyne.util.six import string_types


_MISSING = type("_MISSING", (object,), {})()


class ProtocolMixin(object):
    mime_type = 'application/octet-stream'

    SOFT_VALIDATION = type("Soft", (object,), {})
    REQUEST = type("Request", (object,), {})
    RESPONSE = type("Response", (object,), {})

    type = set()
    """Set that contains keywords about a protocol."""

    default_binary_encoding = None
    """Default encoding for binary data. It could be e.g. base64."""

    default_string_encoding = None
    """Default encoding for text content. It could be e.g. UTF-8."""

    type_attrs = {}
    """Default customizations to be passed to underlying classes."""

    def __init__(self, app=None, mime_type=None, ignore_wrappers=None,
                                    binary_encoding=None, string_encoding=None):
        self.__app = None
        self.set_app(app)

        self.ignore_wrappers = ignore_wrappers
        self.event_manager = EventManager(self)
        self.binary_encoding = binary_encoding
        if self.binary_encoding is None:
            self.binary_encoding = self.default_binary_encoding

        self.string_encoding = string_encoding
        if self.string_encoding is None:
            self.string_encoding = self.default_string_encoding

        if mime_type is not None:
            self.mime_type = mime_type

        self._attrcache = WeakKeyDictionary()
        self._sortcache = WeakKeyDictionary()

    def _cast(self, cls_attrs, inst):
        if cls_attrs.parser is not None:
            return cls_attrs.parser(inst)
        return inst

    _parse = _cast

    def _sanitize(self, cls_attrs, inst):
        if cls_attrs.sanitizer is not None:
            return cls_attrs.sanitizer(inst)
        return inst

    def _datetime_from_sec(self, cls, value):
        try:
            return datetime.fromtimestamp(value)
        except TypeError:
            logger.error("Invalid value %r", value)
            raise

    def _datetime_from_sec_float(self, cls, value):
        try:
            return datetime.fromtimestamp(value)
        except TypeError:
            logger.error("Invalid value %r", value)
            raise

    def _datetime_from_msec(self, cls, value):
        try:
            return datetime.fromtimestamp(value // 1000)
        except TypeError:
            logger.error("Invalid value %r", value)
            raise

    def _datetime_from_msec_float(self, cls, value):
        try:
            return datetime.fromtimestamp(value / 1000)
        except TypeError:
            logger.error("Invalid value %r", value)
            raise

    def _datetime_from_usec(self, cls, value):
        try:
            return datetime.fromtimestamp(value / 1e6)
        except TypeError:
            logger.error("Invalid value %r", value)
            raise

    def _get_datetime_format(self, cls_attrs):
        # FIXME: this should be dt_format, all other aliases are to be
        # deprecated
        dt_format = cls_attrs.datetime_format
        if dt_format is None:
            dt_format = cls_attrs.dt_format
        if dt_format is None:
            dt_format = cls_attrs.date_format
        if dt_format is None:
            dt_format = cls_attrs.out_format
        if dt_format is None:
            dt_format = cls_attrs.format

        return dt_format

    def _get_date_format(self, cls_attrs):
        date_format = cls_attrs.date_format
        if date_format is None:
            date_format = cls_attrs.format

        return date_format

    def _get_time_format(self, cls_attrs):
        time_format = cls_attrs.time_format
        if time_format is None:
            time_format = cls_attrs.format

        return time_format

    @property
    def app(self):
        return self.__app

    @staticmethod
    def strip_wrappers(cls, inst):
        ti = getattr(cls, '_type_info', {})

        while len(ti) == 1 and cls.Attributes._wrapper:
            # Wrappers are auto-generated objects that have exactly one
            # child type.
            key, = ti.keys()
            if not issubclass(cls, Array):
                inst = getattr(inst, key, None)
            cls, = ti.values()
            ti = getattr(cls, '_type_info', {})

        return cls, inst

    def set_app(self, value):
        assert self.__app is None, "One protocol instance should belong to one " \
                                   "application instance. It currently belongs " \
                                   "to: %r" % self.__app
        self.__app = value

    @staticmethod
    def issubclass(sub, cls):
        suborig = getattr(sub, '__orig__', None)
        clsorig = getattr(cls, '__orig__', None)
        return issubclass(sub if suborig is None else suborig,
                          cls if clsorig is None else clsorig)

    def get_cls_attrs(self, cls):
        logger.debug("%r attrcache size: %d", self, len(self._attrcache))
        attr = self._attrcache.get(cls, None)
        if attr is not None:
            return attr

        self._attrcache[cls] = attr = DefaultAttrDict([
                (k, getattr(cls.Attributes, k))
                        for k in dir(cls.Attributes) + META_ATTR
                                                     if not k.startswith('__')])

        if cls.Attributes.prot_attrs:
            cls_attrs = cls.Attributes.prot_attrs.get(self.__class__, {})
            # logger.debug("%r cls attr %r", cls, cls_attrs)
            attr.update(cls_attrs)

            inst_attrs = cls.Attributes.prot_attrs.get(self, {})
            # logger.debug("%r inst attr %r", cls, cls_attrs)
            attr.update(inst_attrs)

        return attr

    def get_context(self, parent, transport):
        return ProtocolContext(parent, transport)

    def generate_method_contexts(self, ctx):
        """Generates MethodContext instances for every callable assigned to the
        given method handle.

        The first element in the returned list is always the primary method
        context whereas the rest are all auxiliary method contexts.
        """

        call_handles = self.get_call_handles(ctx)
        if len(call_handles) == 0:
            raise ResourceNotFoundError(ctx.method_request_string)

        retval = []
        for d in call_handles:
            assert d is not None

            c = ctx.copy()
            c.descriptor = d

            retval.append(c)

        return retval

    def get_call_handles(self, ctx):
        """Method to be overriden to perform any sort of custom method mapping
        using any data in the method context. Returns a list of contexts.
        Can return multiple contexts if a method_request_string matches more
        than one function. (This is called the fanout mode.)
        """

        name = ctx.method_request_string
        if not name.startswith(u"{"):
            name = u'{%s}%s' % (self.app.interface.get_tns(), name)

        call_handles = self.app.interface.service_method_map.get(name, [])

        return call_handles

    def get_polymorphic_target(self, cls, inst):
        """If the protocol is polymorphic, extract what's returned by the user
        code.
        """

        if not self.polymorphic:
            logger.debug("PMORPH Skipped: %r is NOT polymorphic", self)
            return cls, False

        orig_cls = cls.__orig__ or cls

        if inst.__class__ is orig_cls:
            logger.debug("PMORPH Skipped: Instance class %r is the same as "
                                        "designated base class", inst.__class__)
            return cls, False

        if not isinstance(inst, orig_cls):
            logger.debug("PMORPH Skipped: Instance class %r is not a subclass "
                        "of designated base class %r", inst.__class__, orig_cls)
            return cls, False

        cls_attr = self.get_cls_attrs(cls)
        polymap_cls = cls_attr.polymap.get(inst.__class__, None)

        if polymap_cls is not None:
            logger.debug("PMORPH OK: cls switch with polymap: %r => %r",
                                                               cls, polymap_cls)
            return polymap_cls, True

        else:
            logger.debug("PMORPH OK: cls switch without polymap: %r => %r",
                                                            cls, inst.__class__)
            return inst.__class__, True

    @staticmethod
    def trc_verbose(cls, locale, default):
        """Translate a class.

        :param cls: class
        :param locale: locale string
        :param default: default string if no translation found
        :returns: translated string
        """

        if locale is None:
            locale = DEFAULT_LOCALE
            _log_locale = "default locale '%s'"
        else:
            _log_locale = "given locale '%s'"

        if cls.Attributes.translations is None:
            retval = default
            _log_tr = "translated to '%s' without any translations at all with"

        else:
            retval = cls.Attributes.translations.get(locale, _MISSING)
            if retval is _MISSING:
                retval = default
                _log_tr = "translated to '%s': No translation for"
            else:
                _log_tr = "translated to '%s' with"

        logger.debug(' '.join(("%r ", _log_tr, _log_locale)),
                                                            cls, retval, locale)

        return retval

    @staticmethod
    def trc(cls, locale, default):
        """Translate a class.

        :param cls: class
        :param locale: locale string
        :param default: default string if no translation found
        :returns: translated string
        """

        if locale is None:
            locale = DEFAULT_LOCALE
        if cls.Attributes.translations is not None:
            return cls.Attributes.translations.get(locale, default)
        return default

    @staticmethod
    def trd_verbose(trdict, locale, default):
        """Translate from a translations dict.

        :param trdict: translation dict
        :param locale: locale string
        :param default: default string if no translation found
        :returns: translated string
        """

        if locale is None:
            locale = DEFAULT_LOCALE
            _log_locale = "default locale '%s'"
        else:
            _log_locale = "given locale '%s'"

        if trdict is None:
            retval = default
            _log_tr = "translated to '%s' without any translations at all with"

        elif isinstance(trdict, string_types):
            retval = trdict
            _log_tr = "translated to '%s' regardless of"

        else:
            retval = trdict.get(locale, _MISSING)
            if retval is _MISSING:
                retval = default
                _log_tr = "translated to '%s': No translation for"
            else:
                _log_tr = "translated to '%s' with"

        logger.debug(' '.join(("%r ", _log_tr, _log_locale)),
                                                         trdict, retval, locale)

        return retval

    @staticmethod
    def trd(trdict, locale, default):
        """Translate from a translations dict.

        :param trdict: translation dict
        :param locale: locale string
        :param default: default string if no translation found
        :returns: translated string
        """

        if locale is None:
            locale = DEFAULT_LOCALE
        if trdict is None:
            return default
        if isinstance(trdict, string_types):
            return trdict

        return trdict.get(locale, default)

    def sort_fields(self, cls=None, items=None):
        logger.debug("%r sortcache size: %d", self, len(self._sortcache))
        retval = self._sortcache.get(cls, None)
        if retval is not None:
            return retval

        if items is None:
            items = list(cls.get_flat_type_info(cls).items())

        indexes = {}
        for k, v in items:
            order = self.get_cls_attrs(v).order
            if order is not None:
                if order < 0:
                    indexes[k] = len(items) + order
                else:
                    indexes[k] = order

        for k, v in items:
            order = self.get_cls_attrs(v).order
            if order is None:
                indexes[k] = len(indexes)

        items.sort(key=lambda x: indexes[x[0]])
        self._sortcache[cls] = items

        return items


META_ATTR = ['nullable', 'default_factory']
