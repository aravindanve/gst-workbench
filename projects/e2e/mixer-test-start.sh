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
        location=../../media/lava.mkv \
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
    ! rtpbin.send_rtp_sink_1 &

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
        location=../../media/montreal.mkv \
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
    ! rtpbin.send_rtp_sink_1 &

gst-launch-1.0 -v \
    rtpbin name=rtpbin \
    udpsrc \
        caps="application/x-rtp,media=video,clock-rate=90000,encoding-name=H264,payload=101" \
        port=4000 \
        address=127.0.0.1 \
    ! rtpbin.recv_rtp_sink_0 \
    udpsrc \
        port=4001 \
        address=127.0.0.1 \
    ! rtpbin.recv_rtcp_sink_0 \
    rtpbin.send_rtcp_src_0 \
    ! udpsink port=3000 \
        sync=false \
        async=false \
    rtpbin. \
    ! rtph264depay \
    ! avdec_h264 \
    ! videoconvert \
    ! autovideosink \
    udpsrc \
        caps="application/x-rtp,media=audio,clock-rate=48000,encoding-name=OPUS,payload=100" \
        port=4002 \
        address=127.0.0.1 \
    ! rtpbin.recv_rtp_sink_1 \
    udpsrc \
        port=4003 \
        address=127.0.0.1 \
    ! rtpbin.recv_rtcp_sink_1 \
    rtpbin.send_rtcp_src_1 \
    ! udpsink port=3001 \
        sync=false \
        async=false \
    rtpbin. \
    ! rtpopusdepay \
    ! opusdec \
    ! audioconvert \
    ! autoaudiosink &

./mixer.py &
