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

# TODO: strip comments without removing e.g. <!--[if lt IE 9]>


from __future__ import print_function

import logging
logger_c = logging.getLogger("%s.cloth" % __name__)
logger_s = logging.getLogger("%s.serializer" % __name__)

from lxml import html, etree
from copy import deepcopy
from inspect import isgenerator

from spyne.util import Break, coroutine
from spyne.util.web import log_repr
from spyne.util.oset import oset
from spyne.util.six import string_types
from spyne.model import Array, AnyXml, AnyHtml, ModelBase, ComplexModelBase, \
    PushBase, XmlAttribute, File, ByteArray, AnyUri, XmlData, Any

from spyne.protocol import OutProtocolBase
from spyne.util.cdict import cdict

_revancestors = lambda elt: list(reversed(tuple(elt.iterancestors())))


def _prevsibls(elt, since=None):
    return reversed(list(_prevsibls_since(elt, since)))


def _prevsibls_since(elt, since):
    if since is elt:
        return

    for prevsibl in elt.itersiblings(preceding=True):
        if prevsibl is since:
            break
        yield prevsibl


def _gen_tagname(ns, name):
    if ns is not None:
        name = "{%s}%s" % (ns, name)
    return name


class ClothParserMixin(object):
    ID_ATTR_NAME = 'spyne-id'
    DATA_TAG_NAME = 'spyne-data'
    ROOT_ATTR_NAME = 'spyne-root'

    @classmethod
    def from_xml_cloth(cls, cloth):
        retval = cls()
        retval._init_cloth(cloth, cloth_parser=etree.XMLParser())
        return retval

    @classmethod
    def from_html_cloth(cls, cloth):
        retval = cls()
        retval._init_cloth(cloth, cloth_parser=html.HTMLParser())
        return retval

    def _parse_file(self, file_name, cloth_parser):
        cloth = etree.parse(file_name, parser=cloth_parser)
        return cloth.getroot()

    def _init_cloth(self, cloth, cloth_parser):
        """Called from XmlCloth.__init__ in order to not break the dunder init
        signature consistency"""

        self._cloth = None
        self._root_cloth = None

        self._mrpc_cloth = self._root_cloth = None
        if isinstance(cloth, string_types):
            cloth = self._parse_file(cloth, cloth_parser)

        if cloth is None:
            return

        q = "//*[@%s]" % self.ROOT_ATTR_NAME
        elts = cloth.xpath(q)
        if len(elts) > 0:
            logger_c.debug("Using %r as root cloth.", cloth)
            self._root_cloth = elts[0]
        else:
            logger_c.debug("Using %r as plain cloth.", cloth)
            self._cloth = cloth

        self._mrpc_cloth = self._pop_elt(cloth, 'mrpc_entry')

    def _pop_elt(self, elt, what):
        query = '//*[@%s="%s"]' % (self.ID_ATTR_NAME, what)
        retval = elt.xpath(query)
        if len(retval) > 1:
            raise ValueError("more than one element found for query %r" % query)

        elif len(retval) == 1:
            retval = retval[0]
            retval.iterancestors().next().remove(retval)
            return retval


