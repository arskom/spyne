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

from spyne.const.xml_ns import xsi as NS_XSI, soap11_env as NS_SOAP_ENV
from spyne.model import PushBase, ComplexModelBase, AnyXml, Fault, AnyDict, \
    AnyHtml, ModelBase, ByteArray, XmlData, Any, AnyUri, ImageUri
from spyne.model.enum import EnumBase
from spyne.protocol import OutProtocolBase
from spyne.protocol.xml import SchemaValidationError
from spyne.util import coroutine, Break, six
from spyne.util.web import log_repr
from spyne.util.cdict import cdict
from spyne.util.etreeconv import dict_to_etree


# FIXME: Serialize xml attributes!!!
from spyne.util.six import string_types


class ToParentMixin(OutProtocolBase):
    def __init__(self, app=None, mime_type=None,
                 ignore_uncap=False, ignore_wrappers=False, polymorphic=True):
        super(ToParentMixin, self).__init__(app=app,
                                 mime_type=mime_type, ignore_uncap=ignore_uncap,
                                 ignore_wrappers=ignore_wrappers)

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

    def to_subprot(self, ctx, cls, inst, parent, name, subprot, **kwargs):
        return subprot.subserialize(ctx, cls, inst, parent, name, **kwargs)

    def to_parent(self, ctx, cls, inst, parent, name, nosubprot=False, **kwargs):
        prot_name = self.__class__.__name__

        cls, switched = self.get_polymorphic_target(cls, inst)

        # if there is a subprotocol, switch to it
        subprot = getattr(cls.Attributes, 'prot', None)
        if subprot is not None and not nosubprot and not \
                                           (subprot in ctx.protocol.prot_stack):
            logger.debug("Subprot from %r to %r", self, subprot)
            return self.to_subprot(ctx, cls, inst, parent, name, subprot,
                                                                       **kwargs)

        # if there is a class cloth, switch to it
        ret, cor_handle = self.check_class_cloths(ctx, cls, inst, parent, name,
                                                                       **kwargs)
        if ret:
            return cor_handle

        # if instance is None, use the default factory to generate one
        _df = cls.Attributes.default_factory
        if inst is None and callable(_df):
            inst = _df()

        # if instance is still None, use the default value
        if inst is None:
            inst = cls.Attributes.default

        # if instance is still None, use the global null handler to serialize it
        if inst is None and self.use_global_null_handler:
            identifier = prot_name + '.null_to_parent'
            logger.debug("Writing %s using %s for %s.", name, identifier,
                                                            cls.get_type_name())
            return self.null_to_parent(ctx, cls, inst, parent, name, **kwargs)

        # if requested, ignore wrappers
        if self.ignore_wrappers and issubclass(cls, ComplexModelBase):
            cls, inst = self.strip_wrappers(cls, inst)

        # if cls is an iterable of values and it's not been iterated on, do it
        from_arr = kwargs.get('from_arr', False)
        if not from_arr and cls.Attributes.max_occurs > 1:
            return self.array_to_parent(ctx, cls, inst, parent, name, **kwargs)

        # fetch the serializer for the class at hand
        try:
            handler = self.serialization_handlers[cls]
        except KeyError:
            # if this protocol uncapable of serializing this class
            if self.ignore_uncap:
                logger.debug("Ignore uncap %r", name)
                return  # ignore it if requested

            # raise the error otherwise
            logger.error("%r is missing handler for %r for field %r",
                                                                self, cls, name)
            raise

        # push the instance at hand to instance stack. this makes it easier for
        # protocols to make decisions based on parents of instances at hand.
        ctx.outprot_ctx.inst_stack.append( (cls, inst) )

        # finally, serialize the value. retval is the coroutine handle if any
        identifier = "%s.%s" % (prot_name, handler.__name__)
        log_str = log_repr(inst, cls, from_array=kwargs.get('from_arr', None))
        logger.debug("Writing %s using %s for %s. Inst: %r", name,
                                       identifier, cls.get_type_name(), log_str)

        retval = handler(ctx, cls, inst, parent, name, **kwargs)

        # FIXME: to_parent must be made to a coroutine for the below to remain
        #        consistent when Iterable.Push is used.
        ctx.outprot_ctx.inst_stack.pop()

        return retval

    def model_base_to_parent(self, ctx, cls, inst, parent, name, **kwargs):
        parent.write(E(name, self.to_unicode(cls, inst)))

    @coroutine
    def array_to_parent(self, ctx, cls, inst, parent, name, **kwargs):
        if inst is None:
            inst = []

        if isinstance(inst, PushBase):
            while True:
                sv = (yield)
                ret = self.to_parent(ctx, cls, sv, parent, name, from_arr=True,
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

        else:
            assert isinstance(inst, Iterable), ("%r is not iterable" % inst)

            for i, sv in enumerate(inst):
                kwargs['from_arr'] = True
                kwargs['array_index'] = i
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

    def not_supported(self, ctx, cls, *args, **kwargs):
        if not self.ignore_uncap:
            raise NotImplementedError("Serializing %r not supported!" % cls)

    def anyuri_to_parent(self, ctx, cls, inst, parent, name, **kwargs):
        assert name is not None
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

        if text is None:
            text = name

        retval = E.a(text)

        if href is not None:
            retval.attrib['href'] = href

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
            ret = self._write_members(ctx, parent_cls, inst, parent, **kwargs)
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

        for k, v in cls._type_info.items():
            attr = self.get_cls_attrs(v)
            if attr.exc:
                prot_name = self.__class__.__name__
                logger.debug("%s: excluded for %s.", k, prot_name)
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

        # TODO: Put xml attributes as well in the below element() call.
        with parent.element(name):
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

    @coroutine
    def fault_to_parent(self, ctx, cls, inst, parent, name):
        PREF_SOAP_ENV = ctx.app.interface.prefmap[NS_SOAP_ENV]
        tag_name = "{%s}Fault" % NS_SOAP_ENV

        with parent.element(tag_name):
            parent.write(
                E("faultcode", '%s:%s' % (PREF_SOAP_ENV, inst.faultcode)),
                E("faultstring", inst.faultstring),
                E("faultactor", inst.faultactor),
            )

            if isinstance(etree._Element):
                parent.write(E.detail(inst.detail))

            # add other nonstandard fault subelements with get_members_etree
            ret = self._write_members(ctx, cls, inst, parent)
            if ret is not None:
                try:
                    while True:
                        sv2 = (yield) # may throw Break
                        ret.send(sv2)

                except Break:
                    try:
                        ret.throw(Break())
                    except StopIteration:
                        pass

    @coroutine
    def schema_validation_error_to_parent(self, ctx, cls, inst, parent, **_):
        PREF_SOAP_ENV = ctx.app.interface.prefmap[NS_SOAP_ENV]
        tag_name = "{%s}Fault" % NS_SOAP_ENV

        with parent.element(tag_name):
            parent.write(
                E("faultcode", '%s:%s' % (PREF_SOAP_ENV, inst.faultcode)),
                # HACK: Does anyone know a better way of injecting raw xml entities?
                E("faultstring", html.fromstring(inst.faultstring).text),
                E("faultactor", inst.faultactor),
            )
            if isinstance(etree._Element):
                parent.write(E.detail(inst.detail))

            # add other nonstandard fault subelements with get_members_etree
            ret = self._write_members(ctx, cls, inst, parent)
            if ret is not None:
                try:
                    while True:
                        sv2 = (yield) # may throw Break
                        ret.send(sv2)

                except Break:
                    try:
                        ret.throw(Break())
                    except StopIteration:
                        pass

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
