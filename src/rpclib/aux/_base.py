
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

from rpclib import AuxMethodContext


def process_contexts(server, contexts, p_ctx, error=None):
    for ctx in contexts:
        ctx.descriptor.aux.initialize_context(ctx, p_ctx, error)
        if error is None or ctx.descriptor.aux.process_exceptions:
            ctx.descriptor.aux.process_context(server, ctx)


class AuxProcBase(object):
    def __init__(self, process_exceptions=False):
        self.methods = []
        self.process_exceptions = process_exceptions

    def process(self, server, ctx, *args, **kwargs):
        server.get_in_object(ctx)
        if ctx.in_error is not None:
            logger.exception(ctx.in_error)
            return ctx.in_error

        server.get_out_object(ctx)
        if ctx.out_error is not None:
            logger.exception(ctx.out_error)
            return ctx.out_error

        server.get_out_string(ctx)
        for s in ctx.out_string:
            pass

    def process_context(self, server, ctx, p_ctx, p_error):
        raise NotImplementedError()

    def initialize(self, server):
        pass

    def initialize_context(self, ctx, p_ctx, error):
        ctx.aux = AuxMethodContext(p_ctx, error)
