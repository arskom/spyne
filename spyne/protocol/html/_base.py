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

from collections import defaultdict

from lxml import etree, html
from lxml.html.builder import E

from spyne.util import coroutine, Break, six
from spyne.util.oset import oset
from spyne.util.etreeconv import dict_to_etree

from spyne.protocol.cloth import XmlCloth
from spyne.protocol.cloth._base import XmlClothProtocolContext


def parse_html_fragment_file(T_FILES):
    elt = html.fromstring(open(T_FILES).read())
    elt.getparent().remove(elt)
    return elt


class HtmlClothProtocolContext(XmlClothProtocolContext):
    def __init__(self, parent, transport, type=None):
        super(HtmlClothProtocolContext, self).__init__(parent, transport, type)

        self.assets = []
        self.eltstack = defaultdict(list)
        self.ctxstack = defaultdict(list)
        self.rootstack = oset()
        self.tags = set()
        self.objcache = dict()

        # these are supposed to be for neurons.base.screen.ScreenBase subclasses
        self.screen = None
        self.prev_view = None
        self.next_view = None


class HtmlCloth(XmlCloth):
    mime_type = 'text/html; charset=UTF-8'

    def __init__(self, app=None, encoding='utf8',
                      mime_type=None, ignore_uncap=False, ignore_wrappers=False,
                                cloth=None, cloth_parser=None, polymorphic=True,
                             strip_comments=True, hier_delim='.', doctype=None):

        super(HtmlCloth, self).__init__(app=app, encoding=encoding,
                                 mime_type=mime_type, ignore_uncap=ignore_uncap,
                                   ignore_wrappers=ignore_wrappers, cloth=cloth,
                             cloth_parser=cloth_parser, polymorphic=polymorphic,
                                                  strip_comments=strip_comments)

        self.hier_delim = hier_delim
        self.doctype = doctype
        self.default_method = 'html'

    def _parse_file(self, file_name, cloth_parser):
        if cloth_parser is None:
            cloth_parser = html.HTMLParser()

        cloth = html.parse(file_name, parser=cloth_parser)
        return cloth.getroot()

    def docfile(self, *args, **kwargs):
        logger.debug("Starting file with %r %r", args, kwargs)
        return etree.htmlfile(*args, **kwargs)

    def get_context(self, parent, transport):
        return HtmlClothProtocolContext(parent, transport)

    @staticmethod
    def get_class_cloth(cls):
        return cls.Attributes._html_cloth

    @staticmethod
    def get_class_root_cloth(cls):
        return cls.Attributes._html_root_cloth

    def dict_to_parent(self, ctx, cls, inst, parent, name, **kwargs):
        parent.write(repr(inst))

    @staticmethod
    def add_html_attr(attr_name, attr_dict, class_name):
        if attr_name in attr_dict:
            attr_dict[attr_name] = ' '.join(
                                       (attr_dict.get('class', ''), class_name))
        else:
            attr_dict[attr_name] = class_name

    @staticmethod
    def add_style(attr_dict, data):
        style = attr_dict.get('style', None)

        if style is not None:
            attr_dict['style'] = ';'.join(style, data)

        else:
            attr_dict['style'] = data

    @staticmethod
    def selsafe(s):
        return s.replace('[', '').replace(']', '').replace('.', '__')

    @coroutine
    def complex_to_parent(self, ctx, cls, inst, parent, name, use_ns=False,
                                                                      **kwargs):
        inst = cls.get_serialization_instance(inst)

        # TODO: Put xml attributes as well in the below element() call.
        with parent.element(name):
            ret = self._write_members(ctx, cls, inst, parent, use_ns=False,
                                                                       **kwargs)
            if ret is not None:
                try:
                    while True:
                        sv2 = (yield)  # may throw Break
                        ret.send(sv2)

                except Break:
                    try:
                        ret.throw(Break())
                    except StopIteration:
                        pass

    def gen_anchor(self, cls, inst, name, anchor_class=None):
        assert name is not None
        cls_attrs = self.get_cls_attrs(cls)

        href = getattr(inst, 'href', None)
        if href is None: # this is not a AnyUri.Value instance.
            href = inst

            content = None
            text = cls_attrs.text

        else:
            content = getattr(inst, 'content', None)
            text = getattr(inst, 'text', None)
            if text is None:
                text = cls_attrs.text

        if anchor_class is None:
            anchor_class = cls_attrs.anchor_class

        if text is None:
            text = name

        retval = E.a(text)

        if href is not None:
            retval.attrib['href'] = href

        if anchor_class is not None:
            retval.attrib['class'] = anchor_class

        if content is not None:
            retval.append(content)

        return retval

    def any_uri_to_parent(self, ctx, cls, inst, parent, name, **kwargs):
        retval = self.gen_anchor(cls, inst, name)
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

    def byte_array_to_parent(self, ctx, cls, inst, parent, name, **kwargs):
        ret = self.to_unicode(cls, inst, self.binary_encoding)

        if ret is not None:
            parent.write(ret)

    def model_base_to_parent(self, ctx, cls, inst, parent, name, **kwargs):
        ret = self.to_unicode(cls, inst)

        if ret is not None:
            parent.write(ret)

    def null_to_parent(self, ctx, cls, inst, parent, name, **kwargs):
        pass

    def any_xml_to_parent(self, ctx, cls, inst, parent, name, **kwargs):
        if isinstance(inst, (six.text_type, six.binary_type)):
            inst = etree.fromstring(inst)

        parent.write(inst)

    def any_html_to_parent(self, ctx, cls, inst, parent, name, **kwargs):
        cls_attrs = self.get_cls_attrs(cls)

        if cls_attrs.as_string:
            if not (isinstance(inst, str) or isinstance(inst, six.text_type)):
                inst = html.tostring(inst)

        else:
            if isinstance(inst, str) or isinstance(inst, six.text_type):
                inst = html.fromstring(inst)

        parent.write(inst)

    def any_to_parent(self, ctx, cls, inst, parent, name, **kwargs):
        parent.write(inst)

    def any_dict_to_parent(self, ctx, cls, inst, parent, name, **kwargs):
        elt = E('foo')
        dict_to_etree(inst, elt)

        parent.write(elt[0])

    def fault_to_parent(self, ctx, cls, inst, parent, name, **kwargs):
        self.complex_to_parent(ctx, cls, inst, parent, name, **kwargs)


# FIXME: Deprecated
HtmlBase = HtmlCloth