class ToClothMixin(OutProtocolBase, ClothParserMixin):
    def __init__(self, app=None, mime_type=None, ignore_uncap=False,
                                       ignore_wrappers=False, polymorphic=True):
        super(ToClothMixin, self).__init__(app=app, mime_type=mime_type,
                     ignore_uncap=ignore_uncap, ignore_wrappers=ignore_wrappers)

        self.polymorphic = polymorphic

        self.rendering_handlers = cdict({
            ModelBase: self.model_base_to_cloth,
            AnyXml: self.xml_to_cloth,
            Any: self.any_to_cloth,
            AnyHtml: self.html_to_cloth,
            AnyUri: self.anyuri_to_cloth,
            ComplexModelBase: self.complex_to_cloth,
        })

    def _get_elts(self, elt, tag_id=None):
        if tag_id is None:
            return elt.xpath('.//*[@%s]' % self.ID_ATTR_NAME)
        return elt.xpath('.//*[@%s="%s"]' % (self.ID_ATTR_NAME, tag_id))

    def _get_outmost_elts(self, tmpl, tag_id=None):
        ids = set()

        # we assume xpath() returns elements in top to bottom (or outside to
        # inside) order.
        for elt in self._get_elts(tmpl, tag_id):
            if elt is tmpl:  # FIXME: kill this
                logger_c.debug("Don't send myself")
                continue  # don't send myself

            if len(set((id(e) for e in elt.iterancestors())) & ids) > 0:
                logger_c.debug("Don't send grandchildren")
                continue  # don't send grandchildren

            if id(elt) in ids:  # FIXME: this check should be safe to remove
                logger_c.debug("Don't send what's already sent")
                continue  # don't send what's already sent

            ids.add(id(elt))
            yield elt

    def _get_clean_elt(self, elt, what):
        query = '//*[@%s="%s"]' % (self.ID_ATTR_NAME, what)
        retval = elt.xpath(query)
        if len(retval) > 1:
            raise ValueError("more than one element found for query %r" % query)

        elif len(retval) == 1:
            retval = retval[0]
            del retval.attrib[self.ID_ATTR_NAME]
            return retval

    def _get_elts_by_id(self, elt, what):
        retval = elt.xpath('//*[@id="%s"]' % what)
        logger_c.debug("id=%r got %r", what, retval)
        return retval

    @staticmethod
    def _methods(cls, inst):
        while cls.Attributes._wrapper and len(cls._type_info) > 0:
            cls, = cls._type_info.values()

        if cls.Attributes.methods is not None:
            for k, v in cls.Attributes.methods.items():
                is_shown = True
                if v.when is not None:
                    is_shown = v.when(inst)

                if is_shown:
                    yield k, v

    def _actions_to_cloth(self, ctx, cls, inst, template):
        if self._mrpc_cloth is None:
            logger_c.warning("missing 'mrpc_template'")
            return

        for elt in self._get_elts(template, "mrpc"):
            for k, v in self._methods(cls, inst):
                href = v.in_message.get_type_name()
                text = v.translate(ctx.locale, v.in_message.get_type_name())

                mrpc_template = deepcopy(self._mrpc_cloth)
                anchor = self._get_clean_elt(mrpc_template, 'mrpc_link')
                anchor.attrib['href'] = href

                text_elt = self._get_clean_elt(mrpc_template, 'mrpc_text')
                if text_elt is not None:
                    text_elt.text = text
                else:
                    anchor.text = text

                elt.append(mrpc_template)
                                           # mutable default ok because readonly
    def _enter_cloth(self, ctx, cloth, parent, attrs={}, skip=False):
        """There is no _exit_cloth because exiting from tags is done
        automatically with subsequent calls to _enter_cloth and finally to
        _close_cloth."""

        logger_c.debug("entering %s %r nsmap=%r attrs=%r skip=%s",
                              cloth.tag, cloth.attrib, cloth.nsmap, attrs, skip)

        if not ctx.protocol.doctype_written:
            self.write_doctype(ctx, parent, cloth)

        tags = ctx.protocol.tags
        rootstack = ctx.protocol.rootstack
        assert isinstance(rootstack, oset)

        eltstack = ctx.protocol.eltstack
        ctxstack = ctx.protocol.ctxstack

        cureltstack = eltstack[rootstack.back]
        curctxstack = ctxstack[rootstack.back]

        cloth_root = cloth.getroottree().getroot()
        if not cloth_root in rootstack:
            rootstack.add(cloth_root)
            cureltstack = eltstack[rootstack.back]
            curctxstack = ctxstack[rootstack.back]

            assert rootstack.back == cloth_root

        while rootstack.back != cloth_root:
            self._close_cloth(ctx, parent)

        last_elt = None
        if len(cureltstack) > 0:
            last_elt = cureltstack[-1]

        ancestors = _revancestors(cloth)

        # move up in tag stack until the ancestors of both
        # source and target tags match
        while ancestors[:len(cureltstack)] != cureltstack:
            elt = cureltstack.pop()
            elt_ctx = curctxstack.pop()

            last_elt = elt
            if elt_ctx is not None:
                self.event_manager.fire_event(("before_exit", elt), ctx, parent)
                elt_ctx.__exit__(None, None, None)
                logger_c.debug("\texit norm %s %s", elt.tag, elt.attrib)
                if elt.tail is not None:
                    parent.write(elt.tail)

            # unless we're at the same level as the relevant ancestor of the
            # target node
            if ancestors[:len(cureltstack)] != cureltstack:
                # write following siblings before closing parent node
                for sibl in elt.itersiblings(preceding=False):
                    logger_c.debug("\twrite exit sibl %s %r %d",
                                                sibl.tag, sibl.attrib, id(sibl))
                    parent.write(sibl)

        # write remaining ancestors of the target node.
        for anc in ancestors[len(cureltstack):]:
            # write previous siblings of ancestors (if any)
            prevsibls = _prevsibls(anc, since=last_elt)
            for elt in prevsibls:
                if id(elt) in tags:
                    logger_c.debug("\tskip  anc prevsibl %s %r",
                                                            elt.tag, elt.attrib)
                    continue
                logger_c.debug("\twrite anc prevsibl %s %r 0x%x",
                                                   elt.tag, elt.attrib, id(elt))
                parent.write(elt)

            # enter the ancestor node
            if len(cureltstack) == 0:
                # if this is the first node ever, initialize namespaces as well
                anc_ctx = parent.element(anc.tag, anc.attrib, nsmap=anc.nsmap)
            else:
                anc_ctx = parent.element(anc.tag, anc.attrib)
            anc_ctx.__enter__()
            logger_c.debug("\tenter norm %s %r 0x%x", anc.tag,
                                                            anc.attrib, id(anc))
            if anc.text is not None:
                parent.write(anc.text)

            rootstack.add(anc.getroottree().getroot())
            cureltstack = eltstack[rootstack.back]
            curctxstack = ctxstack[rootstack.back]
            cureltstack.append(anc)
            curctxstack.append(anc_ctx)

        # now that at the same level as the target node,
        # write its previous siblings
        prevsibls = _prevsibls(cloth, since=last_elt)
        for elt in prevsibls:
            if elt is last_elt:
                continue
            if id(elt) in tags:
                logger_c.debug("\tskip  cloth prevsibl %s %r",elt.tag, elt.attrib)
                continue
            logger_c.debug("\twrite cloth prevsibl %s %r", elt.tag, elt.attrib)
            parent.write(elt)

        skip = skip or (cloth.tag == self.DATA_TAG_NAME)

        if skip:
            tags.add(id(cloth))
            curtag = None

        else:
            # finally, enter the target node.
            attrib = dict([(k, v) for k, v in cloth.attrib.items()
                        if not (k in (self.ID_ATTR_NAME, self.ROOT_ATTR_NAME))])

            attrib.update(attrs)

            self.event_manager.fire_event(("before_entry", cloth), ctx,
                                                                 parent, attrib)

            if len(cureltstack) == 0:
                curtag = parent.element(cloth.tag, attrib, nsmap=cloth.nsmap)
            else:
                curtag = parent.element(cloth.tag, attrib)
            curtag.__enter__()
            if cloth.text is not None:
                parent.write(cloth.text)

        rootstack.add(cloth.getroottree().getroot())
        cureltstack = eltstack[rootstack.back]
        curctxstack = ctxstack[rootstack.back]

        cureltstack.append(cloth)
        curctxstack.append(curtag)

        logger_c.debug("")

    def _close_cloth(self, ctx, parent):
        rootstack = ctx.protocol.rootstack
        cureltstack = ctx.protocol.eltstack[rootstack.back]
        curctxstack = ctx.protocol.ctxstack[rootstack.back]

        for elt, elt_ctx in reversed(tuple(zip(cureltstack, curctxstack))):
            cu = ctx.protocol[self].close_until
            if elt is cu:
                logger_c.debug("closed until %r, breaking out", cu)
                ctx.protocol[self].close_cloth = None
                break

            if elt_ctx is not None:
                self.event_manager.fire_event(("before_exit", elt), ctx, parent)
                elt_ctx.__exit__(None, None, None)
                logger_c.debug("exit %s close", elt.tag)
                if elt.tail is not None:
                    parent.write(elt.tail)

            for sibl in elt.itersiblings(preceding=False):
                logger_c.debug("write %s nextsibl", sibl.tag)
                parent.write(sibl)
                if sibl.tail is not None:
                    parent.write(sibl.tail)

        rootstack.pop()

    @coroutine
    def to_parent_cloth(self, ctx, cls, inst, cloth, parent, name,
                                                      from_arr=False, **kwargs):
        if len(ctx.protocol.eltstack) > 0:
            ctx.protocol[self].close_until = ctx.protocol.eltstack[-1]

        cls_cloth = self.get_class_cloth(cls)
        if cls_cloth is not None:
            logger_c.debug("%r to object cloth", cls)
            cloth = cls_cloth

        ret = self.to_cloth(ctx, cls, inst, cloth, parent, '')
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
                    self._close_cloth(ctx, parent)
        else:
            self._close_cloth(ctx, parent)

    @coroutine
    def to_root_cloth(self, ctx, cls, inst, cloth, parent, name):
        if len(ctx.protocol.eltstack) > 0:
            ctx.protocol[self].close_until = ctx.protocol.eltstack[-1]

        self._enter_cloth(ctx, cloth, parent)

        ret = self.start_to_parent(ctx, cls, inst, parent, name)
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
                    self._close_cloth(ctx, parent)
        else:
            self._close_cloth(ctx, parent)

    # TODO: Maybe DRY this with to_parent?
    def to_cloth(self, ctx, cls, inst, cloth, parent, name=None, from_arr=False,
                                                                      **kwargs):
        prot_name = self.__class__.__name__

        if cloth is None:
            return self.to_parent(ctx, cls, inst, parent, name, **kwargs)

        cls, switched = self.get_polymorphic_target(cls, inst)

        # if there's a subprotocol, switch to it
        subprot = getattr(cls.Attributes, 'prot', None)
        if subprot is not None and not (subprot is self):
            self._enter_cloth(ctx, cloth, parent)
            return subprot.subserialize(ctx, cls, inst, parent, name, **kwargs)

        # if instance is None, use the default factory to generate one
        _df = cls.Attributes.default_factory
        if inst is None and callable(_df):
            inst = _df()

        # if instance is still None, use the default value
        if inst is None:
            inst = cls.Attributes.default

        retval = None
        if inst is None:
            identifier = "%s.%s" % (prot_name, "null_to_cloth")
            logger_s.debug("Writing %s using %s for %s.", name,
                                                identifier, cls.get_type_name())

            ctx.protocol.tags.add(id(cloth))
            if cls.Attributes.min_occurs > 0:
                parent.write(cloth)

        else:
            if not from_arr and cls.Attributes.max_occurs > 1:
                return self.array_to_cloth(ctx, cls, inst, cloth, parent,
                                                                      name=name)

            handler = self.rendering_handlers[cls]

            identifier = "%s.%s" % (prot_name, handler.__name__)
            logger_s.debug("Writing %s using %s for %s. Inst: %r", name,
                                       identifier, cls.get_type_name(),
                                       log_repr(inst, cls, from_array=from_arr))

            retval = handler(ctx, cls, inst, cloth, parent, name=name)

        return retval

    def model_base_to_cloth(self, ctx, cls, inst, cloth, parent, name):
        self._enter_cloth(ctx, cloth, parent)
        parent.write(self.to_unicode(cls, inst))

    def xml_to_cloth(self, ctx, cls, inst, cloth, parent, name):
        self._enter_cloth(ctx, cloth, parent)
        if isinstance(inst, string_types):
            inst = etree.fromstring(inst)
        parent.write(inst)

    def any_to_cloth(self, ctx, cls, inst, cloth, parent, name):
        self._enter_cloth(ctx, cloth, parent)
        parent.write(inst)

    def html_to_cloth(self, ctx, cls, inst, cloth, parent, name):
        self._enter_cloth(ctx, cloth, parent)
        if isinstance(inst, string_types):
            inst = html.fromstring(inst)
        parent.write(inst)

    def anyuri_to_cloth(self, ctx, cls, inst, cloth, parent, name, **kwargs):
        self._enter_cloth(ctx, cloth, parent)
        self.anyuri_to_parent(ctx, cls, inst, parent, name, **kwargs)

    @coroutine
    def complex_to_cloth(self, ctx, cls, inst, cloth, parent, name=None,
                                                                      **kwargs):
        fti = cls.get_flat_type_info(cls)

        attrs = {}
        for k, v in fti.items():
            if not issubclass(v, XmlAttribute):
                continue

            ns = v._ns
            if ns is None:
                ns = v.Attributes.sub_ns

            val = getattr(inst, k, None)
            k = _gen_tagname(ns, k)

            if val is not None:
                if issubclass(v.type, (ByteArray, File)):
                    attrs[k] = self.to_unicode(v.type, val, self.binary_encoding)
                else:
                    attrs[k] = self.to_unicode(v.type, val)

        self._enter_cloth(ctx, cloth, parent, attrs=attrs)

        for elt in self._get_elts(cloth, "mrpc"):
            self._actions_to_cloth(ctx, cls, inst, elt)

        for i, elt in enumerate(self._get_outmost_elts(cloth)):
            k = elt.attrib[self.ID_ATTR_NAME]
            v = fti.get(k, None)

            if v is None:
                logger_c.warning("elt id %r not in %r", k, cls)
                self._enter_cloth(ctx, elt, parent, skip=True)
                continue

            if issubclass(v, XmlData):
                v = v.type

            if issubclass(cls, Array):
                # if cls is an array, inst should already be a sequence type
                # (eg list), so there's no point in doing a getattr -- we will
                # unwrap it and serialize it in the next round of to_cloth call.
                val = inst
            else:
                val = getattr(inst, k, None)

            ret = self.to_cloth(ctx, v, val, elt, parent, name=k, **kwargs)
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
    def array_to_cloth(self, ctx, cls, inst, cloth, parent, name=None, **kwargs):
        if isinstance(inst, PushBase):
            while True:
                sv = (yield)
                ret = self.to_cloth(ctx, cls, sv, cloth, parent,
                                             name=name, from_arr=True, **kwargs)
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
                ret = self.to_cloth(ctx, cls, sv, cloth, parent,
                                             from_arr=True, name=name, **kwargs)
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
