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

#
# This module contains DEPRECATED code. It can disappear at any moment now.
#

import logging
logger = logging.getLogger(__name__)

from lxml import html
from spyne.util import six


class HtmlPage(object):
    """An EXPERIMENTAL protocol-ish that parses and generates a template for
    a html file.

    >>> open('temp.html', 'w').write('<html><body><div id="some_div" /></body></html>')
    >>> t = HtmlPage('temp.html')
    >>> t.some_div = "some_text"
    >>> from lxml import html
    >>> print html.tostring(t.html)
    <html><body><div id="some_div">some_text</div></body></html>
    """

    reserved = ('html', 'file_name')

    def __init__(self, file_name):
        self.__frozen = False
        self.__file_name = file_name
        self.__html = html.fromstring(open(file_name, 'r').read())

        self.__ids = {}
        for elt in self.__html.xpath('//*[@id]'):
            key = elt.attrib['id']
            if key in self.__ids:
                raise ValueError("Don't use duplicate values in id attributes "
                                 "of the tags in template documents. "
                                 "id=%r appears more than once." % key)
            if key in HtmlPage.reserved:
                raise ValueError("id attribute values %r are reserved." %
                                                              HtmlPage.reserved)

            self.__ids[key] = elt
            s = "%r -> %r" % (key, elt)
            logger.debug(s)

        self.__frozen = True

    @property
    def file_name(self):
        return self.__file_name

    @property
    def html(self):
        return self.__html

    def __getattr__(self, key):
        try:
            return object.__getattr__(self, key)

        except AttributeError:
            try:
                return self.__ids[key]
            except KeyError:
                raise AttributeError(key)

    def __setattr__(self, key, value):
        if key.endswith('__frozen') or not self.__frozen:
            object.__setattr__(self, key, value)

        else:
            elt = self.__ids.get(key, None)
            if elt is None:
                raise AttributeError(key)

            # set it in.
            if isinstance(value, six.string_types):
                elt.text = value
            else:
                elt.addnext(value)
                parent = elt.getparent()
                parent.remove(elt)
                self.__ids[key] = value
