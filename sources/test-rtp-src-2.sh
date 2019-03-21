gst-launch-1.0 -v \
    rtpbin name=rtpbin \
    rtpbin.send_rtp_src_0 \
    ! udpsink host=127.0.0.1 port=5100 \
    rtpbin.send_rtcp_src_0 \
    ! udpsink host=127.0.0.1 port=5101 sync=false async=false \
    udpsrc host=127.0.0.1 port=5102 \
    ! rtpbin.recv_rtcp_sink_0 \
    rtpbin.send_rtp_src_1 \
    ! udpsink host=127.0.0.1 port=5110 \
    rtpbin.send_rtcp_src_1 \
    ! udpsink host=127.0.0.1 port=5111 sync=false async=false \
    udpsrc host=127.0.0.1 port=5112 \
    ! rtpbin.recv_rtcp_sink_1 \
    autovideosrc \
    ! videoscale \
    ! videoconvert \
    ! timeoverlay \
    ! video/x-raw,width=640,height=360 \
    ! x264enc \
    ! rtph264pay \
    ! rtpbin.send_rtp_sink_0 \
    multifilesrc \
        location=../media/wave.mp4 \
        loop=true \
    ! decodebin \
    ! audio/x-raw \
    ! audioconvert \
    ! opusenc \
    ! rtpopuspay \
    ! rtpbin.send_rtp_sink_1
