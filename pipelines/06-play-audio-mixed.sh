# see https://gstreamer.freedesktop.org/data/doc/gstreamer/head/gst-plugins-base-plugins/html/gst-plugins-base-plugins-audiomixer.html

# gst-launch-1.0 audiotestsrc freq=100 \
#     ! audiomixer name=mix \
#     ! audioconvert \
#     ! autoaudiosink \
#     audiotestsrc freq=500 \
#     ! mix.

# gst-launch-1.0 audiomixer name=mix \
#   mix. ! audioconvert ! audioresample ! autoaudiosink \
#   audiotestsrc num-buffers=400 volume=0.2 ! mix. \
#   audiotestsrc num-buffers=300 volume=0.2 freq=880 timestamp-offset=1000000000 ! mix. \
#   audiotestsrc num-buffers=100 volume=0.2 freq=660 timestamp-offset=2000000000 ! mix. \

# gst-launch-1.0 audiomixer name=mix \
#   mix. ! audioconvert ! audioresample ! autoaudiosink \
#   filesrc location=../media/wave.mp4 ! decodebin ! audioresample ! mix. \
#   audiotestsrc num-buffers=300 volume=0.2 freq=880 timestamp-offset=1000000000 ! mix. \
#   audiotestsrc num-buffers=100 volume=0.2 freq=660 timestamp-offset=2000000000 ! mix. \

gst-launch-1.0 \
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
    filesrc location=../media/rocket.mp4 \
    ! decodebin \
    ! audioresample \
    ! mixer.
