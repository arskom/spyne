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

from lxml import etree, html
from lxml.builder import E

from spyne.const.xml_ns import xsi as NS_XSI, soap_env as NS_SOAP_ENV
from spyne.model import PushBase, ComplexModelBase, AnyXml, Fault, AnyDict, \
    AnyHtml, ModelBase, ByteArray, XmlData
from spyne.model.enum import EnumBase
from spyne.protocol import ProtocolBase
from spyne.protocol.xml import SchemaValidationError
from spyne.util import coroutine, Break
from spyne.util.cdict import cdict
from spyne.util.etreeconv import dict_to_etree


# FIXME: Serialize xml attributes!!!
class ToParentMixin(ProtocolBase):
    def __init__(self, app=None, validator=None, mime_type=None,
                                     ignore_uncap=False, ignore_wrappers=False):
        super(ToParentMixin, self).__init__(app=app, validator=validator,
                                 mime_type=mime_type, ignore_uncap=ignore_uncap,
                                 ignore_wrappers=ignore_wrappers)

        self.serialization_handlers = cdict({
            AnyXml: self.xml_to_parent,
            Fault: self.fault_to_parent,
            AnyDict: self.dict_to_parent,
            AnyHtml: self.html_to_parent,
            EnumBase: self.enum_to_parent,
            ModelBase: self.base_to_parent,
            ByteArray: self.byte_array_to_parent,
            ComplexModelBase: self.complex_to_parent,
            SchemaValidationError: self.schema_validation_error_to_parent,
        })

    def to_parent(self, ctx, cls, inst, parent, name, **kwargs):
        subprot = getattr(cls.Attributes, 'prot', None)

        if subprot is not None and not (subprot is self):
            return subprot.subserialize(ctx, cls, inst, parent, name, **kwargs)

        handler = self.serialization_handlers[cls]
        if inst is None:
            inst = cls.Attributes.default

        if inst is None:
            return self.null_to_parent(ctx, cls, inst, parent, name, **kwargs)

        if issubclass(cls, ComplexModelBase) and self.ignore_wrappers:
            cls, inst = self.strip_wrappers(cls, inst)

        from_arr = kwargs.get('from_arr', False)
        if not from_arr and cls.Attributes.max_occurs > 1:
            return self.array_to_parent(ctx, cls, inst, parent, name, **kwargs)

        return handler(ctx, cls, inst, parent, name, **kwargs)

    def model_base_to_parent(self, ctx, cls, inst, parent, name, **kwargs):
        parent.write(E(name, self.to_string(cls, inst)))

    @coroutine
    def complex_model_to_parent(self, ctx, cls, inst, parent, name, **kwargs):
        with parent.element(name):
            ret = self._get_members(ctx, cls, inst, parent, **kwargs)
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
    def array_to_parent(self, ctx, cls, inst, parent, name, **kwargs):
        name = cls.get_type_name()
        if isinstance(inst, PushBase):
            while True:
                sv = (yield)
                print sv
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
            for sv in inst:
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

    @coroutine
    def _get_members(self, ctx, cls, inst, parent, **kwargs):
        for k, v in cls.get_flat_type_info(cls).items():
            print "_get_members", k, v
            try:
                subvalue = getattr(inst, k, None)
            except: # to guard against e.g. SqlAlchemy throwing NoSuchColumnError
                subvalue = None

            sub_name = v.Attributes.sub_name
            if sub_name is None:
                sub_name = k

            # Don't include empty values for non-nillable optional attributes.
            if subvalue is not None or v.Attributes.min_occurs > 0:
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

    def not_supported(self, cls, *args, **kwargs):
        if not self.ignore_uncap:
            raise NotImplementedError("Serializing %r not supported!" % cls)

    def anyhtml_to_parent(self, ctx, cls, inst, parent, name, **kwargs):
        parent.write(inst)

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
        parent.write(E(name,
                        self.to_string(cls, inst, self.default_binary_encoding)))

    def base_to_parent(self, ctx, cls, inst, parent, name, **kwargs):
        parent.write(E(name, self.to_string(cls, inst)))

    def null_to_parent(self, ctx, cls, inst, parent, ns, name, **kwargs):
        parent.write(E(name, **{'{%s}nil' % NS_XSI: 'true'}))

    @coroutine
    def _write_members(self, ctx, cls, inst, parent):
        parent_cls = getattr(cls, '__extends__', None)

        if not (parent_cls is None):
            ret = self._write_members(ctx, parent_cls, inst, parent)
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
            try: # to guard against e.g. SqlAlchemy throwing NoSuchColumnError
                subvalue = getattr(inst, k, None)
            except:
                subvalue = None

            # This is a tight loop, so enable this only when necessary.
            # logger.debug("get %r(%r) from %r: %r" % (k, v, inst, subvalue))

            if issubclass(v, XmlData):
                if subvalue is not None:
                    parent.write(self.to_string(k.type, subvalue))
                continue

            sub_ns = v.Attributes.sub_ns
            if sub_ns is None:
                sub_ns = cls.get_namespace()

            sub_name = v.Attributes.sub_name
            if sub_name is None:
                sub_name = k

            name = "{%s}%s" % (sub_ns, sub_name)
            if subvalue is not None or v.Attributes.min_occurs > 0:
                ret = self.to_parent(ctx, v, subvalue, parent, name)
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
    def complex_to_parent(self, ctx, cls, inst, parent, name):
        inst = cls.get_serialization_instance(inst)

        # TODO: Put xml attributes as well in the below element() call.
        with parent.element(name):
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
    def schema_validation_error_to_parent(self, ctx, cls, inst, parent, ns):
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

    def enum_to_parent(self, ctx, cls, inst, parent, ns, name='retval'):
        self.base_to_parent(ctx, cls, str(inst), parent, ns, name)

    def xml_to_parent(self, ctx, cls, inst, parent, ns, name):
        if isinstance(inst, basestring):
            inst = etree.fromstring(inst)

        parent.write(inst)

    def html_to_parent(self, ctx, cls, inst, parent, ns, name):
        if isinstance(inst, str) or isinstance(inst, unicode):
            inst = html.fromstring(inst)

        parent.write(inst)

    def dict_to_parent(self, ctx, cls, inst, parent, ns, name):
        elt = E(name)
        dict_to_etree(inst, elt)
        parent.write(elt)
