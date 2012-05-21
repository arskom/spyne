#!/bin/bash
# quick way to test gstreamer pipeline

gst-launch-0.10 v4l2src device=/dev/video0 ! video/x-raw-yuv,width=320,height=240 ! videorate ! video/x-raw-yuv,framerate=25/2 \
    ! videoscale ! video/x-raw-yuv,width=320,height=240 ! ffmpegcolorspace \
    ! theoraenc quality=32 ! oggmux name=mux ! filesink location=streamfile.ogg
