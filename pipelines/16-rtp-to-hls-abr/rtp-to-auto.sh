# clean up
rm ../../dots/*

# gst-launch-1.0 -v udpsrc address=127.0.0.1 port=5000 ! fakesink dump=1

# GST_DEBUG_DUMP_DOT_DIR=../../dots GST_DEBUG=3,*rtp*:6 gst-launch-1.0 \
#     udpsrc \
#         caps=application/x-rtp,media=video,clock-rate=90000,encoding-name=VP8,payload=101 \
#         address=127.0.0.1 \
#         port=5000 \
#     ! .recv_rtp_sink_0 rtpbin \
#     ! rtpvp8depay \
#     ! vp8dec \
#     ! autovideosink

GST_DEBUG_DUMP_DOT_DIR=../../dots GST_DEBUG=3,*rtp*:6 gst-launch-1.0 \
    input-selector name=selector_0 \
    ! autovideosink \
    videotestsrc \
        pattern=snow \
    ! selector_0. \
    udpsrc \
        caps=application/x-rtp,media=video,clock-rate=90000,encoding-name=VP8,payload=101 \
        address=127.0.0.1 \
        port=5000 \
    ! .recv_rtp_sink_0 rtpbin \
    ! rtpvp8depay \
    ! vp8dec \
    ! selector_0.

# gst-launch-1.0 \
#     audiomixer name=amixer \
#     ! autoaudiosink \
#     videomixer name=vmixer \
#         background=black \
#         sink_1::alpha=1 sink_0::zorder=1 sink_0::xpos=0 sink_0::ypos=180 \
#         sink_2::alpha=1 sink_1::zorder=2 sink_1::xpos=640 sink_1::ypos=180 \
#     ! video/x-raw,width=1280,height=720 \
#     ! autovideosink \
#     filesrc location=../../media/montreal.mp4 \
#     ! decodebin name=decoder_0 \
#     decoder_0. \
#     ! queue \
#     ! audioresample \
#     ! amixer. \
#     decoder_0. \
#     ! queue \
#     ! videorate \
#     ! video/x-raw,framerate=\(fraction\)30000/1001 \
#     ! videoconvert \
#     ! video/x-raw,format=I420 \
#     ! videoscale \
#     ! video/x-raw,width=640,height=360 \
#     ! timeoverlay \
#     ! vmixer. \
#     filesrc location=../../media/wave.mp4 \
#     ! decodebin name=decoder_1 \
#     decoder_1. \
#     ! queue \
#     ! audioresample \
#     ! amixer. \
#     decoder_1. \
#     ! queue \
#     ! videorate \
#     ! video/x-raw,framerate=\(fraction\)30000/1001 \
#     ! videoconvert \
#     ! video/x-raw,format=I420 \
#     ! videoscale \
#     ! video/x-raw,width=640,height=360 \
#     ! timeoverlay \
#     ! vmixer.
