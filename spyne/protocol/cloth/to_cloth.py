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
logger_c = logging.getLogger("%s.cloth" % __name__)
logger_s = logging.getLogger("%s.serializer" % __name__)

from lxml import html, etree
from copy import deepcopy
from inspect import isgenerator

from spyne.util import Break, coroutine
from spyne.util.oset import oset
from spyne.util.six import string_types
from spyne.util.color import R, B
from spyne.model import Array, AnyXml, AnyHtml, ModelBase, ComplexModelBase, \
    PushBase, XmlAttribute, AnyUri, XmlData, Any

from spyne.protocol import OutProtocolBase
from spyne.util.cdict import cdict

_revancestors = lambda elt: list(reversed(tuple(elt.iterancestors())))

_NODATA = type("_NODATA", (object,), {})


def _prevsibls(elt, strip_comments, since=None):
    return reversed(list(_prevsibls_since(elt, strip_comments, since)))


def _prevsibls_since(elt, strip_comments, since):
    if since is elt:
        return

    for prevsibl in elt.itersiblings(preceding=True):
        if prevsibl is since:
            break

        if strip_comments and isinstance(elt, etree.CommentBase):
            if elt.text.startswith('[if ') and elt.text.endswith('[endif]'):
                pass
            else:
                continue

        yield prevsibl


def _set_identifier_prefix(obj, prefix, mrpc_id='mrpc', id_attr='id',
                            data_tag='data', data_attr='data', attr_attr='attr',
                                        root_attr='root', tagbag_attr='tagbag'):
    obj.ID_PREFIX = prefix

    obj.MRPC_ID = '{}{}'.format(prefix, mrpc_id)
    obj.ID_ATTR_NAME = '{}{}'.format(prefix, id_attr)
    obj.DATA_TAG_NAME = '{}{}'.format(prefix, data_tag)
    obj.DATA_ATTR_NAME = '{}{}'.format(prefix, data_attr)
    obj.ATTR_ATTR_NAME = '{}{}'.format(prefix, attr_attr)
    obj.ROOT_ATTR_NAME = '{}{}'.format(prefix, root_attr)
    obj.TAGBAG_ATTR_NAME = '{}{}'.format(prefix, tagbag_attr)
    # FIXME: get rid of this. We don't want logic creep inside cloths
    obj.WRITE_CONTENTS_WHEN_NOT_NONE = '{}write-contents'.format(prefix)

    obj.SPYNE_ATTRS = {
        obj.ID_ATTR_NAME,
        obj.DATA_ATTR_NAME,
        obj.ATTR_ATTR_NAME,
        obj.ROOT_ATTR_NAME,
        obj.TAGBAG_ATTR_NAME,
        obj.WRITE_CONTENTS_WHEN_NOT_NONE,
    }


class ClothParserMixin(object):
    ID_PREFIX = 'spyne-'

    # these are here for documentation purposes. The are all reinitialized with
    # the call ta _set_identifier_prefix below the class definition
    ID_ATTR_NAME = 'spyne-id'
    DATA_TAG_NAME = 'spyne-data'
    DATA_ATTR_NAME = 'spyne-data'
    ATTR_ATTR_NAME = 'spyne-attr'
    ROOT_ATTR_NAME = 'spyne-root'
    TAGBAG_ATTR_NAME = 'spyne-tagbag'
    WRITE_CONTENTS_WHEN_NOT_NONE = 'spyne-write-contents'

    def set_identifier_prefix(self, what):
        _set_identifier_prefix(self, what)
        return self

    @classmethod
    def from_xml_cloth(cls, cloth, strip_comments=True):
        retval = cls()
        retval._init_cloth(cloth, cloth_parser=etree.XMLParser(),
                                                  strip_comments=strip_comments)
        return retval

    @classmethod
    def from_html_cloth(cls, cloth, strip_comments=True):
        retval = cls()
        retval._init_cloth(cloth, cloth_parser=html.HTMLParser(),
                                                  strip_comments=strip_comments)
        return retval

    @staticmethod
    def _strip_comments(root):
        for elt in root.iter():
            if isinstance(elt, etree.CommentBase):
                if elt.getparent() is not None:
                    if elt.text.startswith('[if ') \
                                               and elt.text.endswith('[endif]'):
                        pass
                    else:
                        elt.getparent().remove(elt)

    def _parse_file(self, file_name, cloth_parser):
        cloth = etree.parse(file_name, parser=cloth_parser)
        return cloth.getroot()

    def _init_cloth(self, cloth, cloth_parser, strip_comments):
        """Called from XmlCloth.__init__ in order to not break the dunder init
        signature consistency"""

        self._cloth = None
        self._root_cloth = None
        self.strip_comments = strip_comments

        self._mrpc_cloth = self._root_cloth = None

        if cloth is None:
            return

        if isinstance(cloth, string_types):
            cloth = self._parse_file(cloth, cloth_parser)

        if strip_comments:
            self._strip_comments(cloth)

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
            next(retval.iterancestors()).remove(retval)
            return retval


