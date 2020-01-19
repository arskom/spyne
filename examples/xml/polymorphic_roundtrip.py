#!/usr/bin/env python3

from __future__ import print_function, unicode_literals

import sys

from lxml import etree
from spyne.interface.xml_schema.parser import hier_repr

from spyne.util import six
from spyne import ComplexModel, Unicode
from spyne.util.xml import get_object_as_xml_polymorphic, \
    get_xml_as_object_polymorphic


# uncomment to see what's going on under the hood
# import logging
# logging.basicConfig(level=logging.DEBUG,
#     format='%(levelname)-7s %(module)12s:%(lineno)-4d | %(message)s')


class B(ComplexModel):
    __namespace__ = 'some_ns'
    _type_info = {
        '_b': Unicode,
    }

    def __init__(self):
        super(B, self).__init__()
        self._b = "b"


class C(B):
    __namespace__ = 'some_ns'
    _type_info = {
        '_c': Unicode,
    }

    def __init__(self):
        super(C, self).__init__()
        self._c = "c"


class A(ComplexModel):
    __namespace__ = 'some_ns'
    _type_info = {
        '_a': Unicode,
        '_b': B,
    }

    def __init__(self, b=None):
        super(A, self).__init__()
        self._a = 'a'
        self._b = b


a = A(b=C())
elt = get_object_as_xml_polymorphic(a, A)
xml_string = etree.tostring(elt, pretty_print=True)
if six.PY2:
    print(xml_string, end="")
else:
    sys.stdout.buffer.write(xml_string)

element_tree = etree.fromstring(xml_string)
new_a = get_xml_as_object_polymorphic(elt, A)

assert new_a._a == a._a, (a._a, new_a._a)
assert new_a._b._b == a._b._b, (a._b._b, new_a._b._b)
assert new_a._b._c == a._b._c, (a._b._c, new_a._b._c)

print(hier_repr(new_a))
