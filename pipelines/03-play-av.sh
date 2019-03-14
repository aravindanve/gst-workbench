gst-launch-1.0 filesrc location=../media/lava.webm ! decodebin name=decoder \
    decoder. ! queue ! videoconvert ! autovideosink \
    decoder. ! queue ! audioconvert ! autoaudiosink
