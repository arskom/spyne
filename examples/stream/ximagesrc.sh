#!/bin/bash
# quick way to test gstreamer pipeline

gst-launch-0.10 ximagesrc ! video/x-raw-rgb,framerate=2/1 ! ffmpegcolorspace \
    ! theoraenc quality=32 ! oggmux name=mux ! filesink location=streamfile.ogg
