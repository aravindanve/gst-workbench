# see https://gstreamer.freedesktop.org/data/doc/gstreamer/head/gst-plugins-good-plugins/html/gst-plugins-good-plugins-videomixer.html
# see https://gstreamer.freedesktop.org/data/doc/gstreamer/head/gst-plugins-base-plugins/html/gst-plugins-base-plugins-audiomixer.html

# clean up
rm -rf ../outputs/11-hls/
mkdir -p ../outputs/11-hls/

# launch
gst-launch-1.0 -v \
    mpegtsmux name=muxer `# mpegtsmux or hlssink does not work properly video is not sink_0` \
    ! hlssink \
        location=../outputs/11-hls/chunk%05d.ts \
        max-files=16 \
        playlist-length=8 \
        playlist-location=../outputs/11-hls/playlist.m3u8 \
        target-duration=2 \
    videomixer name=vmixer \
        background=black \
        sink_0::alpha=1 sink_0::zorder=0 \
        sink_1::alpha=1 sink_1::zorder=1 sink_1::xpos=1420 sink_1::ypos=105 \
        sink_2::alpha=1 sink_2::zorder=2 sink_2::xpos=1420 sink_2::ypos=395 \
        sink_3::alpha=1 sink_3::zorder=3 sink_3::xpos=1420 sink_3::ypos=685 \
    ! x264enc \
    ! video/x-h264,profile=high \
    ! muxer. \
    audiomixer name=amixer \
    ! audioresample \
    ! faac \
    ! muxer. \
    filesrc location=../media/montreal.mp4 \
    ! decodebin name=decoder_0 \
    decoder_0. \
    ! queue \
    ! audioresample \
    ! amixer. \
    decoder_0. \
    ! queue \
    ! videorate \
    ! video/x-raw,framerate=\(fraction\)30000/1001 \
    ! videoconvert \
    ! video/x-raw,format=I420 \
    ! videoscale \
    ! video/x-raw,width=1920,height=1080 \
    ! timeoverlay \
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
    ! video/x-raw,width=480,height=270 \
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
    ! video/x-raw,width=480,height=270 \
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
    ! video/x-raw,width=480,height=270 \
    ! timeoverlay \
    ! vmixer.
