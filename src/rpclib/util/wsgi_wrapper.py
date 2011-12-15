
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

"""A Convenience module for wsgi wrapper libraries."""

import os
import logging
logger = logging.getLogger(__name__)

import twisted.web.server
import twisted.web.static

from twisted.web.resource import Resource
from twisted.web.wsgi import WSGIResource
from twisted.internet import reactor

def run_twisted(apps, port, with_static_file_server=True):
    """Twisted wrapper for the rpclib.server.wsgi.Application

    Takes a list of tuples containing application, url pairs, and a port to
    to listen to.
    """

    static_dir = os.path.abspath(".")
    if with_static_file_server:
        logging.info("registering static folder %r on /" % static_dir)
        root = twisted.web.static.File(static_dir)
    else:
        root = Resource()

    for app, url in apps:
        resource = WSGIResource(reactor, reactor, app)
        logging.info("registering %r on /%s" % (app, url))
        root.putChild(url, resource)

    site = twisted.web.server.Site(root)

    reactor.listenTCP(port, site)
    logging.info("listening on: 0.0.0.0:%d" % port)

    return reactor.run()
