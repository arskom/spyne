
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

import unittest

from lxml import etree
from lxml.builder import E

from spyne import ComplexModel, XmlAttribute, Unicode, Array, Integer
from spyne.protocol.cloth import XmlCloth
from spyne.test import FakeContext
from spyne.util.six import BytesIO


class TestXmlCloth(unittest.TestCase):
    def setUp(self):
        self.ctx = FakeContext()
        self.stream = BytesIO()
        logging.basicConfig(level=logging.DEBUG)

    def _run(self, spid, inst):
        cls = inst.__class__
        tmpl = etree.fromstring("""<a><b spyne_id="%s"></b></a>""" % spid)
        with etree.xmlfile(self.stream) as parent:
            XmlCloth(tmpl).subserialize(self.ctx, cls, inst, parent)
        elt = etree.fromstring(self.stream.getvalue())
        print etree.tostring(elt, pretty_print=True)
        return elt

    def test_simple_value(self):
        class SomeObject(ComplexModel):
            s = Unicode

        v = 'punk.'
        elt = self._run('s', SomeObject(s=v))

        assert elt[0].text == v

    def test_simple_empty(self):
        class SomeObject(ComplexModel):
            s = Unicode

        elt = self._run('s', SomeObject())

        assert len(elt) == 0

