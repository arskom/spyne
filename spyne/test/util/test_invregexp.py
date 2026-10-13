#!/usr/bin/env python
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

import unittest

from spyne.util.invregexp import invregexp


class TestInvRegexp(unittest.TestCase):
    def test_alternative(self):
        assert sorted(invregexp('GET|POST')) == ['GET', 'POST']

    def test_range_and_repetition(self):
        assert list(invregexp('[A-C]{2}')) == \
               ['AA', 'AB', 'AC', 'BA', 'BB', 'BC', 'CA', 'CB', 'CC']

    def test_optional_and_group(self):
        assert sorted(invregexp('X(ab)?')) == ['X', 'Xab']

