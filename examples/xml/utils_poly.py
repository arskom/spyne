#!/usr/bin/env python

from __future__ import print_function

import sys

from lxml import etree
from spyne.util import six

from spyne import ComplexModel, Unicode
from spyne.util.xml import get_object_as_xml_polymorphic


class B(ComplexModel):
    _type_info = [
        ('_b', Unicode(default="b")),
    ]


class C(B):
    _type_info = [
        ('_c', Unicode(default="c")),
    ]


class A(ComplexModel):
    _type_info = [
        ('a', Unicode(subname="_a")),
        ('b', B.customize(subname="_b")),
    ]


a = A(b=C())
elt = get_object_as_xml_polymorphic(a, A, no_namespace=True)
xml_string = etree.tostring(elt, pretty_print=True)
if six.PY2:
    print(xml_string, end="")
else:
    sys.stdout.buffer.write(xml_string)
