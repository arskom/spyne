
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

"""The ``spyne.protocol.Yaml`` package contains the Yaml-related protocols.
Currently, only :class:`spyne.protocol.Yaml.YamlDocument` is supported.

Initially released in 2.8.0-rc.

This module is EXPERIMENTAL. You may not recognize the code here next time you
look at it.
"""

from __future__ import absolute_import

import logging
logger = logging.getLogger(__name__)

from spyne.model.fault import Fault
from spyne.protocol.dictobj import DictDocument


import yaml
try:
    from yaml import CLoader as Loader
    from yaml import CDumper as Dumper
except ImportError:
    from yaml import Loader
    from yaml import Dumper

from yaml.parser import ParserError


class YamlDocument(DictDocument):
    """An implementation of the Yaml protocol that uses simpleYaml package when
    available, Yaml package otherwise.
    """

    mime_type = 'application/x-yaml'

    type = set(DictDocument.type)
    type.add('yaml')

    def create_in_document(self, ctx, in_string_encoding=None):
        """Sets ``ctx.in_document``  using ``ctx.in_string``."""

        if in_string_encoding is None:
            in_string_encoding = 'UTF-8'

        try:
            ctx.in_document = yaml.load(''.join(ctx.in_string).decode(
                                             in_string_encoding), Loader=Loader)
        except ParserError, e:
            raise Fault('Client.YamlDecodeError', repr(e))

    def create_out_string(self, ctx, out_string_encoding='utf8'):
        """Sets ``ctx.out_string`` using ``ctx.out_document``."""
        ctx.out_string = (yaml.dump(o, Dumper=Dumper) for o in ctx.out_document)
