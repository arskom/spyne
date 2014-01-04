# encoding: utf8
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

from inspect import isgenerator

from lxml.html.builder import E
from spyne import BODY_STYLE_WRAPPED
from spyne.model import PushBase, Array

from spyne.protocol import ProtocolBase
from spyne.util import coroutine, Break
from spyne.util.six import StringIO


class HtmlBase(ProtocolBase):
    mime_type = 'text/html'

    def serialize(self, ctx, message):
        """Uses ``ctx.out_object``, ``ctx.out_header`` or ``ctx.out_error`` to
        set ``ctx.out_body_doc``, ``ctx.out_header_doc`` and
        ``ctx.out_document`` as an ``lxml.etree._Element instance``.

        Not meant to be overridden.
        """

        assert message in (self.REQUEST, self.RESPONSE)

        self.event_manager.fire_event('before_serialize', ctx)

        if ctx.out_stream is None:
            ctx.out_stream = StringIO()

        if ctx.out_error is not None:
            # All errors at this point must be Fault subclasses.
            inst = ctx.out_error
            cls = inst.__class__
            name = cls.get_type_name()

            ctx.out_document = E.div()
            from lxml import etree
            with etree.xmlfile(ctx.out_stream) as xf:
                retval = HtmlBase.HtmlMicroFormat() \
                                            .to_parent(ctx, cls, inst, xf, name)

        else:
            assert message is self.RESPONSE
            result_message_class = ctx.descriptor.out_message

            name = result_message_class.get_type_name()
            if ctx.descriptor.body_style == BODY_STYLE_WRAPPED:
                if self.ignore_wrappers:
                    ctx.out_object = ctx.out_object[0]
                    result_message = ctx.out_object
                    while result_message_class.Attributes._wrapper:
                        result_message_class = next(iter(
                                      result_message_class._type_info.values()))

                else:
                    result_message = result_message_class()

                    for i, attr_name in enumerate(
                                        result_message_class._type_info.keys()):
                        setattr(result_message, attr_name, ctx.out_object[i])

            else:
                result_message = ctx.out_object

            retval = self.incgen(ctx, result_message_class, result_message, name)

        self.event_manager.fire_event('after_serialize', ctx)

        return retval

    @coroutine
    def incgen(self, ctx, cls, inst, name):
        if name is None:
            name = cls.get_type_name()

        from lxml import etree
        # FIXME: html.htmlfile olmali
        with etree.xmlfile(ctx.out_stream) as xf:
            ret = self.subserialize(ctx, cls, inst, xf, None, name)

            if isgenerator(ret):
                try:
                    while True:
                        sv2 = (yield)
                        ret.send(sv2)
                except Break as b:
                    try:
                        ret.throw(b)
                    except StopIteration:
                        pass

    def create_out_string(self, ctx, charset=None):
        """Sets an iterable of string fragments to ctx.out_string"""

        ctx.out_string = [ctx.out_stream.getvalue()]

    def subserialize(self, ctx, cls, inst, parent, ns=None, name=None):
        if name is None:
            name = cls.get_type_name()
        if cls.Attributes.max_occurs > 1:
            return self.array_to_parent(ctx, cls, inst, parent, name)
        return self.to_parent(ctx, cls, inst, parent, name)

    def decompose_incoming_envelope(self, ctx, message):
        raise NotImplementedError("This is an output-only protocol.")

    @coroutine
    def array_to_parent(self, ctx, cls, inst, parent, name, **kwargs):
        if issubclass(cls, Array):
            cls, = cls._type_info.values()

        name = cls.get_type_name()
        if isinstance(inst, PushBase):
            while True:
                sv = (yield)
                ret = self.to_parent(ctx, cls, sv, parent, name, **kwargs)
                if isgenerator(ret):
                    try:
                        while True:
                            sv2 = (yield)
                            ret.send(sv2)
                    except Break as e:
                        try:
                            ret.throw(e)
                        except StopIteration:
                            pass

        else:
            for sv in inst:
                ret = self.to_parent(ctx, cls, sv, parent, name, **kwargs)
                if isgenerator(ret):
                    try:
                        while True:
                            sv2 = (yield)
                            ret.send(sv2)
                    except Break as e:
                        try:
                            ret.throw(e)
                        except StopIteration:
                            pass

    def to_parent(self, ctx, cls, inst, parent, name, **kwargs):
        subprot = getattr(cls.Attributes, 'prot', None)
        """:type : HtmlBase"""
        if subprot is not None:
            if isinstance(subprot, HtmlBase):
                if not subprot.__class__ is self.__class__:
                    subprot.to_parent(ctx, cls, inst, parent, name, **kwargs)
            else:
                return subprot.subserialize(ctx, cls, inst, parent, None, name)

        handler = self.serialization_handlers[cls]
        if inst is None:
            if cls.Attributes.default is None:
                return self.null_to_parent(ctx, cls, inst, parent, name,
                                                                **kwargs)
            return handler(ctx, cls, cls.Attributes.default, parent, name,
                                                                **kwargs)
        return handler(ctx, cls, inst, parent, name, **kwargs)

    def null_to_parent(self, ctx, cls, inst, parent, name, **kwargs):
        pass

    @coroutine
    def _get_members(self, ctx, cls, inst, parent, **kwargs):
        for k, v in cls.get_flat_type_info(cls).items():
            try:
                subvalue = getattr(inst, k, None)
            except: # to guard against e.g. SqlAlchemy throwing NoSuchColumnError
                subvalue = None

            sub_name = v.Attributes.sub_name
            if sub_name is None:
                sub_name = k

            mo = v.Attributes.max_occurs
            if subvalue is not None and mo > 1:
                ret = self.array_to_parent(ctx, v, subvalue, parent, sub_name,
                                                                 **kwargs)
                if ret is not None:
                    try:
                        while True:
                            sv2 = (yield)
                            ret.send(sv2)
                    except Break as b:
                        try:
                            ret.throw(b)
                        except StopIteration:
                            pass

            # Don't include empty values for non-nillable optional attributes.
            elif subvalue is not None or v.Attributes.min_occurs > 0:
                ret = self.to_parent(ctx, v, subvalue, parent, sub_name, **kwargs)
                if ret is not None:
                    try:
                        while True:
                            sv2 = (yield)
                            ret.send(sv2)
                    except Break as b:
                        try:
                            ret.throw(b)
                        except StopIteration:
                            pass

    @staticmethod
    def translate(cls, locale, default):
        """
        :param cls: class
        :param locale: locale string
        :param default: default string if no translation found
        :returns: translated string
        """

        if cls.Attributes.translations is not None:
            return cls.Attributes.translations.get(locale, default)
        return default


    @staticmethod
    def not_supported(prot, cls, *args, **kwargs):
        raise Exception("Serializing %r Not Supported!" % cls)

    def anyhtml_to_parent(self, ctx, cls, inst, parent, name, **kwargs):
        parent.write(inst)

    def anyuri_to_parent(self, ctx, cls, inst, parent, name, **kwargs):
        href = getattr(inst, 'href', None)
        if href is None: # this is not a AnyUri.Value instance.
            href = inst
            text = getattr(cls.Attributes, 'text', name)
            content = None

        else:
            text = getattr(inst, 'text', None)
            if text is None:
                text = getattr(cls.Attributes, 'text', name)

            content = getattr(inst, 'content', None)

        retval = E.a(text, href=href)
        if content is not None:
            retval.append(content)
        parent.write(retval)

    def imageuri_to_parent(self, ctx, cls, inst, parent, name, **kwargs):
        # with ImageUri, content is ignored.
        href = getattr(inst, 'href', None)
        if href is None: # this is not a AnyUri.Value instance.
            href = inst
            text = getattr(cls.Attributes, 'text', None)

        else:
            text = getattr(inst, 'text', None)
            if text is None:
                text = getattr(cls.Attributes, 'text', None)

        retval = E.img(src=href)
        if text is not None:
            retval.attrib['alt'] = text
        parent.write(retval)
