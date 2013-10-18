#!/usr/bin/env python
from werkzeug.wsgi import DispatcherMiddleware

from apps import spyned
from apps.flasked import app


# SOAP services are distinct wsgi applications, we should use dispatcher
# middleware to bring all aps together
app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {
    '/soap': spyned.wsgi_application
})

if __name__ == '__main__':
    app.run()
