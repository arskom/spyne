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
import time

from twisted.python import log

from spyne.application import Application
from spyne.decorator import srpc
from spyne.protocol.http import HttpRpc
from spyne.protocol.xml import XmlObject
from spyne.service import ServiceBase
from spyne.model.primitive import Integer

host = '127.0.0.1'
port = 9752

class SomeService(ServiceBase):
    @srpc(Integer)
    def block(seconds):
        """Blocks the reactor for given number of seconds."""
        time.sleep(seconds)

def initialize():
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger('spyne.protocol.xml').setLevel(logging.DEBUG)

    observer = log.PythonLoggingObserver('twisted')
    log.startLoggingWithObserver(observer.emit, setStdout=False)


    application = Application([SomeService], 'spyne.examples.hello.twisted',
                                in_protocol=HttpRpc(), out_protocol=XmlObject())

    application.interface.nsmap[None] = application.interface.nsmap['tns']
    application.interface.prefmap[application.interface.nsmap['tns']] = None
    del application.interface.nsmap['tns']

    return application