_set_identifier_prefix(ClothParserMixin, ClothParserMixin.ID_PREFIX)


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
            AnyUri: self.any_uri_to_cloth,
            ComplexModelBase: self.complex_to_cloth,
        })

    def _get_elts(self, elt, tag_id=None):
        if tag_id is None:
            return elt.xpath('.//*[@*[starts-with(name(), "%s")]]' %
                                                                 self.ID_PREFIX)
        return elt.xpath('.//*[@*[starts-with(name(), "%s")]="%s"]' % (
                                                        self.ID_PREFIX, tag_id))

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
                logger_c.debug("Don't send what's already been sent")
                continue  # don't send what's already been sent

            if self.ID_ATTR_NAME in elt.attrib:
                # Prevent primitive attrs like spyne-attr from interfering
                # with elt descent
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

    def _is_tagbag(self, elt):
        return self.TAGBAG_ATTR_NAME in elt.attrib

    @staticmethod
    def _methods(ctx, cls, inst):
        while cls.Attributes._wrapper and len(cls._type_info) > 0:
            cls, = cls._type_info.values()

        if cls.Attributes.methods is not None:
            for k, v in cls.Attributes.methods.items():
                is_shown = True
                if v.when is not None:
                    is_shown = v.when(inst, ctx)

                if is_shown:
                    yield k, v

    def _actions_to_cloth(self, ctx, cls, inst, template):
        if self._mrpc_cloth is None:
            logger_c.warning("missing 'mrpc_template'")
            return

        for elt in self._get_elts(template, self.MRPC_ID):
            for k, v in self._methods(ctx, cls, inst):
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
    def _enter_cloth(self, ctx, cloth, parent, attrib={}, skip=False,
                                                  method=None, skip_dupe=False):
        """Enters the given tag in the document by using the shortest path from
        current tag.

        1. Moves up the tree by writing all tags so that the set of ancestors
           of the current tag are a subset of the ancestors of the parent tag
        2. Writes all tags until hitting a direct ancestor, enters it, and
           keeps writing previous siblings of ancestor tags and entering
           ancestor tags until hitting the target tag.
        3. Enters the target tag and returns

        There is no _exit_cloth because exiting from tags is done
        automatically with subsequent calls to _enter_cloth and finally to
        _close_cloth.

        :param ctx: A MethodContext instance
        :param cloth: The target cloth -- an ``lxml.etree._Element`` instance.
        :param parent: The target stream -- typically an
            ``lxml.etree._IncrementalFileWriter`` instance.
        :param attrib: A dict of additional attributes for the target cloth.
        :param skip: When True, the target tag is actually not entered.
            Typically used for XmlData and friends.
        :param method: One of ``(None, 'html', 'xml')``. When not ``None``,
            overrides the output method of lxml.
        :param skip_dupe: When ``False`` (the default) if this function is
            called repeatedly for the same tag, the tag is exited and reentered.
            This typically happens for types with ``max_occurs`` > 1
            (eg. arrays).
        """

        logger_c.debug("entering %s %r nsmap=%r attrib=%r skip=%s method=%s",
                     cloth.tag, cloth.attrib, cloth.nsmap, attrib, skip, method)

        if not ctx.outprot_ctx.doctype_written:
            self.write_doctype(ctx, parent, cloth)

        tags = ctx.protocol.tags
        rootstack = ctx.protocol.rootstack
        assert isinstance(rootstack, oset)

        eltstack = ctx.protocol.eltstack
        ctxstack = ctx.protocol.ctxstack

        cureltstack = eltstack[rootstack.back]
        curctxstack = ctxstack[rootstack.back]

        if skip_dupe and len(cureltstack) > 0 and cureltstack[-1] is cloth:
            return

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
            prevsibls = _prevsibls(anc, self.strip_comments, since=last_elt)
            for elt in prevsibls:
                if id(elt) in tags:
                    logger_c.debug("\tskip  anc prevsibl %s %r",
                                                            elt.tag, elt.attrib)
                    continue

                logger_c.debug("\twrite anc prevsibl %s %r 0x%x",
                                                   elt.tag, elt.attrib, id(elt))
                parent.write(elt)

            # enter the ancestor node
            kwargs = {}
            if len(cureltstack) == 0:
                # if this is the first node ever, initialize namespaces as well
                kwargs['nsmap'] = anc.nsmap

            anc_ctx = parent.element(anc.tag, anc.attrib, **kwargs)
            anc_ctx.__enter__()
            logger_c.debug("\tenter norm %s %r 0x%x method: %r", anc.tag,
                                                    anc.attrib, id(anc), method)
            if anc.text is not None:
                parent.write(anc.text)

            rootstack.add(anc.getroottree().getroot())
            cureltstack = eltstack[rootstack.back]
            curctxstack = ctxstack[rootstack.back]
            cureltstack.append(anc)
            curctxstack.append(anc_ctx)

        # now that at the same level as the target node,
        # write its previous siblings
        prevsibls = _prevsibls(cloth, self.strip_comments, since=last_elt)
        for elt in prevsibls:
            if elt is last_elt:
                continue

            if id(elt) in tags:
                logger_c.debug("\tskip  cloth prevsibl %s %r",
                                                            elt.tag, elt.attrib)
                continue

            logger_c.debug("\twrite cloth prevsibl %s %r", elt.tag, elt.attrib)
            parent.write(elt)

        skip = skip or (cloth.tag == self.DATA_TAG_NAME)

        if skip:
            tags.add(id(cloth))
            if method is not None:
                curtag = parent.method(method)
                curtag.__enter__()
            else:
                curtag = None

        else:
            # finally, enter the target node.
            cloth_attrib = dict([(k, v) for k, v in cloth.attrib.items()
                                                  if not k in self.SPYNE_ATTRS])

            cloth_attrib.update(attrib)

            self.event_manager.fire_event(("before_entry", cloth), ctx,
                                                           parent, cloth_attrib)

            kwargs = {}
            if len(cureltstack) == 0:
                # if this is the first node ever, initialize namespaces as well
                kwargs['nsmap'] = cloth.nsmap
            if method is not None:
                kwargs['method'] = method
            curtag = parent.element(cloth.tag, cloth_attrib, **kwargs)
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
        close_until = rootstack.back
        cureltstack = ctx.protocol.eltstack[close_until]
        curctxstack = ctx.protocol.ctxstack[close_until]

        for elt, elt_ctx in reversed(tuple(zip(cureltstack, curctxstack))):
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

            if elt is close_until:
                logger_c.debug("closed until %r, breaking out", close_until)
                break

        del ctx.protocol.eltstack[close_until]
        del ctx.protocol.ctxstack[close_until]

        if len(rootstack) > 0:
            rootstack.pop()

    @coroutine
    def to_parent_cloth(self, ctx, cls, inst, cloth, parent, name,
                                                      from_arr=False, **kwargs):
        cls_cloth = self.get_class_cloth(cls)
        if cls_cloth is not None:
            logger_c.debug("%r to object cloth", cls)
            cloth = cls_cloth
            ctx.protocol[self].rootstack.add(cloth)

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

    @coroutine
    def to_root_cloth(self, ctx, cls, inst, cloth, parent, name):
        if len(ctx.protocol.eltstack) > 0:
            ctx.protocol[self].rootstack.add(cloth)

        cls_attrs = self.get_cls_attrs(cls)
        self._enter_cloth(ctx, cloth, parent, method=cls_attrs.method)

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

    # TODO: Maybe DRY this with to_parent?
    @coroutine
    def to_cloth(self, ctx, cls, inst, cloth, parent, name=None,
                        from_arr=False, as_attr=False, as_data=False, **kwargs):

        prot_name = self.__class__.__name__

        if issubclass(cls, XmlAttribute):
            cls = cls.type
            as_attr = True

        elif issubclass(cls, XmlData):
            cls = cls.type
            as_data = True

        pushed = False
        if cloth is None:
            logger_c.debug("No cloth fround, switching to to_parent...")
            ret = self.to_parent(ctx, cls, inst, parent, name, **kwargs)

        else:
            cls, _ = self.get_polymorphic_target(cls, inst)
            cls_attrs = self.get_cls_attrs(cls)

            inst = self._sanitize(cls_attrs, inst)

            # if instance is None, use the default factory to generate one
            _df = cls_attrs.default_factory
            if inst is None and callable(_df):
                inst = _df()

            # if instance is still None, use the default value
            if inst is None:
                inst = cls_attrs.default

            # if there's a subprotocol, switch to it
            subprot = cls_attrs.prot
            if subprot is not None and not (subprot is self):
                # we can't do this because subprotocols don't accept cloths.
                # so we need to enter the cloth, which make it too late to
                # set attributes.
                assert not as_attr, "No subprot supported for fields " \
                    "to be serialized as attributes, use type casting with "  \
                    "customized serializers in the current protocol instead."

                self._enter_cloth(ctx, cloth, parent,
                                          method=cls_attrs.method, skip=as_data)

                ret = subprot.subserialize(ctx, cls, inst, parent, name,
                                     as_attr=as_attr, as_data=as_data, **kwargs)

            # if there is no subprotocol, try rendering the value
            else:
                ret = None

                # try rendering the null value
                if inst is None:
                    if cls_attrs.min_occurs > 0:
                        attrs = {}
                        if as_attr:
                            # FIXME: test needed
                            attrs[name] = ''

                        self._enter_cloth(ctx, cloth, parent, attrib=attrs,
                                                        method=cls_attrs.method)
                        identifier = "%s.%s" % (prot_name, "null_to_cloth")
                        logger_s.debug("Writing '%s' using %s type: %s.", name,
                                                identifier, cls.get_type_name())
                        parent.write(cloth)

                    else:
                        logger_s.debug("Skipping '%s' type: %s because empty.",
                                                      name, cls.get_type_name())
                        self._enter_cloth(ctx, cloth, parent, skip=True,
                                                        method=cls_attrs.method)

                elif as_data:
                    # we only support XmlData of a primitive.,. is this a
                    # problem?
                    ret = self.to_unicode(cls, inst)
                    if ret is not None:
                        parent.write(ret)

                elif as_attr:
                    sub_name = cls_attrs.sub_name
                    if sub_name is None:
                        sub_name = name
                    attrs = {sub_name: self.to_unicode(cls, inst)}

                    self._enter_cloth(ctx, cloth, parent, attrib=attrs,
                                                        method=cls_attrs.method)

                else:
                    # push the instance at hand to instance stack. this makes it
                    # easier for protocols to make decisions based on parents of
                    # instances at hand.
                    pushed = True
                    logger_c.debug("%s %r pushed %r %r", R("#"), self, cls, inst)
                    ctx.outprot_ctx.inst_stack.append((cls, inst, from_arr))

                    # try rendering the array value
                    if not from_arr and cls.Attributes.max_occurs > 1:
                        ret = self.array_to_cloth(ctx, cls, inst, cloth, parent,
                                                     as_attr=as_attr, name=name)
                    else:
                        # try rendering anything else
                        handler = self.rendering_handlers[cls]

                        # disabled for performance reasons
                        # identifier = "%s.%s" % (prot_name, handler.__name__)
                        # from spyne.util.web import log_repr
                        # logger_s.debug("Writing %s using %s for %s. Inst: %r",
                        #              name, identifier, cls.get_type_name(),
                        #              log_repr(inst, cls, from_array=from_arr))

                        ret = handler(ctx, cls, inst, cloth, parent, name=name,
                                                                as_attr=as_attr)

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
                    if pushed:
                        logger_c.debug("%s %r popped %r %r", B("#"),
                                                                self, cls, inst)
                        ctx.outprot_ctx.inst_stack.pop()

        else:
            if pushed:
                logger_c.debug("%s %r popped %r %r", B("#"), self, cls, inst)
                ctx.outprot_ctx.inst_stack.pop()

    def model_base_to_cloth(self, ctx, cls, inst, cloth, parent, name,
                                                                      **kwargs):
        cls_attrs = self.get_cls_attrs(cls)
        self._enter_cloth(ctx, cloth, parent, method=cls_attrs.method)

        # FIXME: Does it make sense to do this in other types?
        if self.WRITE_CONTENTS_WHEN_NOT_NONE in cloth.attrib:
            logger_c.debug("Writing contents for %r", cloth)
            for c in cloth:
                parent.write(c)

        else:
            parent.write(self.to_unicode(cls, inst))

    def xml_to_cloth(self, ctx, cls, inst, cloth, parent, name, **_):
        cls_attrs = self.get_cls_attrs(cls)
        self._enter_cloth(ctx, cloth, parent, method=cls_attrs.method)
        if isinstance(inst, string_types):
            inst = etree.fromstring(inst)
        parent.write(inst)

    def any_to_cloth(self, ctx, cls, inst, cloth, parent, name, **_):
        cls_attrs = self.get_cls_attrs(cls)
        self._enter_cloth(ctx, cloth, parent, method=cls_attrs.method)
        parent.write(inst)

    def html_to_cloth(self, ctx, cls, inst, cloth, parent, name, **_):
        cls_attrs = self.get_cls_attrs(cls)
        self._enter_cloth(ctx, cloth, parent, method=cls_attrs.method)
        if isinstance(inst, string_types):
            inst = html.fromstring(inst)
        parent.write(inst)

    def any_uri_to_cloth(self, ctx, cls, inst, cloth, parent, name, **kwargs):
        cls_attrs = self.get_cls_attrs(cls)
        self._enter_cloth(ctx, cloth, parent, method=cls_attrs.method)
        self.any_uri_to_parent(ctx, cls, inst, parent, name, **kwargs)

    @coroutine
    def complex_to_cloth(self, ctx, cls, inst, cloth, parent, name=None,
                                                       as_attr=False, **kwargs):
        fti = cls.get_flat_type_info(cls)
        cls_attrs = self.get_cls_attrs(cls)

        # It's actually an odict but that's irrelevant here.
        fti_check = dict(fti.items())
        elt_check = set()

        attrib = self._gen_attrib_dict(inst, fti)
        self._enter_cloth(ctx, cloth, parent, attrib=attrib,
                                                        method=cls_attrs.method)

        for elt in self._get_elts(cloth, self.MRPC_ID):
            self._actions_to_cloth(ctx, cls, inst, elt)

        if self._is_tagbag(cloth):
            logger_c.debug("%r(%r) IS a tagbag", cloth, cloth.attrib)
            elts = self._get_elts(cloth)
        else:
            logger_c.debug("%r(%r) is NOT a tagbag", cloth, cloth.attrib)
            elts = self._get_outmost_elts(cloth)

        # Check for xmldata after entering the cloth.
        as_data_field = cloth.attrib.get(self.DATA_ATTR_NAME, None)
        if as_data_field is not None:
            self._process_field(ctx, cls, inst, parent, cloth, fti,
                   as_data_field, as_attr, True, fti_check, elt_check, **kwargs)

        for elt in elts:
            for k_attr, as_attr, as_data in ((self.ID_ATTR_NAME, False, False),
                                            (self.ATTR_ATTR_NAME, True, False),
                                            (self.DATA_ATTR_NAME, False, True)):
                field_name = elt.attrib.get(k_attr, None)
                if field_name is None:
                    continue

                if elt.tag == self.DATA_TAG_NAME:
                    as_data = True

                ret = self._process_field(ctx, cls, inst, parent, elt, fti,
                     field_name, as_attr=as_attr, as_data=as_data,
                             fti_check=fti_check, elt_check=elt_check, **kwargs)

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
                            # cf below
                            if not (as_attr or as_data):
                                break
                else:
                    # this is here so that attribute on complex model doesn't get
                    # mixed with in-line attr inside complex model. if an element
                    # has spyne-id, all other attrs are ignored and are processed
                    # by the object's serializer not its parent.
                    if not (as_attr or as_data):
                        break

        if len(fti_check) > 0:
            logger_s.debug("No element found for the following fields: %r",
                                                         list(fti_check.keys()))
        if len(elt_check) > 0:
            logger_s.debug("No field found for element the following "
                                              "elements: %r", list(elt_check))

    def _process_field(self, ctx, cls, inst, parent,
                   elt, fti, field_name, as_attr, as_data, fti_check, elt_check,
                                                                      **kwargs):
        field_type = fti.get(field_name, None)
        fti_check.pop(field_name, None)

        if field_type is None:
            logger_c.warning("elt id %r not in %r", field_name, cls)
            elt_check.add(field_name)
            self._enter_cloth(ctx, elt, parent, skip=True)
            return

        cls_attrs = self.get_cls_attrs(field_type)
        if cls_attrs.exc:
            logger_c.debug("Skipping elt id %r because "
                           "it was excluded", field_name)
            return

        sub_name = cls_attrs.sub_name
        if sub_name is None:
            sub_name = field_name

        if issubclass(cls, Array):
            # if cls is an array, inst should already be a sequence type
            # (eg list), so there's no point in doing a getattr -- we will
            # unwrap it and serialize it in the next round of to_cloth call.
            val = inst
        else:
            val = getattr(inst, field_name, None)

        if as_data:
            self._enter_cloth(ctx, elt, parent, skip=True, skip_dupe=True,
                                                        method=cls_attrs.method)

        return self.to_cloth(ctx, field_type, val, elt, parent,
                      name=sub_name, as_attr=as_attr, as_data=as_data, **kwargs)

    @coroutine
    def array_to_cloth(self, ctx, cls, inst, cloth, parent, name=None,
                                                                      **kwargs):
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
            sv = _NODATA

            for sv in inst:
                was_empty = False

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

            if sv is _NODATA:
                # FIXME: what if min_occurs >= 1?
                # fake entering the cloth to prevent it from being flushed as
                # parent or sibling of another node later.
                self._enter_cloth(ctx, cloth, parent, skip=True)
