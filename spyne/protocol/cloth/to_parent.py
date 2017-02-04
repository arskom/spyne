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

from __future__ import print_function

import logging
logger = logging.getLogger(__name__)

from inspect import isgenerator
from collections import Iterable

from lxml import etree, html
from lxml.builder import E

from spyne.const.xml import NS_XSI, NS_SOAP11_ENV, SOAP11_ENV
from spyne.model import PushBase, ComplexModelBase, AnyXml, Fault, AnyDict, \
    AnyHtml, ModelBase, ByteArray, XmlData, Any, AnyUri, ImageUri, XmlAttribute

from spyne.model.enum import EnumBase
from spyne.protocol import OutProtocolBase
from spyne.protocol.xml import SchemaValidationError
from spyne.util import coroutine, Break, six
from spyne.util.cdict import cdict
from spyne.util.etreeconv import dict_to_etree
from spyne.util.color import R, B


# FIXME: Serialize xml attributes!!!
from spyne.util.six import string_types


class ToParentMixin(OutProtocolBase):
    def __init__(self, app=None, mime_type=None, ignore_uncap=False,
                                       ignore_wrappers=False, polymorphic=True):
        super(ToParentMixin, self).__init__(app=app, mime_type=mime_type,
                     ignore_uncap=ignore_uncap, ignore_wrappers=ignore_wrappers)

        self.polymorphic = polymorphic
        self.use_global_null_handler = True

        self.serialization_handlers = cdict({
            ModelBase: self.base_to_parent,

            AnyXml: self.xml_to_parent,
            AnyUri: self.anyuri_to_parent,
            ImageUri: self.imageuri_to_parent,
            AnyDict: self.dict_to_parent,
            AnyHtml: self.html_to_parent,
            Any: self.any_to_parent,

            Fault: self.fault_to_parent,
            EnumBase: self.enum_to_parent,
            ByteArray: self.byte_array_to_parent,
            ComplexModelBase: self.complex_to_parent,
            SchemaValidationError: self.schema_validation_error_to_parent,
        })

    def start_to_parent(self, ctx, cls, inst, parent, name, **kwargs):
        """This is what subserialize calls"""

        # if no doctype was written, write it
        if not getattr(ctx.protocol, 'doctype_written', False):
            self.write_doctype(ctx, parent)

        return self.to_parent(ctx, cls, inst, parent, name, **kwargs)

    @staticmethod
    def get_subprot(ctx, cls_attrs, nosubprot=False):
        subprot = cls_attrs.prot
        if subprot is not None and not nosubprot and not \
                                           (subprot in ctx.protocol.prot_stack):
            return subprot
        return None

    def to_subprot(self, ctx, cls, inst, parent, name, subprot, **kwargs):
        return subprot.subserialize(ctx, cls, inst, parent, name, **kwargs)

    @coroutine
    def to_parent(self, ctx, cls, inst, parent, name, nosubprot=False, **kwargs):
        pushed = False
        has_cloth = False

        prot_name = self.__class__.__name__

        cls, switched = self.get_polymorphic_target(cls, inst)
        cls_attrs = self.get_cls_attrs(cls)

        # if there is a subprotocol, switch to it
        subprot = self.get_subprot(ctx, cls_attrs, nosubprot)
        if subprot is not None:
            logger.debug("Subprot from %r to %r", self, subprot)
            ret = self.to_subprot(ctx, cls, inst, parent, name, subprot,
                                                                       **kwargs)
        else:
            # if there is a class cloth, switch to it
            has_cloth, cor_handle = self.check_class_cloths(ctx, cls, inst,
                                                         parent, name, **kwargs)
            if has_cloth:
                ret = cor_handle

            else:
                # if instance is None, use the default factory to generate one
                _df = cls_attrs.default_factory
                if inst is None and callable(_df):
                    inst = _df()

                # if instance is still None, use the default value
                if inst is None:
                    inst = cls_attrs.default

                # if instance is still None, use the global null handler to
                # serialize it
                if inst is None and self.use_global_null_handler:
                    identifier = prot_name + '.null_to_parent'
                    logger.debug("Writing %s using %s for %s.", name,
                                                identifier, cls.get_type_name())
                    self.null_to_parent(ctx, cls, inst, parent, name, **kwargs)

                    return

                # if requested, ignore wrappers
                if self.ignore_wrappers and issubclass(cls, ComplexModelBase):
                    cls, inst = self.strip_wrappers(cls, inst)

                # if cls is an iterable of values and it's not being iterated on, do it
                from_arr = kwargs.get('from_arr', False)
                # we need cls.Attributes here because we need the ACTUAL attrs that were
                # set by the Array.__new__
                if not from_arr and cls.Attributes.max_occurs > 1:
                    ret = self.array_to_parent(ctx, cls, inst, parent, name,
                                                                       **kwargs)
                else:
                    # fetch the serializer for the class at hand
                    try:
                        handler = self.serialization_handlers[cls]

                    except KeyError:
                        # if this protocol uncapable of serializing this class
                        if self.ignore_uncap:
                            logger.debug("Ignore uncap %r", name)
                            return  # ignore it if requested

                        # raise the error otherwise
                        logger.error("%r is missing handler for "
                                             "%r for field %r", self, cls, name)
                        raise

                    # push the instance at hand to instance stack. this makes it
                    # easier for protocols to make decisions based on parents
                    # of instances at hand.
                    ctx.outprot_ctx.inst_stack.append( (cls, inst, from_arr) )
                    pushed = True
                    logger.debug("%s %r pushed %r %r", R("$"), self, cls, inst)

                    # disabled for performance reasons
                    # from spyne.util.web import log_repr
                    # identifier = "%s.%s" % (prot_name, handler.__name__)
                    # log_str = log_repr(inst, cls,
                    #                   from_array=kwargs.get('from_arr', None))
                    # logger.debug("Writing %s using %s for %s. Inst: %r", name,
                    #                  identifier, cls.get_type_name(), log_str)

                    # finally, serialize the value. retval is the coroutine
                    # handle if any
                    ret = handler(ctx, cls, inst, parent, name, **kwargs)

        if isgenerator(ret):
            try:
                while True:
                    sv2 = (yield)
                    ret.send(sv2)

            except Break as e:
                try:
                    ret.throw(e)

                except (Break, StopIteration, GeneratorExit):
                    pass

                finally:
                    if has_cloth:
                        self._close_cloth(ctx, parent)

                    if pushed:
                        logger.debug("%s %r popped %r %r", B("$"), self, cls,
                                                                           inst)
                        ctx.outprot_ctx.inst_stack.pop()

        else:
            if has_cloth:
                self._close_cloth(ctx, parent)

            if pushed:
                logger.debug("%s %r popped %r %r", B("$"), self, cls, inst)
                ctx.outprot_ctx.inst_stack.pop()

    def model_base_to_parent(self, ctx, cls, inst, parent, name, **kwargs):
        parent.write(E(name, self.to_unicode(cls, inst)))

    @coroutine
    def array_to_parent(self, ctx, cls, inst, parent, name, **kwargs):
        if inst is None:
            inst = ()

        ser_subprot = self.get_subprot(ctx, self.get_cls_attrs(cls))

        # FIXME: it's sad that this function has the same code twice.

        if isinstance(inst, PushBase):
            # this will be popped by pusher_try_close
            ctx.pusher_stack.append(inst)

            i = 0

            try:
                while True:
                    sv = (yield)

                    ctx.protocol.inst_stack.append(sv)
                    kwargs['from_arr'] = True
                    kwargs['array_index'] = i

                    if ser_subprot is not None:
                        ser_subprot.column_table_before_row(ctx, cls, inst,
                                                         parent, name, **kwargs)

                    ret = self.to_parent(ctx, cls, sv, parent, name, **kwargs)

                    i += 1
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

                        finally:
                            popped_val = ctx.protocol.inst_stack.pop()
                            assert popped_val is sv

                            if ser_subprot is not None:
                                ser_subprot.column_table_before_row(ctx, cls,
                                                   inst, parent, name, **kwargs)
                    else:
                        popped_val = ctx.protocol.inst_stack.pop()
                        assert popped_val is sv

                        if ser_subprot is not None:
                            ser_subprot.column_table_after_row(ctx, cls, inst,
                                                         parent, name, **kwargs)

            except Break:
                # pusher is done with pushing
                pass

        else:
            assert isinstance(inst, Iterable), ("%r is not iterable" % (inst,))

            for i, sv in enumerate(inst):
                ctx.protocol.inst_stack.append(sv)
                kwargs['from_arr'] = True
                kwargs['array_index'] = i

                if ser_subprot is not None:
                    ser_subprot.column_table_before_row(ctx, cls, inst, parent,
                                                                 name, **kwargs)

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

                    finally:
                        popped_val = ctx.protocol.inst_stack.pop()
                        assert popped_val is sv

                        if ser_subprot is not None:
                            ser_subprot.column_table_after_row(ctx, cls, inst,
                                                         parent, name, **kwargs)

                else:
                    popped_val = ctx.protocol.inst_stack.pop()
                    assert popped_val is sv

                    if ser_subprot is not None:
                        ser_subprot.column_table_after_row(ctx, cls, inst,
                                                         parent, name, **kwargs)

    def not_supported(self, ctx, cls, *args, **kwargs):
        if not self.ignore_uncap:
            raise NotImplementedError("Serializing %r not supported!" % cls)

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

    def anyuri_to_parent(self, ctx, cls, inst, parent, name, **kwargs):
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
        parent.write(E(name, self.to_unicode(cls, inst, self.binary_encoding)))

    def base_to_parent(self, ctx, cls, inst, parent, name, **kwargs):
        parent.write(E(name, self.to_unicode(cls, inst)))

    def null_to_parent(self, ctx, cls, inst, parent, name, **kwargs):
        parent.write(E(name, **{'{%s}nil' % NS_XSI: 'true'}))

    @coroutine
    def _write_members(self, ctx, cls, inst, parent, use_ns=True, **kwargs):
        parent_cls = getattr(cls, '__extends__', None)

        if not (parent_cls is None):
            ret = self._write_members(ctx, parent_cls, inst, parent,
                                                        use_ns=use_ns, **kwargs)
            if ret is not None:
                try:
                    while True:
                        sv2 = (yield)
                        ret.send(sv2)

                except Break:
                    try:
                        ret.throw(Break())
                    except StopIteration:
                        pass

        for k, v in self.sort_fields(cls):
            attr = self.get_cls_attrs(v)
            if attr.exc:
                prot_name = self.__class__.__name__
                logger.debug("%s: excluded for %s.", k, prot_name)
                continue

            if issubclass(v, XmlAttribute):
                continue

            try:  # e.g. SqlAlchemy could throw NoSuchColumnError
                subvalue = getattr(inst, k, None)
            except:
                subvalue = None

            # This is a tight loop, so enable this only when necessary.
            # logger.debug("get %r(%r) from %r: %r" % (k, v, inst, subvalue))

            sub_ns = attr.sub_ns
            if sub_ns is None:
                sub_ns = cls.get_namespace()

            sub_name = attr.sub_name
            if sub_name is None:
                sub_name = k

            if use_ns:
                name = "{%s}%s" % (sub_ns, sub_name)
            else:
                name = sub_name

            if issubclass(v, XmlData):
                if subvalue is not None:
                    self.to_parent(ctx, v, inst, parent, name=name, **kwargs)
                continue

            if subvalue is not None or attr.min_occurs > 0:
                ret = self.to_parent(ctx, v, subvalue, parent, name, **kwargs)
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

    @coroutine
    def complex_to_parent(self, ctx, cls, inst, parent, name, **kwargs):
        inst = cls.get_serialization_instance(inst)

        attrs = self._gen_attr_dict(inst, cls.get_flat_type_info(cls))

        with parent.element(name, attrib=attrs):
            parent.write(" ")
            ret = self._write_members(ctx, cls, inst, parent, **kwargs)
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

    def fault_to_parent(self, ctx, cls, inst, parent, name):
        PREF_SOAP_ENV = ctx.app.interface.prefmap[NS_SOAP11_ENV]
        tag_name = SOAP11_ENV("Fault")

        with parent.element(tag_name):
            parent.write(
                E("faultcode", '%s:%s' % (PREF_SOAP_ENV, inst.faultcode)),
                E("faultstring", inst.faultstring),
                E("faultactor", inst.faultactor),
            )

            if isinstance(inst.detail, etree._Element):
                parent.write(E.detail(inst.detail))

            # add other nonstandard fault subelements with get_members_etree
            self._write_members(ctx, cls, inst, parent)
            # no need to track the returned generator because we expect no
            # PushBase instance here.

    def schema_validation_error_to_parent(self, ctx, cls, inst, parent, **_):
        PREF_SOAP_ENV = ctx.app.interface.prefmap[NS_SOAP11_ENV]
        tag_name = SOAP11_ENV("Fault")

        with parent.element(tag_name):
            parent.write(
                E("faultcode", '%s:%s' % (PREF_SOAP_ENV, inst.faultcode)),
                # HACK: Does anyone know a better way of injecting raw xml entities?
                E("faultstring", html.fromstring(inst.faultstring).text),
                E("faultactor", inst.faultactor),
            )

            if isinstance(inst.detail, etree._Element):
                parent.write(E.detail(inst.detail))

            # add other nonstandard fault subelements with get_members_etree
            self._write_members(ctx, cls, inst, parent)
            # no need to track the returned generator because we expect no
            # PushBase instance here.

    def enum_to_parent(self, ctx, cls, inst, parent, name, **kwargs):
        self.base_to_parent(ctx, cls, str(inst), parent, name)

    def xml_to_parent(self, ctx, cls, inst, parent, name, **kwargs):
        if isinstance(inst, string_types):
            inst = etree.fromstring(inst)

        parent.write(inst)

    def html_to_parent(self, ctx, cls, inst, parent, name, **kwargs):
        if isinstance(inst, str) or isinstance(inst, six.text_type):
            inst = html.fromstring(inst)

        parent.write(inst)

    def any_to_parent(self, ctx, cls, inst, parent, name, **kwargs):
        parent.write(inst)

    def dict_to_parent(self, ctx, cls, inst, parent, name, **kwargs):
        elt = E(name)
        dict_to_etree(inst, elt)
        parent.write(elt)
