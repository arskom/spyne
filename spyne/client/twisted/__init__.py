
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

"""The Twisted Http Client transport."""

from spyne import __version__ as VERSION
from spyne.util import six

from spyne.client import RemoteService
from spyne.client import RemoteProcedureBase
from spyne.client import ClientBase

from zope.interface import implements

from twisted.internet import reactor
from twisted.internet.defer import Deferred
from twisted.internet.protocol import Protocol

from twisted.web import error as werror
from twisted.web.client import Agent
from twisted.web.client import ResponseDone
from twisted.web.iweb import IBodyProducer
from twisted.web.iweb import UNKNOWN_LENGTH
from twisted.web.http_headers import Headers


class _Producer(object):
    if six.PY2:
        implements(IBodyProducer)

    _deferred = None

    def __init__(self, body):
        """:param body: an iterable of strings"""

        self.__paused = False

        # check to see if we can determine the length
        try:
            len(body) # iterator?
            self.length = sum([len(fragment) for fragment in body])
            self.body = iter(body)

        except TypeError:
            self.length = UNKNOWN_LENGTH

        self._deferred = Deferred()

    def startProducing(self, consumer):
        self.consumer = consumer

        self.resumeProducing()

        return self._deferred

    def resumeProducing(self):
        self.__paused = False
        for chunk in self.body:
            self.consumer.write(chunk)
            if self.__paused:
                break
        else:
            self._deferred.callback(None) # done producing forever

    def pauseProducing(self):
        self.__paused = True

    def stopProducing(self):
        self.__paused = True


class _Protocol(Protocol):
    def __init__(self, ctx):
        self.ctx = ctx
        self.deferred = Deferred()

    def dataReceived(self, bytes):
        self.ctx.in_string.append(bytes)

    def connectionLost(self, reason):
        if reason.check(ResponseDone):
            self.deferred.callback(None)
        else:
            self.deferred.errback(reason)


class _RemoteProcedure(RemoteProcedureBase):
    def __call__(self, *args, **kwargs):
        # there's no point in having a client making the same request more than
        # once, so if there's more than just one context, it's rather a bug.
        # The comma-in-assignment trick is a pedantic way of getting the first
        # and the only variable from an iterable. so if there's more than one
        # element in the iterable, it'll fail miserably.
        self.ctx, = self.contexts

        self.get_out_object(self.ctx, args, kwargs)
        self.get_out_string(self.ctx)

        self.ctx.in_string = []

        agent = Agent(reactor)
        d = agent.request(
            b'POST', self.url,
            Headers({b'User-Agent':
                         [b'Spyne Twisted Http Client %s' % VERSION.encode()]}),
            _Producer(self.ctx.out_string)
        )

        def _process_response(_, response):
            # this sets ctx.in_error if there's an error, and ctx.in_object if
            # there's none.
            self.get_in_object(self.ctx)

            if self.ctx.in_error is not None:
                raise self.ctx.in_error
            elif response.code >= 400:
                raise werror.Error(response.code)
            return self.ctx.in_object

        def _cb_request(response):
            p = _Protocol(self.ctx)
            response.deliverBody(p)
            return p.deferred.addCallback(_process_response, response)

        return d.addCallback(_cb_request)


class TwistedHttpClient(ClientBase):
    def __init__(self, url, app):
        super(TwistedHttpClient, self).__init__(url, app)

        self.service = RemoteService(_RemoteProcedure, url, app)
