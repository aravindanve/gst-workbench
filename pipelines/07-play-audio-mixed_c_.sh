# see https://gstreamer.freedesktop.org/data/doc/gstreamer/head/gst-plugins-base-plugins/html/gst-plugins-base-plugins-audiomixer.html

gst-launch-1.0 -v \
    audiomixer name=mixer \
    ! autoaudiosink \
    filesrc location=../media/wave.mp4 \
    ! decodebin \
    ! audioresample \
    ! mixer. \
    filesrc location=../media/montreal.mp4 \
    ! decodebin \
    ! audioresample \
    ! mixer. \
    filesrc location=../media/tube.mp4 \
    ! decodebin \
    ! audioresample \
    ! mixer. \
    filesrc location=../media/lava.webm \
    ! decodebin \
    ! audioresample \
    ! mixer.
