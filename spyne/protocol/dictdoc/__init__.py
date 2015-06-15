
#
# spyne - Copyright (C) Spyne contributors.
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301
#

"""The ``spyne.protocol.dictdoc`` module contains an abstract
protocol that deals with hierarchical and flat dicts as {in,out}_documents.

Flattening
==========

Plain HTTP does not support hierarchical key-value stores. Spyne makes plain
HTTP fake hierarchical dicts with two small hacks.

Let's look at the following object hierarchy: ::

    class Inner(ComplexModel):
        c = Integer
        d = Array(Integer)

    class Outer(ComplexModel):
        a = Integer
        b = Inner

For example, the ``Outer(a=1, b=Inner(c=2))`` object would correspond to the
following hierarchichal dict representation: ::

    {'a': 1, 'b': { 'c': 2 }}

Here's what we do to deserialize the above object structure from a flat dict:

1. Object hierarchies are flattened. e.g. the flat representation of the above
   dict is: ``{'a': 1, 'b.c': 2}``.
2. Arrays of objects are sent using variables with array indexes in square
   brackets. So the request with the following query object: ::

      {'a': 1, 'b.d[0]': 1, 'b.d[1]': 2}}

  ... corresponds to: ::

      {'a': 1, 'b': { 'd': [1,2] }}

  If we had: ::

      class Inner(ComplexModel):
          c = Integer

      class Outer(ComplexModel):
          a = Integer
          b = Array(SomeObject)

  Or the following object: ::

      {'a': 1, 'b[0].c': 1, 'b[1].c': 2}}

  ... would correspond to: ::

      {'a': 1, 'b': [{ 'c': 1}, {'c': 2}]}

  ... which would deserialize as: ::

      Outer(a=1, b=[Inner(c=1), Inner(c=2)])

These hacks are both slower to process and bulkier on wire, so use class
hierarchies with HTTP only when performance is not that much of a concern.

Cookies
=======

Cookie headers are parsed and fields within HTTP requests are assigned to
fields in the ``in_header`` class, if defined.

It's also possible to get the ``Cookie`` header intact by defining an
``in_header`` object with a field named ``Cookie`` (case sensitive).

As an example, let's assume the following HTTP request: ::

    GET / HTTP/1.0
    Cookie: v1=4;v2=8
    (...)

The keys ``v1`` and ``v2`` are passed to the instance of the ``in_header``
class if it has fields named ``v1`` or ``v2``\.

Wrappers
========

Wrapper objects are an artifact of the Xml world, which don't really make sense
in other protocols. Let's look at the following object: ::

    v = Permission(application='app', feature='f1'),

Here's how it would be serialized to XML: ::

    <Permission>
      <application>app</application>
      <feature>f1</feature>
    </Permission>

With ``ignore_wrappers=True`` (which is the default) This gets serialized to
dict as follows: ::

    {
        "application": "app",
        "feature": "f1"
    }

When ``ignore_wrappers=False``, the same value/type combination would result in
the following dict: ::

    {"Permission": {
        {
            "application": "app",
            "feature": "f1"
        }
    },

This could come in handy in case you don't know what type to expect.
"""

from spyne.protocol.dictdoc._base import DictDocument
from spyne.protocol.dictdoc.hier import HierDictDocument
from spyne.protocol.dictdoc.simple import SimpleDictDocument
