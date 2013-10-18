from spyne.application import Application
from spyne.decorator import rpc
from spyne.model.complex import Iterable
from spyne.model.primitive import Integer, Unicode
from spyne.protocol.http import HttpRpc
from spyne.protocol.json import JsonDocument
from spyne.service import ServiceBase


class HelloWorldService(ServiceBase):
    @rpc(Unicode, Integer, _returns=Iterable(Unicode))
    def hello(ctx, name, times):
        name = name or ctx.udc.config['HELLO']
        for i in range(times):
            yield u'Hello, %s' % name


class UserDefinedContext(object):
    def __init__(self, flask_config):
        self.config = flask_config


def create_app(flask_app):
    '''Creates SOAP services application and distribute Flask config into
    user con defined context for each method call.
    '''
    application = Application(
        [HelloWorldService], 'flask-spyne-example',
        # The input protocol is set as HttpRpc to make our service easy to call.
        in_protocol=HttpRpc(validator='soft'),
        out_protocol=JsonDocument(ignore_wrappers=True),
    )

    # Use `method_call` hook to pass flask config to each service method
    # context. But if you have any better ideas do it, make a pull request.
    # NOTE. I refuse idea to wrap each call into Flask application context
    # because in fact we inside Spyne app context, not the Flask one.
    def _flask_config_context(ctx):
        ctx.udc = UserDefinedContext(flask_app.config)
    application.event_manager.add_listener('method_call', _flask_config_context)

    return application
