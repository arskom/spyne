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

from __future__ import absolute_import

import sys

from spyne import ComplexModel, Unicode, Integer, Array, TTableModel, rpc, \
    Application, Service
from spyne.protocol.soap import Soap11
from spyne.server.wsgi import WsgiApplication
from spyne.util.cherry import cherry_graft_and_start

TableModel = TTableModel()


class Vehicle(ComplexModel):
    _type_info = [
        ('owner', Unicode),
    ]


class Car(Vehicle):
    _type_info = [
        ('color', Unicode),
        ('speed', Integer),
    ]


class Bike(Vehicle):
    _type_info = [
        ('size', Integer),
    ]


class Garage(ComplexModel):
    _type_info = [
        ('vehicles', Array(Vehicle)),
    ]


class SomeService(Service):
    @rpc(_returns=Garage)
    def get_garage_dump(self):
        return Garage(
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

application = Application([SomeService], 'tns',
    in_protocol=Soap11(validator='lxml'),
    out_protocol=Soap11(polymorphic=True)
)

sys.exit(cherry_graft_and_start(WsgiApplication(application)))
