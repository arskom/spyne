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

import multiprocessing
import logging
logger = logging.getLogger('spyne.wsgi')
logger.setLevel(logging.DEBUG)

import gobject
gobject.threads_init()
import gst

import zmq
context = zmq.Context()

from werkzeug.wsgi import DispatcherMiddleware
from werkzeug.exceptions import NotFound
from werkzeug.serving import run_simple

from spyne.application import Application
from spyne.decorator import rpc
from spyne.service import ServiceBase
from spyne.model.binary import ByteArray
from spyne.server.wsgi import WsgiApplication
from spyne.protocol.http import HttpRpc

port = 9000
url = 'stream'
video_device = "/dev/video0"
stream_socket = "tcp://127.0.0.1:5678"
header_socket = "tcp://127.0.0.1:5679"

# Use mplayer tv:// -tv device=/dev/video0 to get the default resolution of your
# webcam and adjust the width and height settings below.

# You need gstreamer, its python bindings and relevant plugins installed as well
# as werkzeug and pyzmq to run this example. easy_install werkzeug and
# easy_install pyzmq or pyzmq-static will install the python packages. refer to
# your distro's documentation on installing gstreamer and friends.

# FIXME: This is most probably a linux-specific example. Users of other
#        operating systems; Patches are welcome!

# FIXME: Does not flush non-keyframe data after sending stream headers like
#        multifdsink does. Patches are welcome!

# FIXME: Does not support audio. I imagine some small tweak to the below gst
#        pipeline would "Just Work". Patches are welcome!

v4l2_pipeline = (
    'v4l2src device=%s '
    '! video/x-raw-yuv '
    '! videoscale ! video/x-raw-yuv, width=400, height=300 '
    '! videorate ! video/x-raw-yuv,framerate=25/2 '
    '! ffmpegcolorspace '
    '! theoraenc quality=32 ! oggmux ! appsink name=sink sync=False' % video_device)

# use this if you want to publish your screen.
xsrc_pipeline = (
    'ximagesrc '
    '! video/x-raw-rgb,framerate=2/1 '
    '! ffmpegcolorspace '
    '! theoraenc quality=32 ! oggmux ! appsink name=sink sync=False' )

def camera_publisher():
    # init gst
    pipeline = gst.parse_launch(v4l2_pipeline)
    pipeline.set_state(gst.STATE_PLAYING)
    appsink = pipeline.get_by_name('sink')
    buffer = appsink.emit('pull-preroll')
    caps = buffer.get_caps()[0]
    stream_header = ""
    if caps.has_field("streamheader"):
        stream_header = ''.join([str(h) for h in caps["streamheader"]])

    # init zeromq
    inner_context = zmq.Context()

    # send stream header to the http daemon
    socket = inner_context.socket(zmq.REP)
    socket.bind(header_socket)
    socket.recv()
    socket.send(str(stream_header))
    socket.close()

    # publish stream
    publisher = inner_context.socket(zmq.PUB)
    publisher.bind(stream_socket)
    while True:
        buf = appsink.emit('pull-buffer')
        publisher.send(str(buf))


class StreamingService(ServiceBase):
    stream_header = ""

    @rpc(_returns=ByteArray)
    def webcam(ctx):
        yield StreamingService.stream_header

        socket = context.socket(zmq.SUB)
        socket.connect(stream_socket)
        socket.setsockopt(zmq.SUBSCRIBE, "")

        while True:
            yield socket.recv()


def main():
    # start publisher process
    p = multiprocessing.Process(target=camera_publisher)
    p.start()

    stream_app = WsgiApplication(Application([StreamingService],
            tns='spyne.examples.stream',
            in_protocol=HttpRpc(),
            out_protocol=HttpRpc(mime_type='video/ogg'),
        ))

    root_app = DispatcherMiddleware(NotFound(), {'/stream': stream_app})

    # get stream header from the publisher process
    socket = context.socket(zmq.REQ)
    socket.connect(header_socket)
    socket.send("hey")
    StreamingService.stream_header = socket.recv()
    socket.close()

    # have fun!
    run_simple('0.0.0.0', port, root_app, static_files={'/':"."}, threaded=True)

if __name__ == '__main__':
    import sys
    sys.exit(main())
