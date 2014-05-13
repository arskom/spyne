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

from collections import deque
from inspect import isgenerator

from spyne.util import Break, coroutine
from spyne.model import Array, AnyXml, AnyHtml, ModelBase, ComplexModelBase, \
    PushBase
from spyne.protocol import ProtocolBase
from spyne.util.cdict import cdict


_prevsibs = lambda elt: list(elt.itersiblings(preceding=True))
_ancestors = lambda elt: list(elt.iterancestors())


class ToClothMixin(ProtocolBase):
    def __init__(self, app=None, validator=None, mime_type=None,
                                     ignore_uncap=False, ignore_wrappers=False):
        super(ToClothMixin, self).__init__(app=app, validator=validator,
                                 mime_type=mime_type, ignore_uncap=ignore_uncap,
                                 ignore_wrappers=ignore_wrappers)

        self.rendering_handlers = cdict({
            ModelBase: self.model_base_to_cloth,
            AnyXml: self.element_to_cloth,
            AnyHtml: self.element_to_cloth,
            ComplexModelBase: self.complex_to_cloth,
        })
        
    def _get_elts(self, elt, tag_id=None):
        if tag_id is None:
            return elt.xpath('//*[@%s]' % self.attr_name)
        return elt.xpath('//*[@%s="%s"]' % (self.attr_name, tag_id))

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
        print "id=%r" % what, "got",
        retval = elt.xpath('//*[@id="%s"]' % what)
        print retval
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
                    yield k,v

    def complex_to_cloth(self, ctx, cls, inst, cloth, parent, name=None):
        for elt in self._get_elts(cloth, "mrpc"):
            self._actions_to_cloth(ctx, cls, inst, elt)

        fti = cls.get_flat_type_info(cls)
        for i, elt in enumerate(self._get_outmost_elts(cloth)):
            k = elt.attrib[self.attr_name]
            v = fti.get(k, None)
            if v is None:
                logger.warning("elt id %r not in %r", k, cls)
                continue

            # if cls is an array, inst should already be a sequence type
            # (eg list), so there's no point in doing a getattr -- we will
            # unwrap it and serialize it in the next round of to_cloth call.
            if issubclass(cls, Array):
                val = inst
            else:
                val = getattr(inst, k, None)

            self.to_cloth(ctx, v, val, elt, parent, name=k)

    @coroutine
    def array_to_cloth(self, ctx, cls, inst, cloth, parent, name=None, **kwargs):
        if isinstance(inst, PushBase):
            while True:
                sv = (yield)
                ret = self.to_cloth(ctx, cls, sv, cloth, parent, from_arr=True, **kwargs)
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
                ret = self.to_cloth(ctx, cls, sv, cloth, parent, from_arr=True, **kwargs)
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

    def to_cloth(self, ctx, cls, inst, cloth, parent, name=None, from_arr=False, **kwargs):
        if cloth is None:
            return self.to_parent(ctx, cls, inst, parent, name, **kwargs)

        if inst is None:
            inst = cls.Attributes.default

        if inst is None:
            if cls.Attributes.min_occurs > 0:
                parent.write(cloth)

        elif not from_arr and cls.Attributes.max_occurs > 1:
            return self.array_to_cloth(ctx, cls, inst, cloth, parent, name=name)

        self._enter_cloth(ctx, cloth, parent)
        handler = self.rendering_handlers[cls]
        return handler(ctx, cls, inst, cloth, parent, name=name)

    def model_base_to_cloth(self, ctx, cls, inst, cloth, parent, name):
        print cls, inst
        parent.write(self.to_string(cls, inst))

    def element_to_cloth(self, ctx, cls, inst, cloth, parent, name):
        print cls, inst
        parent.write(inst)

    def _enter_cloth(self, ctx, cloth, parent):
        if cloth is self._cloth:
            print "return"
            return

        assert len(list(cloth.iterancestors())) > 0
        stack = ctx.protocol.stack
        tags = ctx.protocol.tags

        # exit from prev cloth write to the first ancestor
        anc = list(reversed(_ancestors(cloth)))
        while anc[:len(stack)] != list([s for s, sc in stack]):
            elt, elt_ctx = ctx.protocol.stack.pop()
            elt_ctx.__exit__(None, None, None)
            print "exit ", elt.tag, "norm"
            for sibl in elt.itersiblings():
                if sibl in anc:
                    break
                print "write", sibl.tag, "exit sibl"
                parent.write(sibl)

        print "entering", cloth.tag
        deps = deque()
        for sibl in _prevsibs(cloth):
            if id(sibl) in tags:
                break
            deps.appendleft((False, sibl))

        for elt in cloth.iterancestors():
            if elt in list([s for s, sc in stack]):
                break
            deps.appendleft((True, elt))

            for sibl in _prevsibs(elt):
                if id(sibl) in tags:
                    break

                deps.appendleft((False, sibl))

        # write parents with parent siblings
        print deps
        for new, elt in deps:
            open_elts = [id(e) for e, e_ctx in stack]
            if id(elt) in open_elts:
                print "skip ", elt
            else:
                if new:
                    curtag = parent.element(elt.tag, elt.attrib)
                    curtag.__enter__()
                    print "enter", elt.tag, "norm"
                    stack.append( (elt, curtag) )
                else:
                    parent.write(elt)
                    print "write", elt.tag, "norm"

                print "- adding", elt.tag, id(elt)
                tags.add(id(elt))

        # write the element itself
        attrib = dict([(k2, v2) for k2, v2 in cloth.attrib.items()
                           if not (k2 in (self.attr_name,self.root_attr_name))])

        curtag = parent.element(cloth.tag, attrib)
        curtag.__enter__()
        stack.append( (cloth, curtag) )
        print "entering", cloth.tag, 'ok'

    def _close_cloth(self, ctx, parent):
        for elt, elt_ctx in reversed(ctx.protocol.stack):
            print "exit ", elt.tag, "close"
            elt_ctx.__exit__(None, None, None)
            for sibl in elt.itersiblings():
                print "write", sibl.tag, "close sibl"
                parent.write(sibl)

    def to_parent_cloth(self, ctx, cls, inst, cloth, parent, name, from_arr=False, **kwargs):
        ctx.protocol.stack = deque()
        ctx.protocol.tags = set()

        self.to_cloth(ctx, cls, inst, cloth, parent)
        self._close_cloth(ctx, parent)

    @coroutine
    def to_root_cloth(self, ctx, cls, inst, cloth, parent, name=None):
        ctx.protocol.stack = deque()
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
                    self._close_cloth(ctx, parent)
