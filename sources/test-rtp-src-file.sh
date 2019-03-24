# GST_DEBUG_DUMP_DOT_DIR=. \
# gst-launch-1.0 -v \
#     multifilesrc \
#         location=../media/lava.mkv \
#     ! matroskademux name=demux \
#     multiqueue name=q \
#     demux.audio_0 \
#     ! q.sink_0 \
#     demux.video_0 \
#     ! q.sink_1 \
#     q.src_0 \
#     ! opusdec \
#     ! queue \
#     ! audioresample \
#     ! autoaudiosink \
#     q.src_1 \
#     ! vp8dec \
#     ! queue \
#     ! videoconvert \
#     ! autovideosink

# gst-launch-1.0 -v \
#     rtpbin name=rtpbin \
#     rtpbin.send_rtp_src_0 \
#     ! udpsink host=127.0.0.1 port=5000 \
#     rtpbin.send_rtcp_src_0 \
#     ! udpsink host=127.0.0.1 port=5001 sync=false async=false \
#     udpsrc address=127.0.0.1 port=6000 \
#     ! rtpbin.recv_rtcp_sink_0 \
#     rtpbin.send_rtp_src_1 \
#     ! udpsink host=127.0.0.1 port=5002 \
#     rtpbin.send_rtcp_src_1 \
#     ! udpsink host=127.0.0.1 port=5003 sync=false async=false \
#     udpsrc address=127.0.0.1 port=6001 \
#     ! rtpbin.recv_rtcp_sink_1 \
#     multiqueue name=multiq \
#     videotestsrc pattern=snow \
#     ! multiq.sink_0 \
#     audiotestsrc wave=sine \
#     ! multiq.sink_1 \
#     multiq.src_0 \
#     ! queue \
#     ! vp8enc \
#     ! rtpvp8pay \
#     ! application/x-rtp,clock-rate=90000,payload=101 \
#     ! rtpbin.send_rtp_sink_0 \
#     multiq.src_1 \
#     ! queue \
#     ! opusenc \
#     ! rtpopuspay \
#     ! application/x-rtp,clock-rate=48000,payload=100 \
#     ! rtpbin.send_rtp_sink_1

# GST_DEBUG_DUMP_DOT_DIR=. \
gst-launch-1.0 -v \
    rtpbin name=rtpbin \
    rtpbin.send_rtp_src_0 \
    ! udpsink host=127.0.0.1 port=5000 \
    rtpbin.send_rtcp_src_0 \
    ! udpsink host=127.0.0.1 port=5001 sync=false async=false \
    udpsrc address=127.0.0.1 port=6000 \
    ! rtpbin.recv_rtcp_sink_0 \
    rtpbin.send_rtp_src_1 \
    ! udpsink host=127.0.0.1 port=5002 \
    rtpbin.send_rtcp_src_1 \
    ! udpsink host=127.0.0.1 port=5003 sync=false async=false \
    udpsrc address=127.0.0.1 port=6001 \
    ! rtpbin.recv_rtcp_sink_1 \
    multiqueue name=multiq \
    multifilesrc \
        loop=true \
        location=../media/lava.mkv \
    ! matroskademux name=demux \
    demux. \
    ! video/x-vp8,width=1280,height=720,framerate=1000/1,interlace-mode=mixed \
    ! multiq.sink_0 \
    demux. \
    ! audio/x-opus,rate=48000,channels=2,channel-mapping-family=0,stream-count=1,coupled-count=1 \
    ! multiq.sink_1 \
    multiq.src_0 \
    ! queue \
    ! rtpvp8pay \
    ! application/x-rtp,clock-rate=90000,payload=101 \
    ! rtpbin.send_rtp_sink_0 \
    multiq.src_1 \
    ! queue \
    ! rtpopuspay \
    ! application/x-rtp,clock-rate=48000,payload=100 \
    ! rtpbin.send_rtp_sink_1
