# see https://gstreamer.freedesktop.org/data/doc/gstreamer/head/gst-plugins-good-plugins/html/gst-plugins-good-plugins-videomixer.html
# see https://gstreamer.freedesktop.org/data/doc/gstreamer/head/gst-plugins-base-plugins/html/gst-plugins-base-plugins-audiomixer.html

# NOTE: takes nearly 5-6s to encode chunks of 2s each

# clean up
rm -rf ../outputs/15-captured-hls-abr/
rm ../dots/*

# create output dirs
mkdir -p ../outputs/15-captured-hls-abr/160p/
mkdir -p ../outputs/15-captured-hls-abr/240p/
mkdir -p ../outputs/15-captured-hls-abr/360p/
mkdir -p ../outputs/15-captured-hls-abr/480p/
mkdir -p ../outputs/15-captured-hls-abr/720p/

# create master playlist
cat << EOF >> ../outputs/15-captured-hls-abr/master.m3u8
#EXTM3U
#EXT-X-VERSION:3
#EXT-X-STREAM-INF:BANDWIDTH=437500,RESOLUTION=284x160
160p/playlist.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=875000,RESOLUTION=426x240
240p/playlist.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=1750000,RESOLUTION=640x360
360p/playlist.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=2625000,RESOLUTION=854x480
480p/playlist.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=5250000,RESOLUTION=1280x720
720p/playlist.m3u8
EOF

# launch
GST_DEBUG_DUMP_DOT_DIR=../dots gst-launch-1.0 -v \
    mpegtsmux name=muxer160 `# mpegtsmux or hlssink does not work properly video is not sink_0` \
    ! hlssink \
        location=../outputs/15-captured-hls-abr/160p/chunk%05d.ts \
        max-files=16 \
        playlist-length=8 \
        playlist-location=../outputs/15-captured-hls-abr/160p/playlist.m3u8 \
        target-duration=2 \
    mpegtsmux name=muxer240 `# mpegtsmux or hlssink does not work properly video is not sink_0` \
    ! hlssink \
        location=../outputs/15-captured-hls-abr/240p/chunk%05d.ts \
        max-files=16 \
        playlist-length=8 \
        playlist-location=../outputs/15-captured-hls-abr/240p/playlist.m3u8 \
        target-duration=2 \
    mpegtsmux name=muxer360 `# mpegtsmux or hlssink does not work properly video is not sink_0` \
    ! hlssink \
        location=../outputs/15-captured-hls-abr/360p/chunk%05d.ts \
        max-files=16 \
        playlist-length=8 \
        playlist-location=../outputs/15-captured-hls-abr/360p/playlist.m3u8 \
        target-duration=2 \
    mpegtsmux name=muxer480 `# mpegtsmux or hlssink does not work properly video is not sink_0` \
    ! hlssink \
        location=../outputs/15-captured-hls-abr/480p/chunk%05d.ts \
        max-files=16 \
        playlist-length=8 \
        playlist-location=../outputs/15-captured-hls-abr/480p/playlist.m3u8 \
        target-duration=2 \
    mpegtsmux name=muxer720 `# mpegtsmux or hlssink does not work properly video is not sink_0` \
    ! hlssink \
        location=../outputs/15-captured-hls-abr/720p/chunk%05d.ts \
        max-files=16 \
        playlist-length=8 \
        playlist-location=../outputs/15-captured-hls-abr/720p/playlist.m3u8 \
        target-duration=2 \
    videoscale name=vscaler160 \
    ! video/x-raw,width=284,height=160 \
    ! x264enc \
        speed-preset=fast \
        vbv-buf-capacity=200 \
        bitrate=100 \
    ! video/x-h264,profile=high \
    ! muxer160. \
    videoscale name=vscaler240 \
    ! video/x-raw,width=426,height=240 \
    ! x264enc \
        speed-preset=fast \
        vbv-buf-capacity=400 \
        bitrate=200 \
    ! video/x-h264,profile=high \
    ! muxer240. \
    videoscale name=vscaler360 \
    ! video/x-raw,width=640,height=360 \
    ! x264enc \
        speed-preset=fast \
        vbv-buf-capacity=800 \
        bitrate=400 \
    ! video/x-h264,profile=high \
    ! muxer360. \
    videoscale name=vscaler480 \
    ! video/x-raw,width=854,height=480 \
    ! x264enc \
        speed-preset=fast \
        vbv-buf-capacity=1600 \
        bitrate=800 \
    ! video/x-h264,profile=high \
    ! muxer480. \
    videoscale name=vscaler720 \
    ! video/x-raw,width=1280,height=720 \
    ! x264enc \
        speed-preset=fast \
        vbv-buf-capacity=2400 \
        bitrate=1200 \
    ! video/x-h264,profile=high \
    ! muxer720. \
    faac name=aencoder64 \
        bitrate=64000 \
    ! tee name=aencoder64t \
    aencoder64t. \
    ! queue \
    ! muxer160. \
    faac name=aencoder96 \
        bitrate=96000 \
    ! tee name=aencoder96t \
    aencoder96t. \
    ! queue \
    ! muxer240. \
    aencoder96t. \
    ! queue \
    ! muxer360. \
    faac name=aencoder128 \
        bitrate=128000 \
    ! tee name=aencoder128t \
    aencoder128t. \
    ! queue \
    ! muxer480. \
    aencoder128t. \
    ! queue \
    ! muxer720. \
    videomixer name=vmixer \
        background=black \
        sink_0::alpha=1 sink_0::zorder=0 \
        sink_1::alpha=1 sink_1::zorder=1 sink_1::xpos=910 sink_1::ypos=50 \
        sink_2::alpha=1 sink_2::zorder=2 sink_2::xpos=910 sink_2::ypos=260 \
        sink_3::alpha=1 sink_3::zorder=3 sink_3::xpos=910 sink_3::ypos=470 \
    ! tee name=vt \
    vt. \
    ! queue \
    ! vscaler160. \
    vt. \
    ! queue \
    ! vscaler240. \
    vt. \
    ! queue \
    ! vscaler360. \
    vt. \
    ! queue \
    ! vscaler480. \
    vt. \
    ! queue \
    ! vscaler720. \
    audiomixer name=amixer \
    ! audioresample \
    ! tee name=at \
    at. \
    ! queue \
    ! aencoder64. \
    at. \
    ! queue \
    ! aencoder96. \
    at. \
    ! queue \
    ! aencoder128. \
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
    ! video/x-raw,framerate=\(fraction\)30000/1000 \
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
    ! video/x-raw,framerate=\(fraction\)30000/1000 \
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
    ! video/x-raw,framerate=\(fraction\)30000/1000 \
    ! videoconvert \
    ! video/x-raw,format=I420 \
    ! videoscale \
    ! video/x-raw,width=480,height=270 \
    ! timeoverlay \
    ! vmixer.
