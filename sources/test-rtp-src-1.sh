gst-launch-1.0 -v \
    rtpbin name=rtpbin \
        latency=2000 \
    rtpbin.send_rtp_src_0 \
    ! udpsink host=127.0.0.1 port=5000 \
    rtpbin.send_rtcp_src_0 \
    ! udpsink host=127.0.0.1 port=5001 sync=false async=false \
    udpsrc address=127.0.0.1 port=5002 \
    ! rtpbin.recv_rtcp_sink_0 \
    rtpbin.send_rtp_src_1 \
    ! udpsink host=127.0.0.1 port=5010 \
    rtpbin.send_rtcp_src_1 \
    ! udpsink host=127.0.0.1 port=5011 sync=false async=false \
    udpsrc address=127.0.0.1 port=5012 \
    ! rtpbin.recv_rtcp_sink_1 \
    autovideosrc \
    ! videoscale \
    ! videoconvert \
    ! timeoverlay \
    ! video/x-raw,width=640,height=360 \
    ! vp8enc \
    ! rtpvp8pay \
    ! application/x-rtp,clock-rate=90000,payload=101 \
    ! rtpbin.send_rtp_sink_0 \
    multifilesrc \
        location=../media/montreal.mp4 \
        loop=true \
    ! decodebin \
    ! audio/x-raw \
    ! audioconvert \
    ! opusenc \
    ! rtpopuspay \
    ! application/x-rtp,clock-rate=48000,payload=100 \
    ! rtpbin.send_rtp_sink_1
