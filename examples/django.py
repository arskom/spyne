# coding: utf-8

# Fork of https://gist.github.com/1242760

from django.http import HttpResponse
from rpclib.server.wsgi import WsgiApplication

class DjangoApplication(WsgiApplication):
    def __call__(self, request):
        django_response = HttpResponse()

        def start_response(status, headers):
            status, reason = status.split(' ', 1)

            django_response.status_code = int(status)
            for header, value in headers:
                django_response[header] = value

        environ = request.META.copy()
        environ['wsgi.input'] = request
        environ['wsgi.multithread'] = False

        response = WsgiApplication.__call__(self, environ, start_response)

        django_response.content = "\n".join(response)

        return django_response
