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

from spyne.util import six, coroutine, Break
from spyne.util.cdict import cdict

from spyne.model import Array, AnyHtml, ComplexModelBase, ByteArray, \
    ModelBase, PushBase, ImageUri, AnyUri

from spyne.protocol.html import HtmlBase


class HtmlMicroFormat(HtmlBase):
    def __init__(self, app=None, ignore_uncap=False, ignore_wrappers=False,
                                cloth=None, cloth_parser=None, polymorphic=True,
                                                      doctype="<!DOCTYPE html>",
                       root_tag='div', child_tag='div', field_name_attr='class',
                             field_name_tag=None, field_name_class='field_name',
                                                        before_first_root=None):
        """Protocol that returns the response object according to the "html
        microformat" specification. See
        https://en.wikipedia.org/wiki/Microformats for more info.

        The simple flavour is like the XmlDocument protocol, but returns data in
        <div> or <span> tags.

        :param app: A spyne.application.Application instance.
        :param root_tag: The type of the root tag that encapsulates the return
            data.
        :param child_tag: The type of the tag that encapsulates the fields of
            the returned object.
        :param field_name_attr: The name of the attribute that will contain the
            field names of the complex object children.
        """

        super(HtmlMicroFormat, self).__init__(app=app,
                     ignore_uncap=ignore_uncap, ignore_wrappers=ignore_wrappers,
                cloth=cloth, cloth_parser=cloth_parser, polymorphic=polymorphic,
                                               hier_delim=None, doctype=doctype)

        if six.PY2:
            text_type = basestring
        else:
            text_type = str

        assert isinstance(root_tag, text_type)
        assert isinstance(child_tag, text_type)
        assert isinstance(field_name_attr, text_type)
        assert field_name_tag is None or isinstance(field_name_tag, text_type)

        self.root_tag = root_tag
        self.child_tag = child_tag
        self.field_name_attr = field_name_attr
        self.field_name_tag = field_name_tag
        if field_name_tag is not None:
            self.field_name_tag = E(field_name_tag)
        self._field_name_class = field_name_class
        if before_first_root is not None:
            self.event_manager.add_listener("before_first_root",
                                                              before_first_root)

        self.serialization_handlers = cdict({
            Array: self.array_to_parent,
            AnyUri: self.any_uri_to_parent,
            AnyHtml: self.any_html_to_parent,
            ImageUri: self.imageuri_to_parent,
            ByteArray: self.not_supported,
            ModelBase: self.model_base_to_parent,
            ComplexModelBase: self.complex_model_to_parent,
        })

    def anyuri_to_parent(self, ctx, cls, inst, parent, name, **kwargs):
        retval = self.gen_anchor(cls, inst, parent)
        retval.attrib[self.field_name_attr] = name
        parent.write(retval)

    def model_base_to_parent(self, ctx, cls, inst, parent, name, **kwargs):
        retval = E(self.child_tag, **{self.field_name_attr: name})
        data_str = self.to_unicode(cls, inst)

        if self.field_name_tag is not None:
            field_name = cls.Attributes.translations.get( name)
            field_name_tag = self.field_name_tag(field_name,
                                             **{'class':self._field_name_class})
            field_name_tag.tail = data_str
            retval.append(field_name_tag)

        else:
            retval.text = data_str

        parent.write(retval)

    def start_to_parent(self, ctx, cls, inst, parent, name, **kwargs):
        """This is what subserialize calls"""

        # if no doctype was written, write it
        if not getattr(ctx.outprot_ctx, 'doctype_written', False):
            if len(ctx.protocol.prot_stack) == 1:
                if self.doctype is not None:
                    parent.write_doctype(self.doctype)

            # set this to true as no doctype can be written after this
            # stage anyway.
            ctx.outprot_ctx.doctype_written = True

        return self.to_parent(ctx, cls, inst, parent, name, **kwargs)

    @coroutine
    def complex_model_to_parent(self, ctx, cls, inst, parent, name,
                                                        use_ns=False, **kwargs):
        attrs = {self.field_name_attr: name}

        if not getattr(ctx.protocol, 'before_first_root', False):
            self.event_manager.fire_event("before_first_root",
                                         ctx, cls, inst, parent, name, **kwargs)
            ctx.protocol.before_first_root = True

        with parent.element(self.root_tag, attrs):
            ret = self._write_members(ctx, cls, inst, parent, use_ns=False,
                                                                       **kwargs)
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

    @coroutine
    def array_to_parent(self, ctx, cls, inst, parent, name, from_arr=False, **kwargs):
        attrs = {self.field_name_attr: name}

        if issubclass(cls, Array):
            cls, = cls._type_info.values()

        name = cls.get_type_name()
        with parent.element(self.root_tag, attrs):
            if isinstance(inst, PushBase):
                while True:
                    sv = (yield)
                    ret = self.to_parent(ctx, cls, sv, parent, name,
                                                        from_arr=True, **kwargs)
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
                    ret = self.to_parent(ctx, cls, sv, parent, name,
                                                        from_arr=True, **kwargs)
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

    def null_to_parent(self, ctx, cls, inst, parent, name, **kwargs):
        return [ E(self.child_tag, **{self.field_name_attr: name}) ]

# FIXME: yuck.
from spyne.protocol.cloth import XmlCloth
XmlCloth.HtmlMicroFormat = HtmlMicroFormat
