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


"""
This is a simple HelloWorld example showing how the NullServer works. The
NullServer is meant to be used mainly for testing.
"""


from spyne import Application, rpc, ServiceBase, Iterable, Integer, Unicode
from spyne.protocol.soap import Soap11
from spyne.server.null import NullServer


class HelloWorldService(ServiceBase):
    @rpc(Unicode, Integer, _returns=Iterable(Unicode))
    def say_hello(ctx, name, times):
        for i in range(times):
            yield u'Hello, %s' % name


application = Application([HelloWorldService], 'spyne.examples.hello.soap',
            in_protocol=Soap11(validator='lxml'),
            out_protocol=Soap11(pretty_print=True),
        )


if __name__ == '__main__':
    import logging
    from pprint import pprint

    logging.basicConfig(level=logging.INFO)

    # mutes context markers. set logging level to logging.INFO to enable
    # them.
    logging.getLogger('spyne.server.null').setLevel(logging.CRITICAL)

    print("With serialization")
    print("==================")
    print()

    null = NullServer(application, ostr=True)
    ret_stream = null.service.say_hello('Dave', 5)
    ret_string = ''.join(ret_stream)
    print(ret_string)
    print()

    print("Without serialization")
    print("=====================")
    print()

    null = NullServer(application, ostr=False)
    ret = null.service.say_hello('Dave', 5)

    # because the return value is a generator, we need to iterate over it to
    # see the actual return values.
    pprint(list(ret))
