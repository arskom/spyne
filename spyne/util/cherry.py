# Use Cherrypy as wsgi server.
# Source: https://www.digitalocean.com/community/tutorials/how-to-deploy-python-wsgi-applications-using-a-cherrypy-web-server-behind-nginx

import logging
import cherrypy


def cherry_graft_and_start(wsgi_application, host="0.0.0.0", port=8080,
             num_threads=30, ssl_module=None, cert=None, key=None, cacert=None):

    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger('spyne.protocol.xml').setLevel(logging.DEBUG)

    # Mount the application
    cherrypy.tree.graft(wsgi_application, "/")

    # Unsubscribe the default server
    cherrypy.server.unsubscribe()

    # Instantiate a new server object
    server = cherrypy._cpserver.Server()

    # Configure the server object
    server.socket_host = host
    server.socket_port = port
    server.thread_pool = num_threads

    # For SSL Support
    if ssl_module is not None:
        server.ssl_module            = ssl_module  # eg. 'pyopenssl'
        server.ssl_certificate       = cert  # eg. 'ssl/certificate.crt'
        server.ssl_private_key       = key  # eg. 'ssl/private.key'
        server.ssl_certificate_chain = cacert  # eg. 'ssl/bundle.crt'

    # Subscribe this server
    server.subscribe()

    # Start the server engine (Option 1 *and* 2)
    cherrypy.engine.start()

    return cherrypy.engine.block()
