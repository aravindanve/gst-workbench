# GST_DEBUG_DUMP_DOT_DIR=. \
gst-launch-1.0 -v \
    rtpbin name=rtpbin \
    rtpbin.send_rtp_src_0 \
    ! udpsink host=127.0.0.1 port=5100 \
    rtpbin.send_rtcp_src_0 \
    ! udpsink host=127.0.0.1 port=5101 sync=false async=false \
    udpsrc address=127.0.0.1 port=6100 \
    ! rtpbin.recv_rtcp_sink_0 \
    rtpbin.send_rtp_src_1 \
    ! udpsink host=127.0.0.1 port=5102 \
    rtpbin.send_rtcp_src_1 \
    ! udpsink host=127.0.0.1 port=5103 sync=false async=false \
    udpsrc address=127.0.0.1 port=6101 \
    ! rtpbin.recv_rtcp_sink_1 \
    multiqueue name=multiq \
    multifilesrc \
        loop=true \
        location=../media/montreal.mkv \
    ! matroskademux name=demux \
    demux. \
    ! video/x-vp8,width=1920,height=1080,framerate=30000/1001,interlace-mode=mixed \
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
