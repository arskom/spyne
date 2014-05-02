
from spyne.protocol.html.table import HtmlColumnTable
from spyne.protocol.html.table import HtmlRowTable
from spyne.protocol.html.microformat import HtmlMicroFormat


# FIXME: REMOVE ME
def translate(cls, locale, default):
    retval = None
    if cls.Attributes.translations is not None:
        retval = cls.Attributes.translations.get(locale, None)
    if retval is None:
        return default
    return retval
