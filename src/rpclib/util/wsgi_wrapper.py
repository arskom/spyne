
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

"""A Convenience module for wsgi wrapper routines."""

from rpclib.server.wsgi import WsgiApplication
import os
import logging
logger = logging.getLogger(__name__)

import twisted.web.server
import twisted.web.static

from twisted.web.resource import Resource
from twisted.web.wsgi import WSGIResource
from twisted.internet import reactor

class WsgiMounter(object):
    @staticmethod
    def default(e, s):
        s("404 Not found", [])
        return []

    def __init__(self, mounts=None):
        self.mounts = mounts or { }
        self.mounts = dict([(k, WsgiApplication(v)) for k,v in self.mounts.items()])

    def __call__(self, environ, start_response):
        path_info = environ.get('PATH_INFO', '')
        fragments = [a for a in path_info.split('/') if len(a) > 0]

        script = ''
        if len(fragments) > 0:
            script = fragments[0]

        app = self.mounts.get(script, self.default)

        original_script_name = environ.get('SCRIPT_NAME', '')

        environ['SCRIPT_NAME'] = original_script_name + script
        environ['PATH_INFO'] = '/' + '/'.join(fragments[1:])

        return app(environ, start_response)


def run_twisted(apps, port, static_dir='.'):
    """Twisted wrapper for the rpclib.server.wsgi.Application

    Takes a list of tuples containing application, url pairs, and a port to
    to listen to.
    """

    if static_dir != None:
        static_dir = os.path.abspath(static_dir)
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
