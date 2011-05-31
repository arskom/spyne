#!/usr/bin/python

ns_wsdl = "http://schemas.xmlsoap.org/wsdl/"
ns_schema = "http://www.w3.org/2001/XMLSchema"
import sys

from lxml import etree
from collections import deque

def cache_order(l,ns):
	return dict([ ("{%s}%s" % (ns, a), l.index(a)) for a in l])

wsdl_order = ('types', 'message', 'binding', 'portType', 'service')
wsdl_order = cache_order(wsdl_order,ns_wsdl)

schema_order = ('import', 'element', 'simpleType', 'complexType')
schema_order = cache_order(schema_order,ns_schema)

parser = etree.XMLParser(remove_blank_text=True)
tree = etree.parse(sys.stdin, parser=parser)
from pprint import pprint

l0 = []
type_node = None

for e in tree.getroot():
	if e.tag == "{http://schemas.xmlsoap.org/wsdl/}types":
		assert type_node is None
		type_node = e
	else:
		l0.append(e)
		e.getparent().remove(e)

l0.sort(key=lambda e: (wsdl_order[e.tag], e.attrib['name']))
for e in l0:
	tree.getroot().append(e)

for e in tree.getroot():
	if e.tag in ("{http://schemas.xmlsoap.org/wsdl/}portType", 
				 "{http://schemas.xmlsoap.org/wsdl/}binding"):
		nodes = []
		for p in e.getchildren():
			nodes.append(p)

		nodes.sort(key=lambda e: e.attrib.get('name','0'))

		for p in nodes:
			e.append(p)


schemas = []

for e in type_node:
	schemas.append(e)
	e.getparent().remove(e)

schemas.sort(key=lambda e: e.attrib["targetNamespace"])

for s in schemas:
	type_node.append(s)

for s in schemas:
	nodes = []
	for e in s:
		nodes.append(e)
		e.getparent().remove(e)
		#print e, e.tag, e.attrib
	#print
	nodes.sort(key=lambda e: (schema_order[e.tag],))

	for e in nodes:
		s.append(e)

print etree.tostring(tree)
