# see https://gstreamer.freedesktop.org/data/doc/gstreamer/head/gst-plugins-good-plugins/html/gst-plugins-good-plugins-videomixer.html

gst-launch-1.0 \
    videomixer \
        name=mixer \
        background=black \
        sink_0::alpha=1 sink_0::zorder=0 \
        sink_1::alpha=1 sink_1::zorder=1 sink_1::xpos=1420 sink_1::ypos=105 \
        sink_2::alpha=1 sink_2::zorder=2 sink_2::xpos=1420 sink_2::ypos=395 \
        sink_3::alpha=1 sink_3::zorder=3 sink_3::xpos=1420 sink_3::ypos=685 \
    ! autovideosink \
    filesrc location=../media/wave.mp4 \
    ! decodebin \
    ! videoconvert \
    ! videoscale \
    ! video/x-raw,width=1920,height=1080 \
    ! timeoverlay \
    ! queue \
    ! mixer. \
    filesrc location=../media/montreal.mp4 \
    ! decodebin \
    ! videoconvert \
    ! videoscale \
    ! video/x-raw,width=480,height=270 \
    ! timeoverlay \
    ! queue \
    ! mixer. \
    filesrc location=../media/tube.mp4 \
    ! decodebin \
    ! videoconvert \
    ! videoscale \
    ! video/x-raw,width=480,height=270 \
    ! timeoverlay \
    ! queue \
    ! mixer. \
    filesrc location=../media/rocket.mp4 \
    ! decodebin \
    ! videoconvert \
    ! videoscale \
    ! video/x-raw,width=480,height=270 \
    ! timeoverlay \
    ! queue \
    ! mixer.
