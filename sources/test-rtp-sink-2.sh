# GST_DEBUG_DUMP_DOT_DIR=. \
gst-launch-1.0 -v \
    rtpbin name=rtpbin \
    udpsrc \
        caps="application/x-rtp,media=video,clock-rate=90000,encoding-name=VP8,payload=101" \
        port=5100 \
        address=127.0.0.1 \
    ! rtpbin.recv_rtp_sink_0 \
    udpsrc \
        port=5101 \
        address=127.0.0.1 \
    ! rtpbin.recv_rtcp_sink_0 \
    rtpbin.send_rtcp_src_0 \
    ! udpsink port=6100 \
        sync=false \
        async=false \
    rtpbin. \
    ! rtpvp8depay \
    ! vp8dec \
    ! videoconvert \
    ! autovideosink \
    udpsrc \
        caps="application/x-rtp,media=audio,clock-rate=48000,encoding-name=OPUS,payload=100" \
        port=5102 \
        address=127.0.0.1 \
    ! rtpbin.recv_rtp_sink_1 \
    udpsrc \
        port=5103 \
        address=127.0.0.1 \
    ! rtpbin.recv_rtcp_sink_1 \
    rtpbin.send_rtcp_src_1 \
    ! udpsink port=6101 \
        sync=false \
        async=false \
    rtpbin. \
    ! rtpopusdepay \
    ! opusdec \
    ! audioconvert \
    ! autoaudiosink
