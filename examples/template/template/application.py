
import logging
logger = logging.getLogger(__name__)

from spyne.application import Application
from spyne.error import Fault
from spyne.error import InternalError
from spyne.error import ResourceNotFoundError
from spyne.util.email import email_exception

from sqlalchemy.orm.exc import NoResultFound

from template.context import UserDefinedContext

EXCEPTION_ADDRESS = "everybody@example.com"


def _on_method_call(ctx):
    ctx.udc = UserDefinedContext()


def _on_method_context_closed(ctx):
    if ctx.udc is not None:
        ctx.udc.session.commit()
        ctx.udc.session.close()


class MyApplication(Application):
    def __init__(self, services, tns, name=None,
                                         in_protocol=None, out_protocol=None):
        Application.__init__(self, services, tns, name, in_protocol,
                                                                 out_protocol)

        self.event_manager.add_listener('method_call', _on_method_call)
        self.event_manager.add_listener("method_context_closed",
                                                    _on_method_context_closed)

    def call_wrapper(self, ctx):
        try:
            return ctx.service_class.call_wrapper(ctx)

        except NoResultFound:
            raise ResourceNotFoundError(ctx.in_object)

        except Fault, e:
            logger.error(e)
            raise

        except Exception, e:
            logger.exception(e)
            # This should not happen! Let the team know via email
            email_exception(EXCEPTION_ADDRESS)
            raise InternalError(e)
