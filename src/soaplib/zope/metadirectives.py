from zope.interface import Interface
from zope.configuration.fields import GlobalObject
from zope.schema import TextLine, List


class ISoaplibHandlerDirective(Interface):
    """Handles http/soap requests
    """

    name = TextLine(
        title=u"name",
        description=u"The name of the requested view"
        )

    for_ = GlobalObject(
        title=u"For Interface",
        description=u"The interface the directive is used for",
        required=False
        )

    service_definitions = List(
        title=u"Service Definitions",
        description=u"The service definitions to be served",
        required=True
        )

    app_namespace = TextLine(
        title=u"Application Namespace",
        description=u"The namespace for the soap application",
        required=True
        )
