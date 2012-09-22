
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

"""The ``spyne.server.null`` module contains the NullServer class and its helper
objects.

The name comes from the "null modem connection". Look it up.
"""

import logging
logger = logging.getLogger(__name__)

from spyne import MethodContext

from spyne.client import Factory
from spyne.const.ansi_color import LIGHT_RED
from spyne.const.ansi_color import LIGHT_BLUE
from spyne.const.ansi_color import END_COLOR
from spyne.server import ServerBase


_big_header = ('=' * 40) + LIGHT_RED
_big_footer = END_COLOR + ('=' * 40)
_small_header = ('-' * 20) + LIGHT_BLUE
_small_footer = END_COLOR + ('-' * 20)


class NullServer(ServerBase):
    """A server that doesn't support any transport at all -- it's implemented
    to test services without having to run a server.

    It implicitly uses the 'sync' auxiliary processing mode.

    Note that:
        1) ``**kwargs`` overwrite ``*args``.
        2) You can do: ::

            logging.getLogger('spyne.server.null').setLevel(logging.CRITICAL)

        to hide context delimiters in logs.
    """

    transport = 'noconn://null.spyne'

    def __init__(self, app):
        ServerBase.__init__(self, app)

        self.service = _FunctionProxy(self, self.app)
        self.factory = Factory(self.app)

    def get_wsdl(self):
        return self.app.get_interface_document(self.url)

    def set_options(self, **kwargs):
        self.service.in_header = kwargs.get('soapheaders', self.service.in_header)


class _FunctionProxy(object):
    def __init__(self, server, app):
        self.__app = app
        self.__server = server
        self.in_header = None

    def __getattr__(self, key):
        return _FunctionCall(self.__app, self.__server, key, self.in_header)


class _FunctionCall(object):
    def __init__(self, app, server, key, in_header):
        self.app = app

        self.__key = key
        self.__server = server
        self.__in_header = in_header

    def __call__(self, *args, **kwargs):
        initial_ctx = MethodContext(self)
        initial_ctx.method_request_string = self.__key
        initial_ctx.in_header = self.__in_header
        initial_ctx.transport.type = NullServer.transport

        contexts = self.app.in_protocol.generate_method_contexts(initial_ctx)

        cnt = 0
        retval = None
        logger.warning( "%s start request %s" % (_big_header, _big_footer)  )

        for ctx in contexts:
            # this reconstruction is quite costly. I wonder whether it's a
            # problem though.

            _type_info = ctx.descriptor.in_message._type_info
            ctx.in_object = [None] * len(_type_info)
            for i in range(len(args)):
                ctx.in_object[i] = args[i]

            for i,k in enumerate(_type_info.keys()):
                val = kwargs.get(k, None)
                if val is not None:
                    ctx.in_object[i] = val

            if cnt == 0:
                p_ctx = ctx
            else:
                ctx.descriptor.aux.initialize_context(ctx, p_ctx, error=None)

            # do logging.getLogger('spyne.server.null').setLevel(logging.CRITICAL)
            # to hide the following
            logger.warning( "%s start context %s" % (_small_header, _small_footer) )
            self.app.process_request(ctx)
            logger.warning( "%s  end context  %s" % (_small_header, _small_footer) )

            if ctx.out_error:
                raise ctx.out_error

            else:
                if len(ctx.descriptor.out_message._type_info) == 0:
                    _retval = None

                elif len(ctx.descriptor.out_message._type_info) == 1:
                    _retval = ctx.out_object[0]

                    # workaround to have the context disposed of when the caller
                    # is done with the return value. the context is sometimes
                    # needed to fully construct the return object (e.g. when the
                    # object is a sqlalchemy object bound to a session that's
                    # defined in the context object).
                    try:
                        _retval.__ctx__ = ctx
                    except AttributeError:
                        # not all objects let this happen. (eg. built-in types
                        # like str, but they don't need the context anyway).
                        pass

                else:
                    _retval = ctx.out_object

                    # same as above
                    try:
                        _retval[0].__ctx__ = ctx
                    except AttributeError:
                        pass

            if cnt == 0:
                retval = _retval
            cnt += 1

        logger.warning( "%s  end request  %s" % (_big_header, _big_footer)  )

        return retval
