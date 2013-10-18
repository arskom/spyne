from spyne.application import Application
from spyne.decorator import srpc
from spyne.model.complex import Iterable
from spyne.model.primitive import Integer, Unicode
from spyne.protocol.http import HttpRpc
from spyne.protocol.json import JsonDocument
from spyne.service import ServiceBase
from spyne.server.wsgi import WsgiApplication


class HelloWorldService(ServiceBase):
    @srpc(Unicode, Integer, _returns=Iterable(Unicode))
    def hello(name, times):
        for i in range(times):
            yield u'Hello, %s' % name


application = Application(
    [HelloWorldService], 'flask-spyne-example',
    # The input protocol is set as HttpRpc to make our service easy to call.
    in_protocol=HttpRpc(validator='soft'),
    out_protocol=JsonDocument(ignore_wrappers=True),
)

wsgi_application = WsgiApplication(application)
