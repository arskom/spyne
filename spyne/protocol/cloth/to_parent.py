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
from spyne.util.six.moves.collections_abc import Iterable

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

from spyne.util.six import string_types


class ToParentMixin(OutProtocolBase):
    def __init__(self, app=None, mime_type=None, ignore_uncap=False,
                                       ignore_wrappers=False, polymorphic=True):
        super(ToParentMixin, self).__init__(app=app, mime_type=mime_type,
                     ignore_uncap=ignore_uncap, ignore_wrappers=ignore_wrappers)

        self.polymorphic = polymorphic
        self.use_global_null_handler = True

        self.serialization_handlers = cdict({
            ModelBase: self.model_base_to_parent,

            AnyXml: self.any_xml_to_parent,
            AnyUri: self.any_uri_to_parent,
            ImageUri: self.imageuri_to_parent,
            AnyDict: self.any_dict_to_parent,
            AnyHtml: self.any_html_to_parent,
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
        if not ctx.outprot_ctx.doctype_written:
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
        if cls_attrs.out_type:
            logger.debug("out_type from %r to %r", cls, cls_attrs.out_type)
            cls = cls_attrs.out_type
            cls_attrs = self.get_cls_attrs(cls)

        inst = self._sanitize(cls_attrs, inst)

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

                # if cls is an iterable of values and it's not being iterated
                # on, do it
                from_arr = kwargs.get('from_arr', False)
                # we need cls.Attributes here because we need the ACTUAL attrs
                # that were set by the Array.__new__
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
                    logger.debug("%s %r pushed %r using %r",
                                                     R("$"), self, cls, handler)

                    # disabled for performance reasons
                    # from spyne.util.web import log_repr
                    # identifier = "%s.%s" % (prot_name, handler.__name__)
                    # log_str = log_repr(inst, cls,
                    #                   from_array=kwargs.get('from_arr', None))
                    # logger.debug("Writing %s using %s for %s. Inst: %r", name,
                    #                  identifier, cls.get_type_name(), log_str)

                    # finally, serialize the value. ret is the coroutine handle
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

                    # disabled because to_parent is supposed to take care of this
                    #ctx.protocol.inst_stack.append((cls, sv, True))
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
                            # disabled because to_parent is supposed to take care of this
                            #popped_val = ctx.protocol.inst_stack.pop()
                            #assert popped_val is sv

                            if ser_subprot is not None:
                                ser_subprot.column_table_before_row(ctx, cls,
                                                   inst, parent, name, **kwargs)
                    else:
                        # disabled because to_parent is supposed to take care of this
                        #popped_val = ctx.protocol.inst_stack.pop()
                        #assert popped_val is sv

                        if ser_subprot is not None:
                            ser_subprot.column_table_after_row(ctx, cls, inst,
                                                         parent, name, **kwargs)

            except Break:
                # pusher is done with pushing
                pass

        else:
            assert isinstance(inst, Iterable), ("%r is not iterable" % (inst,))

            for i, sv in enumerate(inst):
                # disabled because to_parent is supposed to take care of this
                #ctx.protocol.inst_stack.append((cls, sv, True)
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
                        # disabled because to_parent is supposed to take care of this
                        #popped_val = ctx.protocol.inst_stack.pop()
                        #assert popped_val is sv

                        if ser_subprot is not None:
                            ser_subprot.column_table_after_row(ctx, cls, inst,
                                                         parent, name, **kwargs)

                else:
                    # disabled because to_parent is supposed to take care of this
                    #popped_val = ctx.protocol.inst_stack.pop()
                    #assert popped_val is sv

                    if ser_subprot is not None:
                        ser_subprot.column_table_after_row(ctx, cls, inst,
                                                         parent, name, **kwargs)

    def not_supported(self, ctx, cls, *args, **kwargs):
        if not self.ignore_uncap:
            raise NotImplementedError("Serializing %r not supported!" % cls)

    def any_uri_to_parent(self, ctx, cls, inst, parent, name, **kwargs):
        self.model_base_to_parent(ctx, cls, inst, parent, name, **kwargs)

    def imageuri_to_parent(self, ctx, cls, inst, parent, name, **kwargs):
        self.model_base_to_parent(ctx, cls, inst, parent, name, **kwargs)

    def byte_array_to_parent(self, ctx, cls, inst, parent, name, **kwargs):
        parent.write(E(name, self.to_unicode(cls, inst, self.binary_encoding)))

    def model_base_to_parent(self, ctx, cls, inst, parent, name, **kwargs):
        parent.write(E(name, self.to_unicode(cls, inst)))

    def null_to_parent(self, ctx, cls, inst, parent, name, **kwargs):
        parent.write(E(name, **{'{%s}nil' % NS_XSI: 'true'}))

    def enum_to_parent(self, ctx, cls, inst, parent, name, **kwargs):
        self.model_base_to_parent(ctx, cls, str(inst), parent, name)

    def any_xml_to_parent(self, ctx, cls, inst, parent, name, **kwargs):
        if isinstance(inst, string_types):
            inst = etree.fromstring(inst)

        parent.write(E(name, inst))

    def any_html_to_unicode(self, cls, inst, **_):
        if isinstance(inst, (str, six.text_type)):
            inst = html.fromstring(inst)

        return inst

    def any_html_to_parent(self, ctx, cls, inst, parent, name, **kwargs):
        cls_attrs = self.get_cls_attrs(cls)

        if cls_attrs.as_string:
            if not (isinstance(inst, str) or isinstance(inst, six.text_type)):
                inst = html.tostring(inst)

        else:
            if isinstance(inst, str) or isinstance(inst, six.text_type):
                inst = html.fromstring(inst)

        parent.write(E(name, inst))

    def any_to_parent(self, ctx, cls, inst, parent, name, **kwargs):
        parent.write(E(name, inst))

    def any_dict_to_parent(self, ctx, cls, inst, parent, name, **kwargs):
        elt = E(name)
        dict_to_etree(inst, elt)
        parent.write(E(name, elt))

    def _gen_sub_name(self, cls, cls_attrs, k, use_ns=None):
        if self.use_ns is not None and use_ns is None:
            use_ns = self.use_ns

        sub_ns = cls_attrs.sub_ns
        if sub_ns is None:
            sub_ns = cls.get_namespace()

        sub_name = cls_attrs.sub_name
        if sub_name is None:
            sub_name = k

        if use_ns:
            name = "{%s}%s" % (sub_ns, sub_name)
        else:
            name = sub_name

        return name

    @coroutine
    def _write_members(self, ctx, cls, inst, parent, use_ns=None, **kwargs):
        if self.use_ns is not None and use_ns is None:
            use_ns = self.use_ns

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

            sub_name = self._gen_sub_name(cls, attr, k, use_ns)

            if issubclass(v, XmlData):
                if issubclass(v.type, AnyXml):
                    parent.write(subvalue)
                else:
                    subvalstr = self.to_unicode(v.type, subvalue)
                    if subvalstr is not None:
                        parent.write(subvalstr)
                continue

            if subvalue is not None or attr.min_occurs > 0:
                ret = self.to_parent(ctx, v, subvalue, parent, sub_name,
                                                        use_ns=use_ns, **kwargs)
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
    def _complex_to_parent_do(self, ctx, cls, inst, parent, **kwargs):
        # parent.write(u"\u200c")  # zero-width non-joiner
        parent.write(" ")  # FIXME: to force empty tags to be sent as
        # <a></a> instead of <a/>
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

    def complex_to_parent(self, ctx, cls, inst, parent, name,
                                         from_arr=False, use_ns=None, **kwargs):
        if not from_arr:
            inst = cls.get_serialization_instance(inst)

        attrib = self._gen_attrib_dict(inst, cls.get_flat_type_info(cls))

        if self.skip_root_tag:
            self._complex_to_parent_do(ctx, cls, inst, parent,
                                                    from_arr=from_arr, **kwargs)

        else:
            if name is None or name == '':
                name = self._gen_sub_name(cls, self.get_cls_attrs(cls),
                                                    cls.get_type_name(), use_ns)
                logger.debug("name is empty, long live name: %s, cls: %r",
                                                                      name, cls)

            with parent.element(name, attrib=attrib):
                self._complex_to_parent_do(ctx, cls, inst, parent,
                                                    from_arr=from_arr, **kwargs)

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
