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

from lxml import etree

from datetime import datetime

from spyne.model import DateTime
from spyne.model import Unicode
from spyne.model import Integer
from spyne.model import ComplexModel
from spyne.interface.xml_schema.parser import hier_repr

from spyne.util.xml import get_schema_documents
from spyne.util.xml import get_object_as_xml
from spyne.util.xml import get_xml_as_object
from spyne.util.xml import parse_schema_string


# Define the object
class SomeObject(ComplexModel):
    i = Integer
    s = Unicode
    d = DateTime
    __repr__ = hier_repr

# Instantiate the object
instance = SomeObject(i=5, s="str", d=datetime.now())

# Generate schema documents
schema_elts = get_schema_documents([SomeObject], 'some_ns')

# Serialize the xml schema document for object
schema = etree.tostring(schema_elts['tns'],  pretty_print=True)

# Serialize the object to XML
instance_elt = get_object_as_xml(instance, SomeObject)

# Serialize the element tree to string
data = etree.tostring(instance_elt, pretty_print=True)

print(instance)
print()
print(schema)
print(data)

# parse the schema document
parsed_schema = parse_schema_string(schema)['some_ns']

# Get SomeObject definition from the parsed schema document
NewObject = parsed_schema.types['SomeObject']

# We print an empty instance just to see the parsed fields.
print(NewObject())

# Deserialize the xml document using the definition from the schema.
new_instance = get_xml_as_object(etree.fromstring(data), NewObject)

print(new_instance)

assert new_instance.s == instance.s
assert new_instance.i == instance.i
assert new_instance.d == instance.d