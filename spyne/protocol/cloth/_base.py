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

import logging
logger = logging.getLogger(__name__)

from inspect import isgenerator
from lxml import etree
from lxml import html
from lxml.etree import LxmlSyntaxError
from lxml.builder import E

from spyne import BODY_STYLE_WRAPPED
from spyne.util import Break, coroutine

from spyne.protocol.cloth.to_parent import ToParentMixin
from spyne.protocol.cloth.to_cloth import ToClothMixin
from spyne.util.six import StringIO, string_types


class XmlCloth(ToParentMixin, ToClothMixin):
    mime_type = 'text/xml'
    HtmlMicroFormat = None

    def __init__(self, app=None, mime_type=None,
                       ignore_uncap=False, ignore_wrappers=False,
                       cloth=None, attr_name='spyne_id', root_attr_name='spyne',
                                                             cloth_parser=None):
        super(XmlCloth, self).__init__(app=app,
                                 mime_type=mime_type, ignore_uncap=ignore_uncap,
                                 ignore_wrappers=ignore_wrappers)

        self.attr_name = attr_name
        self.root_attr_name = root_attr_name

        self._mrpc_cloth = self._root_cloth = None
        self._cloth = cloth
        if isinstance(self._cloth, string_types):
            if cloth_parser is None:
                cloth_parser = etree.XMLParser(remove_comments=True)
            self._cloth = html.parse(cloth, parser=cloth_parser)
            self._cloth = self._cloth.getroot()

        if self._cloth is not None:
            q = "//*[@%s]" % self.root_attr_name
            elts = self._cloth.xpath(q)
            if len(elts) > 0:
                self._root_cloth = elts[0]

            q = "//*[@%s]" % self.attr_name
            if len(elts) == 0:
                self._cloth = None

        if self._cloth is not None:
            self._mrpc_cloth = self._pop_elt(self._cloth, 'mrpc_entry')

    @staticmethod
    def translate(cls, locale, default):
        """
        :param cls: class
        :param locale: locale string
        :param default: default string if no translation found
        :returns: translated string
        """

        if locale is None:
            locale = 'en_US'
        if cls.Attributes.translations is not None:
            return cls.Attributes.translations.get(locale, default)
        return default

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
            print ctx.out_stream, id(ctx.out_stream)

        if ctx.out_error is not None:
            # All errors at this point must be Fault subclasses.
            inst = ctx.out_error
            cls = inst.__class__
            name = cls.get_type_name()

            ctx.out_document = E.div()
            with etree.xmlfile(ctx.out_stream) as xf:
                # as XmlDocument is not push-ready yet, this is what we do.
                # this is a huge hack, bear with me.
                retval = XmlCloth.HtmlMicroFormat() \
                                            .to_parent(ctx, cls, inst, xf, name)

        else:
            assert message is self.RESPONSE
            result_message_class = ctx.descriptor.out_message

            name = result_message_class.get_type_name()
            if ctx.descriptor.body_style == BODY_STYLE_WRAPPED:
                if self.ignore_wrappers:
                    result_message = ctx.out_object[0]
                    while result_message_class.Attributes._wrapper and \
                                      len(result_message_class._type_info) == 1:
                        result_message_class, = \
                                        result_message_class._type_info.values()

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

    def create_out_string(self, ctx, charset=None):
        """Sets an iterable of string fragments to ctx.out_string"""

        if isinstance(ctx.out_stream, StringIO):
            ctx.out_string = [ctx.out_stream.getvalue()]

    @coroutine
    def incgen(self, ctx, cls, inst, name):
        if name is None:
            name = cls.get_type_name()

        try:
            with etree.xmlfile(ctx.out_stream) as xf:
                ret = self.subserialize(ctx, cls, inst, xf, name)
                if isgenerator(ret): # Poor man's yield from
                    try:
                        while True:
                            sv2 = (yield)
                            ret.send(sv2)

                    except Break as b:
                        try:
                            ret.throw(b)
                        except StopIteration:
                            pass
        except LxmlSyntaxError as e:
            if e.msg == 'no content written':
                pass
            else:
                raise

    def subserialize(self, ctx, cls, inst, parent, name=None, **kwargs):
        if name is None:
            name = cls.get_type_name()

        if self._root_cloth is not None:
            return self.to_root_cloth(ctx, cls, inst, self._root_cloth,
                                                         parent, name, **kwargs)

        if self._cloth is not None:
            return self.to_parent_cloth(ctx, cls, inst, self._cloth, parent,
                                                                 name, **kwargs)

        return self.to_parent(ctx, cls, inst, parent, name, **kwargs)

    def decompose_incoming_envelope(self, ctx, message):
        raise NotImplementedError("This is an output-only protocol.")
