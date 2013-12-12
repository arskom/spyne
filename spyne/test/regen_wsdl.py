#!/usr/bin/env python

from lxml import etree
from spyne.test.sort_wsdl import sort_wsdl
from spyne.interface.wsdl import Wsdl11

from spyne.test.interop.server._service import services
from spyne.application import Application

app = Application(services, 'spyne.test.interop.server')
app.transport = 'http://schemas.xmlsoap.org/soap/http'
wsdl = Wsdl11(app.interface)
wsdl.build_interface_document('http://localhost:9754/')
elt = etree.ElementTree(etree.fromstring(wsdl.get_interface_document()))
sort_wsdl(elt)
s = etree.tostring(elt)

# minidom's serialization seems to put attributes in alphabetic order.
# this is exactly what we want here.
from xml.dom.minidom import parseString
doc = parseString(s)
s = doc.toprettyxml(indent='  ', newl='\n', encoding='utf8')
s = s.replace(" xmlns:","\n                  xmlns:")

open('wsdl.xml', 'w').write(s)
print('wsdl.xml written')
