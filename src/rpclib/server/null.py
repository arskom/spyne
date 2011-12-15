
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

"""This module contains the NullServer class and its helper objects."""

import logging
logger = logging.getLogger(__name__)

from rpclib.client._base import Factory
from rpclib.const.ansi_color import LIGHT_RED
from rpclib.const.ansi_color import END_COLOR
from rpclib._base import MethodContext
from rpclib.server import ServerBase

class NullServer(ServerBase):
    """A server that doesn't support any transport at all -- it's implemented
    for testing services without running a server.
    """

    transport = 'noconn://null.rpclib'
    supports_fanout_methods = False

    def __init__(self, app):
        ServerBase.__init__(self, app)

        self.service = _FunctionProxy(self, self.app)
        self.factory = Factory(self.app)

    def get_wsdl(self):
        return self.app.get_interface_document(self.url)

    def set_options(self, **kwargs):
        self.service.in_header = kwargs.get('soapheaders', None)

class _FunctionProxy(object):
    def __init__(self, server, app):
        self.__app = app
        self.__server = server
        self.in_header = None

    def __getattr__(self, key):
        return _FunctionCall(self.__app, self.__server, key, self.in_header)

class _FunctionCall(object):
    def __init__(self, app, server, key, in_header):
        self.__key = key
        self.__app = app
        self.__server = server
        self.__in_header = in_header

    def __call__(self, *args, **kwargs):
        initial_ctx = MethodContext(self.__app)
        initial_ctx.method_request_string = self.__key
        initial_ctx.in_header = self.__in_header
        initial_ctx.in_object = args

        contexts = self.__app.in_protocol.generate_method_contexts(initial_ctx)
        for ctx in contexts:
            # set logging.getLogger('rpclib.server.null').setLevel(logging.CRITICAL)
            # to hide the following
            _header = ('=' * 30) + LIGHT_RED
            _footer = END_COLOR + ('=' * 30)

            logger.warning( "%s start request %s" % (_header, _footer)  )
            self.__app.process_request(ctx)
            logger.warning( "%s  end request  %s" % (_header, _footer)  )

            if ctx.out_error:
                raise ctx.out_error

            else:
                if len(ctx.descriptor.out_message._type_info) == 0:
                    retval = None

                elif len(ctx.descriptor.out_message._type_info) == 1:
                    retval = ctx.out_object[0]

                    # workaround to have the context disposed of when the caller is done
                    # with the return value. the context is sometimes needed to fully
                    # construct the return object (e.g. when the object is a sqlalchemy
                    # object bound to a session that's defined in the context object).
                    try:
                        retval.__ctx__ = ctx
                    except AttributeError:
                        # not all objects let this happen. (eg. built-in types like str)
                        # which don't need the context anyway.
                        pass

                else:
                    retval = ctx.out_object

                    # same as above
                    try:
                        retval[0].__ctx__ = ctx
                    except AttributeError:
                        pass

        return retval
