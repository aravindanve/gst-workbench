# clean up
rm ../dots/*

# GST_DEBUG_DUMP_DOT_DIR=../dots gst-launch-1.0 -v \
#     autovideosrc \
#     ! videoscale \
#     ! videoconvert \
#     ! timeoverlay \
#     ! video/x-raw,format=I420,width=1280,height=720,framerate=\(fraction\)30000/1000 \
#     ! queue \
#     ! autovideosink

# gst-launch-1.0 -v \
#     videomixer \
#         name=mixer \
#         background=black \
#         sink_0::alpha=1 sink_0::zorder=0 \
#         sink_1::alpha=1 sink_1::zorder=1 sink_1::xpos=1420 sink_1::ypos=105 \
#         sink_2::alpha=1 sink_2::zorder=2 sink_2::xpos=1420 sink_2::ypos=395 \
#         sink_3::alpha=1 sink_3::zorder=3 sink_3::xpos=1420 sink_3::ypos=685 \
#     ! autovideosink \
#     videotestsrc is-live=true \
#         pattern=pinwheel \
#     ! videoconvert \
#     ! video/x-raw,format=I420,width=854,height=480,framerate=\(fraction\)30000/1000 \
#     ! mixer. \
#     videotestsrc is-live=true \
#         pattern=ball \
#         background-color=1 \
#     ! videoconvert \
#     ! video/x-raw,format=I420,width=854,height=480,framerate=\(fraction\)30000/1000 \
#     ! mixer.

## WARNING: from element /GstPipeline:pipeline0/GstAutoVideoSink:autovideosink0/GstGLImageSinkBin:autovideosink0-actual-sink-glimage/GstGLImageSink:sink: A lot of buffers are being dropped.
## Additional debug info:
## gstbasesink.c(2902): gboolean gst_base_sink_is_too_late(GstBaseSink *, GstMiniObject *, GstClockTime, GstClockTime, GstClockReturn, GstClockTimeDiff, gboolean) (): /GstPipeline:pipeline0/GstAutoVideoSink:autovideosink0/GstGLImageSinkBin:autovideosink0-actual-sink-glimage/GstGLImageSink:sink:
## There may be a timestamping problem, or this computer is too slow.
# gst-launch-1.0 -v \
#     videomixer \
#         name=mixer \
#         background=black \
#         sink_0::alpha=1 sink_0::zorder=0 \
#         sink_1::alpha=1 sink_1::zorder=1 sink_1::xpos=1420 sink_1::ypos=105 \
#         sink_2::alpha=1 sink_2::zorder=2 sink_2::xpos=1420 sink_2::ypos=395 \
#         sink_3::alpha=1 sink_3::zorder=3 sink_3::xpos=1420 sink_3::ypos=685 \
#     ! autovideosink \
#     videotestsrc is-live=true \
#         pattern=pinwheel \
#     ! videoconvert \
#     ! video/x-raw,format=I420,width=1280,height=720,framerate=\(fraction\)30000/1000 \
#     ! mixer. \
#     videotestsrc is-live=true \
#         pattern=ball \
#         background-color=1 \
#     ! videoconvert \
#     ! video/x-raw,format=I420,width=854,height=480,framerate=\(fraction\)30000/1000 \
#     ! mixer.

# gst-launch-1.0 -v \
#     autovideosrc num-buffers=50 is-live=true \
#     ! videoscale \
#     ! videoconvert \
#     ! timeoverlay \
#     ! video/x-raw,format=I420,width=1280,height=720,framerate=\(fraction\)30000/1000 \
#     ! queue \
#     ! videomixer background=black \
#     ! x264enc \
#     ! mpegtsmux name=muxer \
#     ! filesink location=../outputs/14.ts \

GST_DEBUG_DUMP_DOT_DIR=../dots gst-launch-1.0 -v \
    mpegtsmux name=muxer \
    ! filesink location=../outputs/14-captured-mpegts.ts \
    audiomixer name=amixer \
    ! audioresample \
    ! faac \
    ! muxer. \
    videomixer \
        name=vmixer \
        background=black \
        sink_0::alpha=1 sink_0::zorder=0 \
        sink_1::alpha=1 sink_1::zorder=1 sink_1::xpos=910 sink_1::ypos=50 \
        sink_2::alpha=1 sink_2::zorder=2 sink_2::xpos=910 sink_2::ypos=260 \
        sink_3::alpha=1 sink_3::zorder=3 sink_3::xpos=910 sink_3::ypos=470 \
    ! x264enc \
    ! muxer. \
    autovideosrc is-live=true \
    ! videoscale \
    ! videoconvert \
    ! timeoverlay \
    ! video/x-raw,format=I420,width=1280,height=720,framerate=\(fraction\)30000/1000 \
    ! queue \
    ! vmixer. \
    filesrc location=../media/wave.mp4 \
    ! decodebin name=decoder_1 \
    decoder_1. \
    ! queue \
    ! audioresample \
    ! amixer. \
    decoder_1. \
    ! queue \
    ! videorate \
    ! video/x-raw,framerate=\(fraction\)30000/1001 \
    ! videoconvert \
    ! video/x-raw,format=I420 \
    ! videoscale \
    ! video/x-raw,width=356,height=200 \
    ! timeoverlay \
    ! vmixer. \
    filesrc location=../media/tube.mp4 \
    ! decodebin name=decoder_2 \
    decoder_2. \
    ! queue \
    ! audioresample \
    ! amixer. \
    decoder_2. \
    ! queue \
    ! videorate \
    ! video/x-raw,framerate=\(fraction\)30000/1001 \
    ! videoconvert \
    ! video/x-raw,format=I420 \
    ! videoscale \
    ! video/x-raw,width=356,height=200 \
    ! timeoverlay \
    ! vmixer. \
    filesrc location=../media/lava.webm \
    ! decodebin name=decoder_3 \
    decoder_3. \
    ! queue \
    ! audioresample \
    ! amixer. \
    decoder_3. \
    ! queue \
    ! videorate \
    ! video/x-raw,framerate=\(fraction\)30000/1001 \
    ! videoconvert \
    ! video/x-raw,format=I420 \
    ! videoscale \
    ! video/x-raw,width=356,height=200 \
    ! timeoverlay \
    ! vmixer.
