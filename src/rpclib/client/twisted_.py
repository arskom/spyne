
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

"""The Twisted Http Client transport."""

from rpclib.client import Service
from rpclib.client import RemoteProcedureBase
from rpclib.client import ClientBase

from zope.interface import implements

from twisted.internet import reactor
from twisted.internet.defer import succeed
from twisted.web.iweb import IBodyProducer
from twisted.web.iweb import UNKNOWN_LENGTH
from twisted.web.http_headers import Headers

from twisted.internet.defer import Deferred
from twisted.internet.protocol import Protocol
from twisted.web.client import Agent

class _Producer(object):
    implements(IBodyProducer)

    def __init__(self, body):
        """:param body: an iterable of strings"""

        self.__paused = False

        # check to see if we can determine the length
        try:
            body[0] # check if this is a list
            self.length = sum([len(fragment) for fragment in body])

        except:
            self.length = UNKNOWN_LENGTH

        self.body = iter(body)

    def startProducing(self, consumer):
        self.__paused = False
        while not self.__paused:
            try:
                consumer.write(self.body.next())
            except StopIteration:
                break

        return succeed(None)

    def pauseProducing(self):
        self.__paused = True

    def stopProducing(self):
        self.__paused = True


class _Protocol(Protocol):
    def __init__(self, ctx, finished, response):
        self.finished = finished
        self.response = response
        self.ctx = ctx

    def dataReceived(self, bytes):
        self.ctx.in_string.append(bytes)

    def connectionLost(self, reason):
        self.finished(self.response, reason)


class _RemoteProcedure(RemoteProcedureBase):
    def __call__(self, *args, **kwargs):
        # there's no point in having a client making the same request more than
        # once, so if there's more than just one context, it's rather a bug.
        # the comma-in-assignment trick is a general way of getting the first
        # and the only variable from an iterable. so if there's more than one
        # element in the iterable, it'll fail miserably.
        self.ctx, = self.contexts

        self.get_out_object(self.ctx, args, kwargs)
        self.get_out_string(self.ctx)

        self.ctx.in_string = []

        agent = Agent(reactor)
        d = agent.request(
            'POST', 'http://localhost:9753/',
            Headers({'User-Agent': ['Rpclib Twisted Http Client']}),
            _Producer(self.ctx.out_string)
        )

        user_deferred = Deferred()
        def cb_finished(response, reason):
            # this sets ctx.in_error if there's an error, and ctx.in_object if
            # there's none.
            self.get_in_object(self.ctx)

            if not (self.ctx.in_error is None):
                user_deferred.errback(self.ctx.in_error)
            elif response.code >= 400:
                user_deferred.errback(self.ctx.in_error)
            else:
                user_deferred.callback(self.ctx.in_object)

        def cb_request(response):
            response.deliverBody(_Protocol(self.ctx, cb_finished, response))

        d.addCallback(cb_request)

        return user_deferred

class TwistedHttpClient(ClientBase):
    def __init__(self, url, app):
        ClientBase.__init__(self, url, app)

        self.service = Service(_RemoteProcedure, url, app)
