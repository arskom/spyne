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

from __future__ import absolute_import, print_function

from lxml import etree

from spyne import ComplexModel, Unicode, Integer, Array
from spyne.util.xml import get_object_as_xml_polymorphic


NS = "https://spyne.io/examples/polymorphism"


class Vehicle(ComplexModel):
    __namespace__ = NS
    _type_info = [
        ('owner', Unicode),
    ]


class Car(Vehicle):
    __namespace__ = NS
    _type_info = [
        ('color', Unicode),
        ('speed', Integer),
    ]


class Bike(Vehicle):
    __namespace__ = NS
    _type_info = [
        ('size', Integer),
    ]


class Garage(ComplexModel):
    __namespace__ = NS
    _type_info = [
        ('vehicles', Array(Vehicle)),
    ]


garage = Garage(
    vehicles=[
        Car(
            color="blue",
            speed=100,
            owner="Simba"
        ),
        Bike(
            size=58,
            owner="Nala"
        ),
    ]
)

elt = get_object_as_xml_polymorphic(garage)
print(etree.tostring(elt, pretty_print=True))

# Output:
""" 
<tns:Garage xmlns:tns="https://spyne.io/examples/polymorphism" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <tns:vehicles>
    <tns:Vehicle xsi:type="tns:Car">
      <tns:owner>Simba</tns:owner>
      <tns:color>blue</tns:color>
      <tns:speed>100</tns:speed>
    </tns:Vehicle>
    <tns:Vehicle xsi:type="tns:Bike">
      <tns:owner>Nala</tns:owner>
      <tns:size>58</tns:size>
    </tns:Vehicle>
  </tns:vehicles>
</tns:Garage>
"""
