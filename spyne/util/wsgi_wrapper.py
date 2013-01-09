
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

"""A Convenience module for wsgi wrapper routines."""

import os
import logging
logger = logging.getLogger(__name__)

from spyne.server.wsgi import WsgiApplication

class WsgiMounter(object):
    """Simple mounter object for wsgi callables. Takes a dict where the keys are
    uri fragments and values are :class:`spyne.application.Application`
    instances.
    """

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

        environ['SCRIPT_NAME'] = "/" + original_script_name + script
        environ['PATH_INFO'] = '/' + '/'.join(fragments[1:])

        return app(environ, start_response)


def run_twisted(apps, port, static_dir='.', interface='0.0.0.0'):
    """Twisted wrapper for the spyne.server.wsgi.WsgiApplication. Twisted can
    use one thread per request to run services, so code wrapped this way does
    not necessarily have to respect twisted way of doing things.

    :param apps: List of tuples containing (application, url) pairs
    :param port: Port to listen to.
    :param static_dir: The directory that contains static files. Pass `None` if
        you don't want to server static content. Url fragments in the `apps`
        argument take precedence.
    :param interface: The network interface to which the server binds, if not
        specified, it will accept connections on any interface by default.
    """

    import twisted.web.server
    import twisted.web.static

    from twisted.web.resource import Resource
    from twisted.web.wsgi import WSGIResource
    from twisted.internet import reactor

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
    reactor.listenTCP(port, site, interface=interface)
    logging.info("listening on: %s:%d" % (interface, port))

    return reactor.run()
