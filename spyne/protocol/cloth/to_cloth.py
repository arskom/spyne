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

from lxml import html, etree
from copy import deepcopy
from inspect import isgenerator

from spyne.util import Break, coroutine
from spyne.util.six import string_types
from spyne.model import Array, AnyXml, AnyHtml, ModelBase, ComplexModelBase, \
    PushBase, XmlAttribute, File, ByteArray
from spyne.protocol import ProtocolBase
from spyne.util.cdict import cdict


_prevsibls = lambda elt: list(elt.itersiblings(preceding=True))
_revancestors = lambda elt: list(reversed(list(elt.iterancestors())))


def _gen_tagname(ns, name):
    if ns is not None:
        name = "{%s}%s" % (ns, name)
    return name


class ToClothMixin(ProtocolBase):
    def __init__(self, app=None, validator=None, mime_type=None,
                 ignore_uncap=False, ignore_wrappers=False, polymorphic=True):
        super(ToClothMixin, self).__init__(app=app, validator=validator,
                                 mime_type=mime_type, ignore_uncap=ignore_uncap,
                                                ignore_wrappers=ignore_wrappers)

        self.polymorphic = polymorphic

        self.rendering_handlers = cdict({
            ModelBase: self.model_base_to_cloth,
            AnyXml: self.xml_to_cloth,
            AnyHtml: self.html_to_cloth,
            ComplexModelBase: self.complex_to_cloth,
        })

    def _init_cloth(self, cloth, attr_name, root_attr_name, cloth_parser):
        """Called from XmlCloth.__init__ in order to not break the dunder init
        signature consistency"""

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
            logger.debug("Using cloth as root.")
            q = "//*[@%s]" % self.root_attr_name
            elts = self._cloth.xpath(q)
            if len(elts) > 0:
                self._root_cloth = elts[0]

        if self._cloth is not None:
            self._mrpc_cloth = self._pop_elt(self._cloth, 'mrpc_entry')

    def _get_elts(self, elt, tag_id=None):
        if tag_id is None:
            return elt.xpath('.//*[@%s]' % self.attr_name)
        return elt.xpath('.//*[@%s="%s"]' % (self.attr_name, tag_id))

    def _get_outmost_elts(self, tmpl, tag_id=None):
        ids = set()

        # we assume xpath() returns elements in top to bottom (or outside to
        # inside) order.
        for elt in self._get_elts(tmpl, tag_id):
            if elt is tmpl:
                continue
            if len(set((id(e) for e in elt.iterancestors())) & ids):
                continue
            if not id(elt) in ids:
                ids.add(id(elt))
                yield elt

    def _pop_elt(self, elt, what):
        query = '//*[@%s="%s"]' % (self.attr_name, what)
        retval = elt.xpath(query)
        if len(retval) > 1:
            raise ValueError("more than one element found for query %r" % query)

        elif len(retval) == 1:
            retval = retval[0]
            retval.iterancestors().next().remove(retval)
            return retval

    def _get_clean_elt(self, elt, what):
        query = '//*[@%s="%s"]' % (self.attr_name, what)
        retval = elt.xpath(query)
        if len(retval) > 1:
            raise ValueError("more than one element found for query %r" % query)

        elif len(retval) == 1:
            retval = retval[0]
            del retval.attrib[self.attr_name]
            return retval

    def _get_elts_by_id(self, elt, what):
        print("id=%r" % what, "got", end='')
        retval = elt.xpath('//*[@id="%s"]' % what)
        print(retval)
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
            logger.warning("missing 'mrpc_template'")
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

        print("entering", cloth.tag, cloth.attrib, cloth.nsmap, "skip=%s" % skip)

        tags = ctx.protocol.tags
        eltstack = ctx.protocol.eltstack
        ctxstack = ctx.protocol.ctxstack
        ancestors = _revancestors(cloth)

        last_elt = None
        if len(eltstack) > 0:
            last_elt = eltstack[-1]

        # move up in tag stack until the ancestors of both
        # source and target are the same
        while ancestors[:len(eltstack)] != eltstack:
            elt = eltstack.pop()
            elt_ctx = ctxstack.pop()

            last_elt = elt
            if elt_ctx is not None:
                elt_ctx.__exit__(None, None, None)
                print("\texit norm", elt.tag, elt.attrib)

            # unless we're at the same level as the relevant ancestor of the
            # target node
            if ancestors[:len(eltstack)] != eltstack:
                # write following siblings before closing parent node
                for sibl in elt.itersiblings(preceding=False):
                    print("\twrite exit sibl", sibl.tag, sibl.attrib)
                    parent.write(sibl)

        # write remaining ancestors of the target node.
        for anc in ancestors[len(eltstack):]:
            # write previous siblins of ancestors (if any)
            prevsibls = _prevsibls(anc)
            for elt in prevsibls:
                if elt is last_elt:
                    break
                if id(elt) in tags:
                    print("\skip  anc prevsibl", elt.tag, elt.attrib)
                    continue
                print("\twrite anc prevsibl", elt.tag, elt.attrib)
                parent.write(elt)

            # enter the ancestor node
            if len(eltstack) == 0:
                anc_ctx = parent.element(anc.tag, anc.attrib, nsmap=anc.nsmap)
            else:
                anc_ctx = parent.element(anc.tag, anc.attrib)
            anc_ctx.__enter__()
            print("\tenter norm", anc.tag, anc.attrib)
            eltstack.append(anc)
            ctxstack.append(anc_ctx)

        # now that at the same level as the target node,
        # write its previous siblings
        if not last_elt is cloth:
            prevsibls = _prevsibls(cloth)
            for elt in prevsibls:
                if elt is last_elt:
                    break
                if id(elt) in tags:
                    print("\tskip  cloth prevsibl", elt.tag, elt.attrib)
                    continue
                print("\twrite cloth prevsibl", elt.tag, elt.attrib)
                parent.write(elt)

        if skip:
            tags.add(id(cloth))
            curtag = None

        else:
            # finally, enter the target node.
            attrib = dict([(k, v) for k, v in cloth.attrib.items()
                           if not (k in (self.attr_name, self.root_attr_name))])

            attrib.update(attrs)
            if len(eltstack) == 0:
                curtag = parent.element(cloth.tag, attrib, nsmap=cloth.nsmap)
            else:
                curtag = parent.element(cloth.tag, attrib)
            curtag.__enter__()

        eltstack.append(cloth)
        ctxstack.append(curtag)

        print()

    def _close_cloth(self, ctx, parent):
        for elt, elt_ctx in reversed(zip(ctx.protocol.eltstack,
                                                        ctx.protocol.ctxstack)):
            if elt_ctx is not None:
                elt_ctx.__exit__(None, None, None)
                print("exit ", elt.tag, "close")

            for sibl in elt.itersiblings(preceding=False):
                print("write", sibl.tag, "close sibl")
                parent.write(sibl)

    def to_parent_cloth(self, ctx, cls, inst, cloth, parent, name,
                        from_arr=False, **kwargs):
        ctx.protocol.eltstack = []
        ctx.protocol.ctxstack = []
        ctx.protocol.tags = set()

        self.to_cloth(ctx, cls, inst, cloth, parent)
        self._close_cloth(ctx, parent)

    @coroutine
    def to_root_cloth(self, ctx, cls, inst, cloth, parent, name=None):
        ctx.protocol.eltstack = []
        ctx.protocol.ctxstack = []
        ctx.protocol.tags = set()

        self._enter_cloth(ctx, cloth, parent)

        ret = self.to_parent(ctx, cls, inst, parent, name)
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

    def to_cloth(self, ctx, cls, inst, cloth, parent, name=None, from_arr=False,
                                                                      **kwargs):

        if cloth is None:
            return self.to_parent(ctx, cls, inst, parent, name, **kwargs)

        if self.polymorphic and issubclass(inst.__class__, cls.__orig__ or cls):
            cls = inst.__class__

        if inst is None:
            inst = cls.Attributes.default

        subprot = getattr(cls.Attributes, 'prot', None)
        if subprot is not None and not (subprot is self):
            self._enter_cloth(ctx, cloth, parent)
            return subprot.subserialize(ctx, cls, inst, parent, name, **kwargs)

        retval = None
        if inst is None:
            ctx.protocol.tags.add(id(cloth))
            if cls.Attributes.min_occurs > 0:
                parent.write(cloth)

        else:
            if not from_arr and cls.Attributes.max_occurs > 1:
                return self.array_to_cloth(ctx, cls, inst, cloth, parent, name=name)

            handler = self.rendering_handlers[cls]
            retval = handler(ctx, cls, inst, cloth, parent, name=name)

        return retval

    def model_base_to_cloth(self, ctx, cls, inst, cloth, parent, name):
        self._enter_cloth(ctx, cloth, parent)
        parent.write(self.to_string(cls, inst))

    def xml_to_cloth(self, ctx, cls, inst, cloth, parent, name):
        self._enter_cloth(ctx, cloth, parent)
        if isinstance(inst, string_types):
            inst = etree.fromstring(inst)
        parent.write(inst)

    def html_to_cloth(self, ctx, cls, inst, cloth, parent, name):
        self._enter_cloth(ctx, cloth, parent)
        if isinstance(inst, string_types):
            inst = html.fromstring(inst)
        parent.write(inst)

    @coroutine
    def complex_to_cloth(self, ctx, cls, inst, cloth, parent, name=None):
        fti = cls.get_flat_type_info(cls)

        attrs = {}
        for k, v in fti.items():
            if issubclass(v, XmlAttribute):
                ns = v._ns
                if ns is None:
                    ns = v.Attributes.sub_ns

                k = _gen_tagname(ns, k)
                val = getattr(inst, k, None)

                if val is not None:
                    if issubclass(v.type, (ByteArray, File)):
                        attrs[k] = self.to_string(v.type, val,
                                                           self.binary_encoding)
                    else:
                        attrs[k] = self.to_string(v.type, val)

        self._enter_cloth(ctx, cloth, parent, attrs=attrs)

        for elt in self._get_elts(cloth, "mrpc"):
            self._actions_to_cloth(ctx, cls, inst, elt)

        for i, elt in enumerate(self._get_outmost_elts(cloth)):
            k = elt.attrib[self.attr_name]
            v = fti.get(k, None)

            if v is None:
                logger.warning("elt id %r not in %r", k, cls)
                self._enter_cloth(ctx, elt, parent, skip=True)
                continue

            if issubclass(cls, Array):
                # if cls is an array, inst should already be a sequence type
                # (eg list), so there's no point in doing a getattr -- we will
                # unwrap it and serialize it in the next round of to_cloth call.
                val = inst
            else:
                val = getattr(inst, k, None)

            ret = self.to_cloth(ctx, v, val, elt, parent, name=k)
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
                ret = self.to_cloth(ctx, cls, sv, cloth, parent, from_arr=True,
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
                ret = self.to_cloth(ctx, cls, sv, cloth, parent, from_arr=True,
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
