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
Raw socket client example for MessagePackDocument via MessagePack server.
"""

from __future__ import print_function, absolute_import

# These are analogues from spyne.server.msgpack. What's IN_REQUEST there is
# OUT_REQUEST here because an outgoing request from a client's perspective is an
# incoming request from a server's perspective.
IN_RESPONSE_NO_ERROR = 0
IN_RESPONSE_CLIENT_ERROR = 1
IN_RESPONSE_SERVER_ERROR = 2

OUT_REQUEST = 1


import socket
import msgpack

from spyne.util.six import BytesIO

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(("localhost", 5550))

request_document = {"say_hello": ["Dave", 5]}

# Because the server's input protocol is MessagePackDocument, we serialize the
# request document to msgpack bytestream.
request_bytestream = msgpack.packb(request_document)

# Because our server side transport is msgpack, we put the request bytestream
# inside another MessagePack document.
request_wrapper_document = [OUT_REQUEST, request_bytestream]

# and we serialize the request wrapper document to msgpack bytestream as well
request_wrapper_bytestream = msgpack.packb(request_wrapper_document)

# Some numbers to show how efficient this is:
print("Raw message length:", len(request_bytestream))
print("Wrapped message length:", len(request_wrapper_bytestream))
print("Overhead:", len(request_wrapper_bytestream) - len(request_bytestream),
      "byte(s).")

# which we push to the socket.
s.sendall(request_wrapper_bytestream)

# This is straight from Python example in msgpack.org
in_buffer = msgpack.Unpacker()

while True:
    # We wait for the full message to arrive.
    in_buffer.feed(s.recv(1))

    # Again, straight from the Python example in MessagePack homepage.
    for msg in in_buffer:
        print("Raw response document:", msg)

        # There should be only one entry in the response dict. We ignore the
        # rest here but we could whine about invalid response just as well.
        resp_code, data = iter(msg.items()).next()

        # We finally parse the response. We should probably do a dict lookup
        # here.
        if resp_code == IN_RESPONSE_NO_ERROR:
            print("Success. Response: ", msgpack.unpackb(data))
            # now that we have the response in a structured format, we could
            # further deserialize it to a Python object, depending on our needs.

        elif resp_code == IN_RESPONSE_CLIENT_ERROR:
            print("Invalid Request. Details: ", msgpack.unpackb(data))

        elif resp_code == IN_RESPONSE_SERVER_ERROR:
            print("Internal Error. Details: ", msgpack.unpackb(data))

        else:
            print("Unknown response. Update the client. Additional data:", data)

        # As we only sent one request, we must break after
        # receiving its response.
        break
    else:
        continue

    break  # break after receiving one message. See above for why.
