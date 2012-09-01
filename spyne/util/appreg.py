
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

"""
Module that contains the Spyne Application Registry.
"""

import logging
logger = logging.getLogger(__name__)

_applications = {}

try:
    from collections import namedtuple

    _ApplicationMetaData = namedtuple("_ApplicationMetaData",
                                                  ['app', 'inst_stack', 'null'])
except ImportError: # python 2.5
    class _ApplicationMetaData:
        def __init__(self, app, inst_stack, null):
            self.app = app
            self.inst_stack = inst_stack
            self.null = null


def register_application(app):
    key = (app.tns, app.name)

    from spyne.server.null import NullServer

    try:
        import traceback
        stack = traceback.format_stack()
    except ImportError:
        stack = None

    prev = _applications.get(key, None)

    if prev is not None:
        if hash(prev.app) == hash(app):
            logger.debug("Application %r previously registered as %r is the same"
                        " as %r. Skipping." % (prev.app, key, app))
            prev.inst_stack.append(stack)

        else:
            logger.warning("Overwriting application %r(%r)." % (key, app))

            if prev.inst_stack is not None:
                stack_traces = []
                for s in prev.inst_stack:
                    if s is not None:
                        stack_traces.append(''.join(s))
                logger.debug("Stack trace of the instantiation:\n%s" %
                                   '====================\n'.join(stack_traces))

    _applications[key] = _ApplicationMetaData(app=app, inst_stack=[stack],
                                                          null=NullServer(app))

    logger.debug("Registering %r as %r" % (app, key))


def get_application(tns, name):
    return _applications.get((tns, name), None)
