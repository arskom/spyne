
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
from spyne.protocol.dictdoc import HierDictDocument

import yaml

from yaml.parser import ParserError
try:
    from yaml import CLoader as Loader
    from yaml import CDumper as Dumper
    from yaml import CSafeLoader as SafeLoader
    from yaml import CSafeDumper as SafeDumper

except ImportError:
    from yaml import Loader
    from yaml import Dumper
    from yaml import SafeLoader
    from yaml import SafeDumper


class YamlDocument(HierDictDocument):
    """An implementation of the Yaml protocol that uses the PyYaml package.
    See ProtocolBase ctor docstring for its arguments. Yaml-specific arguments
    follow:

    :param safe: Use ``safe_dump`` instead of ``dump`` and ``safe_load`` instead
    of ``load``. This is not a security feature, search for 'safe_dump' in
    http://www.pyyaml.org/wiki/PyYAMLDocumentation
    :param kwargs: See the yaml documentation in ``load, ``safe_load``, ``dump``
    or ``safe_dump`` depending on whether you use yaml as an input or output
    protocol.

    For the output case, Spyne sets ``default_flow_style=False`` and
    ``indent=4`` by default.
    """

    mime_type = 'text/yaml'

    type = set(HierDictDocument.type)
    type.add('yaml')

    def __init__(self, app=None, validator=None, mime_type=None, skip_depth=0,
                                                            ignore_uncap=False,
                # these are yaml specific
                safe=True, **kwargs):

        HierDictDocument.__init__(self, app, validator, mime_type, skip_depth,
                                                                   ignore_uncap)

        self.in_kwargs = dict(kwargs)
        self.out_kwargs = dict(kwargs)

        self.in_kwargs['Loader'] = Loader
        self.out_kwargs['Dumper'] =  Dumper
        if safe:
            self.in_kwargs['Loader'] = SafeLoader
            self.out_kwargs['Dumper'] =  SafeDumper

        if not 'indent' in self.out_kwargs:
            self.out_kwargs['indent'] = 4

        if not 'default_flow_style' in self.out_kwargs:
            self.out_kwargs['default_flow_style'] = False

    def create_in_document(self, ctx, in_string_encoding=None):
        """Sets ``ctx.in_document``  using ``ctx.in_string``."""

        if in_string_encoding is None:
            in_string_encoding = 'UTF-8'

        try:
            ctx.in_document = yaml.load(''.join(ctx.in_string).decode(
                         in_string_encoding), **self.in_kwargs)

        except ParserError, e:
            raise Fault('Client.YamlDecodeError', repr(e))

    def create_out_string(self, ctx, out_string_encoding='utf8'):
        """Sets ``ctx.out_string`` using ``ctx.out_document``."""
        ctx.out_string = (yaml.dump(o, **self.out_kwargs)
                                                      for o in ctx.out_document)
