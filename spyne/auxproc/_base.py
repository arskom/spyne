
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


"""Base class and other helper methods for Auxiliary Method Processors
('AuxProc's for short). AuxProcs define how an auxiliary method is going to be
executed.
"""

import logging
logger = logging.getLogger(__name__)

from spyne import AuxMethodContext


def process_contexts(server, contexts, p_ctx, error=None):
    """Method to be called in the auxiliary context."""

    for ctx in contexts:
        ctx.descriptor.aux.initialize_context(ctx, p_ctx, error)
        if error is None or ctx.descriptor.aux.process_exceptions:
            ctx.descriptor.aux.process_context(server, ctx)


class AuxProcBase(object):
    def __init__(self, process_exceptions=False):
        """Abstract Base class shared by all AuxProcs.

        :param process_exceptions: If false, does not execute auxiliary methods
        when the main method throws an exception.
        """

        self.methods = []
        self.process_exceptions = process_exceptions

    def process(self, server, ctx, *args, **kwargs):
        """The method that does the actual processing. This should be called
        from the auxiliary context.
        """

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
        """Override this to implement your own auxiliary processor."""

        raise NotImplementedError()

    def initialize(self, server):
        """Override this method to make arbitrary initialization of your
        AuxProc. It's called once, 'as late as possible' into the Application
        initialization."""

    def initialize_context(self, ctx, p_ctx, error):
        """Override this method to alter thow the auxiliary method context is
        initialized. It's called every time the method is executed.
        """

        ctx.aux = AuxMethodContext(p_ctx, error)
