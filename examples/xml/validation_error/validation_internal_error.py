#!/usr/bin/env python

from lxml.etree import XMLParser, fromstring, XMLSchema

schema_doc = open('schema.xsd').read()
inst_doc = open('inst.xml').read()

parser = XMLParser(resolve_entities=False)
elt = fromstring(inst_doc, parser)
schema = XMLSchema(fromstring(schema_doc))
schema.validate(elt)
