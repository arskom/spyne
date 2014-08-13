#!/usr/bin/env python
# encoding: utf8
#
# Copyright © Burak Arslan <burak at arskom dot com dot tr>,
#             Arskom Ltd. http://www.arskom.com.tr
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#    1. Redistributions of source code must retain the above copyright notice,
#       this list of conditions and the following disclaimer.
#    2. Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#    3. Neither the name of the owner nor the names of its contributors may be
#       used to endorse or promote products derived from this software without
#       specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER BE LIABLE FOR ANY DIRECT,
# INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY
# OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE,
# EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#


import logging
logging.basicConfig(level=logging.DEBUG)

import uuid

from datetime import datetime
from pprint import pprint

from lxml import etree

from spyne.model.primitive import Uuid
from spyne.model.primitive import Unicode
from spyne.model.primitive import String
from spyne.model.primitive import Integer
from spyne.model.primitive import Decimal
from spyne.model.primitive import DateTime
from spyne.model.complex import XmlData
from spyne.model.complex import ComplexModel
from spyne.model.complex import XmlAttribute

from spyne.util.xml import get_schema_documents
from spyne.util.xml import get_object_as_xml
from spyne.util.xml import get_xml_as_object
from spyne.util.xml import get_validation_schema


class Punk(ComplexModel):
    __namespace__ = 'some_namespace'

    a = String
    b = Integer
    c = Decimal
    d = DateTime


class Foo(ComplexModel):
    __namespace__ = 'some_other_namespace'

    a = String
    b = Integer
    c = Decimal
    d = DateTime
    e = XmlAttribute(Integer)
    f = XmlAttribute(Unicode, attribute_of='d')


class ProductEdition(ComplexModel):
    __namespace__ = 'kickass_namespace'

    id = XmlAttribute(Uuid)
    name = XmlData(Unicode)


class Product(ComplexModel):
    __namespace__ = 'kickass_namespace'

    id = XmlAttribute(Uuid)
    edition = ProductEdition


docs = get_schema_documents([Punk, Foo, Product])
pprint(docs)
print()

pprint({k: v.attrib['targetNamespace'] for k,v in docs.items()})

# the default ns prefix is always tns
print("the default namespace %r:" % docs['tns'].attrib['targetNamespace'])
print(etree.tostring(docs['tns'], pretty_print=True))
print()

# Namespace prefixes are assigned like s0, s1, s2, etc...
print("the other namespace %r:" % docs['s0'].attrib['targetNamespace'])
print(etree.tostring(docs['s0'], pretty_print=True))
print()

print("the other namespace %r:" % docs['s2'].attrib['targetNamespace'])
print(etree.tostring(docs['s2'], pretty_print=True))
print()

# Object serialization and deserialization
foo = Foo(a='a', b=1, c=3.4, d=datetime(2011, 02, 20), e=5, f='f')
doc = get_object_as_xml(foo, Foo)
print(etree.tostring(doc, pretty_print=True))
print(get_xml_as_object(doc, Foo))
print()

# XmlData example.
print("Product output (illustrates XmlData):")
product = Product(id=uuid.uuid4(), edition=ProductEdition(id=uuid.uuid4(),
                                                             name='My edition'))
print(etree.tostring(get_object_as_xml(product, Product), pretty_print=True))

# See http://lxml.de/validation.html to see what this could be used for.
print(get_validation_schema([Punk, Foo]))
