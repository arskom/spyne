
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

from twisted.internet.defer import Deferred
from twisted.internet.interfaces import IPullProducer
from twisted.web.iweb import UNKNOWN_LENGTH

from zope.interface import implementer


@implementer(IPullProducer)
class Producer(object):
    deferred = None

    def __init__(self, body, consumer):
        """:param body: an iterable of strings"""

        # check to see if we can determine the length
        try:
            len(body) # iterator?
            self.length = sum([len(fragment) for fragment in body])
            self.body = iter(body)

        except TypeError:
            self.length = UNKNOWN_LENGTH
            self.body = body

        self.deferred = Deferred()

        self.consumer = consumer

    def resumeProducing(self):
        try:
            chunk = next(self.body)

        except StopIteration as e:
            self.consumer.unregisterProducer()
            if self.deferred is not None:
                self.deferred.callback(self.consumer)
                self.deferred = None
            return

        self.consumer.write(chunk)

    def pauseProducing(self):
        pass

    def stopProducing(self):
        if self.deferred is not None:
            self.deferred.errback(
                               Exception("Consumer asked us to stop producing"))
        self.deferred = None


from spyne import Address
_TYPE_MAP = {'TCP': Address.TCP4, 'TCP6': Address.TCP6,
             'UDP': Address.UDP4, 'UDP6': Address.UDP6}

def _address_from_twisted_address(peer):
    return Address(
            type=_TYPE_MAP.get(peer.type, None), host=peer.host, port=peer.port)

Address.from_twisted_address = staticmethod(_address_from_twisted_address)
