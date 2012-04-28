
#
# rpclib - Copyright (C) Rpclib contributors.
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


def process_contexts(server, contexts, error=None):
    for ctx in contexts:
        if error is None or ctx.descriptor.aux.process_exceptions:
            ctx.descriptor.aux.process_context(server, ctx, error)


class AuxProcBase(object):
    def __init__(self, process_exceptions=False):
        self.methods = []
        self.process_exceptions = process_exceptions

    def initialize(self):
        pass

    def process(self, server, ctx, error, *args, **kwargs):
        logger.debug("Executing %r" % ctx.descriptor.function)
        server.get_in_object(ctx)
        if ctx.in_error:
            logger.exception(ctx.in_error)
            return ctx.in_error

        server.get_out_object(ctx)
        if ctx.out_error:
            logger.exception(ctx.out_error)
            return ctx.out_error

        server.get_out_string(ctx)
        for s in ctx.out_string:
            logger.debug(s)
