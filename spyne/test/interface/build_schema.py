#!/usr/bin/env python

# This can be used to debug invalid Xml Schema documents.

import sys

from lxml import etree

if len(sys.argv) != 2:
    print "Usage: %s <path_to_xsd_file>" % sys.argv[0]
    sys.exit(1)

f = open(sys.argv[1])

etree.XMLSchema(etree.parse(f))
