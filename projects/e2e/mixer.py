#!/usr/bin/env python3

import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
from threading import Timer, Lock

class Mixer:
    pass

class Stream:
    pass

class UnsupportedException(Exception):
    pass

def debug_graph(gstbin, filename):
    f = open('%s.dot' % filename, 'w')
    f.write(Gst.debug_bin_to_dot_data(gstbin, Gst.DebugGraphDetails.ALL))
    f.close()

def do_mixer_init(**kwargs):
    mixer = Mixer()

    mixer.debug = kwargs.get('debug', False)

    mixer.disposed = False
    mixer.lock = Lock()

    mixer.session_count = 0
    mixer.streams = {}
    mixer.video_streams = {}
    mixer.audio_streams = {}

    mixer.last_resize_video_streams_count = 0

    mixer.pipeline = Gst.Pipeline('mixer')

    mixer.video_format = kwargs.get('video_format') or 'I420'
    mixer.video_framerate = kwargs.get('video_framerate') or '30/1'
    mixer.video_width = kwargs.get('video_width') or 1280
    mixer.video_height = kwargs.get('video_height') or 720
    mixer.videocaps = Gst.caps_from_string(
        'video/x-raw,format=%s,framerate=%s,width=%s,height=%s' % (
            mixer.video_format, mixer.video_framerate, mixer.video_width, mixer.video_height))

    mixer.audio_format = kwargs.get('audio_format') or 'F32LE'
    mixer.audio_rate = kwargs.get('audio_rate') or 44100
    mixer.audio_channels = kwargs.get('audio_channels') or 2
    mixer.audio_layout = kwargs.get('audio_layout') or 'interleaved'
    mixer.audiocaps = Gst.caps_from_string(
        'audio/x-raw,format=%s,rate=%s,channels=%s,layout=%s' % (
            mixer.audio_format, mixer.audio_rate, mixer.audio_channels, mixer.audio_layout))

    mixer.recv_rtpbin = Gst.ElementFactory.make('rtpbin', 'recv_rtpbin')
    mixer.recv_rtpbin.set_property('autoremove', True)
    mixer.recv_rtpbin.set_property('drop-on-latency', True)
    mixer.pipeline.add(mixer.recv_rtpbin)

    default_pattern = kwargs.get('default_pattern') or 'black'
    mixer.videosrc = Gst.ElementFactory.make('videotestsrc', 'videosrc')
    mixer.videosrc.set_property('is-live', True)
    mixer.videosrc.set_property('pattern', default_pattern)
    mixer.pipeline.add(mixer.videosrc)

    mixer.videosrc_capsfilter = Gst.ElementFactory.make('capsfilter', 'videosrc_capsfilter')
    mixer.videosrc_capsfilter.set_property('caps', mixer.videocaps)
    mixer.pipeline.add(mixer.videosrc_capsfilter)

    mixer.videosrc.link(mixer.videosrc_capsfilter)

    default_wave = kwargs.get('default_wave') or 'silence'
    default_volume = kwargs.get('default_volume') or 0.02
    mixer.audiosrc = Gst.ElementFactory.make('audiotestsrc', 'audiosrc')
    mixer.audiosrc.set_property('is-live', True)
    mixer.audiosrc.set_property('wave', default_wave)
    mixer.audiosrc.set_property('volume', default_volume)
    mixer.pipeline.add(mixer.audiosrc)

    mixer.audiosrc_capsfilter = Gst.ElementFactory.make('capsfilter', 'audiosrc_capsfilter')
    mixer.audiosrc_capsfilter.set_property('caps', mixer.audiocaps)
    mixer.pipeline.add(mixer.audiosrc_capsfilter)

    mixer.audiosrc.link(mixer.audiosrc_capsfilter)

    background = kwargs.get('background') or 'black'
    mixer.videomixer = Gst.ElementFactory.make('videomixer', 'videomixer')
    mixer.videomixer.set_property('background', background)
    mixer.pipeline.add(mixer.videomixer)

    videosrc_capsfilter_srcpad = mixer.videosrc_capsfilter.get_static_pad('src')
    videomixer_sinkpad = mixer.videomixer.get_request_pad('sink_0')
    videosrc_capsfilter_srcpad.link(videomixer_sinkpad)

    mixer.videomixer_capsfilter = Gst.ElementFactory.make('capsfilter', 'videomixer_capsfilter')
    mixer.videomixer_capsfilter.set_property('caps', mixer.videocaps)
    mixer.pipeline.add(mixer.videomixer_capsfilter)

    mixer.videomixer.link(mixer.videomixer_capsfilter)

    mixer.audiomixer = Gst.ElementFactory.make('audiomixer', 'audiomixer')
    mixer.pipeline.add(mixer.audiomixer)

    audiosrc_capsfilter_srcpad = mixer.audiosrc_capsfilter.get_static_pad('src')
    audiomixer_sinkpad = mixer.audiomixer.get_request_pad('sink_0')
    audiosrc_capsfilter_srcpad.link(audiomixer_sinkpad)

    mixer.audiomixer_capsfilter = Gst.ElementFactory.make('capsfilter', 'audiomixer_capsfilter')
    mixer.audiomixer_capsfilter.set_property('caps', mixer.audiocaps)
    mixer.pipeline.add(mixer.audiomixer_capsfilter)

    mixer.audiomixer.link(mixer.audiomixer_capsfilter)

    mixer.multiqueue = Gst.ElementFactory.make('multiqueue', 'multiqueue')
    mixer.pipeline.add(mixer.multiqueue)

    videomixer_capsfilter_srcpad = mixer.videomixer_capsfilter.get_static_pad('src')
    multiqueue_sinkpad_0 = mixer.multiqueue.get_request_pad('sink_0')
    videomixer_capsfilter_srcpad.link(multiqueue_sinkpad_0)

    audiomixer_capsfilter_srcpad = mixer.audiomixer_capsfilter.get_static_pad('src')
    multiqueue_sinkpad_1 = mixer.multiqueue.get_request_pad('sink_1')
    audiomixer_capsfilter_srcpad.link(multiqueue_sinkpad_1)

    # FIXME: replace autovideosink with rtpsink
    mixer.videosink = Gst.ElementFactory.make('autovideosink', 'videosink')
    mixer.pipeline.add(mixer.videosink)

    multiqueue_srcpad_0 = mixer.multiqueue.get_static_pad('src_0')
    videosink_sinkpad = mixer.videosink.get_static_pad('sink')
    multiqueue_srcpad_0.link(videosink_sinkpad)

    # FIXME: replace autoaudiosink with rtpsink
    mixer.audiosink = Gst.ElementFactory.make('autoaudiosink', 'audiosink')
    mixer.pipeline.add(mixer.audiosink)

    multiqueue_srcpad_1 = mixer.multiqueue.get_static_pad('src_1')
    audiosink_sinkpad = mixer.audiosink.get_static_pad('sink')
    multiqueue_srcpad_1.link(audiosink_sinkpad)

    mixer.recv_rtpbin.connect('pad-added', _on_mixer_recv_rtpbin_pad_added, mixer)
    mixer.recv_rtpbin.connect('pad-added', _on_mixer_recv_rtpbin_pad_removed, mixer)

    mixer.pipeline.set_state(Gst.State.PAUSED)

    _do_mtunsafe_resize_video_streams(mixer)

    mixer.debug and debug_graph(mixer.pipeline, 'debug_mixer_init')

    return mixer

def do_mixer_start(mixer):
    mixer.pipeline.set_state(Gst.State.PLAYING)

    mixer.debug and debug_graph(mixer.pipeline, 'debug_mixer_start')

def do_mixer_stop(mixer):
    mixer.pipeline.set_state(Gst.State.PAUSED)

    mixer.debug and debug_graph(mixer.pipeline, 'debug_mixer_stop')

def do_mixer_dispose(mixer):
    mixer.pipeline.set_state(Gst.State.NULL)
    mixer.disposed = True

def do_mixer_stream_init(mixer, **kwargs):
    stream = Stream()

    stream.debug = kwargs.get('debug', mixer.debug)

    stream.disposed = False

    stream.media = kwargs.get('media') or 'video'
    stream.clock_rate = kwargs.get('clock_rate') or 90000
    stream.encoding_name = kwargs.get('encoding_name') or 'VP8'
    stream.payload = kwargs.get('payload') or 101

    if stream.media != 'video' and stream.media != 'audio':
        stream.disposed = True
        raise UnsupportedException('Unsupported media: %s' % media)

    if stream.media == 'video' and stream.encoding_name not in ['VP8', 'H264']:
        stream.disposed = True
        raise UnsupportedException('Unsupported %s encoding: %s' % (stream.media, stream.encoding_name))

    if stream.media == 'audio' and stream.encoding_name not in ['OPUS']:
        stream.disposed = True
        raise UnsupportedException('Unsupported %s encoding: %s' % (stream.media, stream.encoding_name))

    with mixer.lock:
        if stream.media == 'video':
            if len(mixer.video_streams) >= 4:
                stream.disposed = True
                raise UnsupportedException('Maximum of 4 video streams supported')
            else:
                mixer.streams[mixer.session_count] = stream
                mixer.video_streams[mixer.session_count] = stream

        elif stream.media == 'audio':
            if len(mixer.audio_streams) >= 6:
                stream.disposed = True
                raise UnsupportedException('Maximum of 6 audio streams supported')
            else:
                mixer.streams[mixer.session_count] = stream
                mixer.audio_streams[mixer.session_count] = stream

        stream.mixer = mixer
        stream.session = mixer.session_count
        stream.name = 'stream_%s' % stream.session

        mixer.session_count += 1

    stream.caps = Gst.caps_from_string(
        'application/x-rtp,media=%s,clock-rate=%s,encoding-name=%s,payload=%s' % (
            stream.media, stream.clock_rate, stream.encoding_name, stream.payload))

    stream.rtpdecodebin = Gst.Bin('%s_rtpdecodebin' % stream.name)

    if stream.encoding_name == 'VP8':
        stream.rtpdecodebin.depay = Gst.ElementFactory.make('rtpvp8depay', 'depay')
        stream.rtpdecodebin.dec = Gst.ElementFactory.make('vp8dec', 'dec')

    elif stream.encoding_name == 'H264':
        stream.rtpdecodebin.depay = Gst.ElementFactory.make('rtph264depay', 'depay')
        stream.rtpdecodebin.dec = Gst.ElementFactory.make('avdec_h264', 'dec')

    elif stream.encoding_name == 'OPUS':
        stream.rtpdecodebin.depay = Gst.ElementFactory.make('rtpopusdepay', 'depay')
        stream.rtpdecodebin.dec = Gst.ElementFactory.make('opusdec', 'dec')

    stream.rtpdecodebin.add(stream.rtpdecodebin.depay)
    stream.rtpdecodebin.add(stream.rtpdecodebin.dec)

    stream.rtpdecodebin.depay.link(stream.rtpdecodebin.dec)

    if stream.media == 'video':
        stream.rtpdecodebin.videorate = Gst.ElementFactory.make('videorate', 'videorate')
        stream.rtpdecodebin.add(stream.rtpdecodebin.videorate)

        stream.rtpdecodebin.videoconvert = Gst.ElementFactory.make('videoconvert', 'videoconvert')
        stream.rtpdecodebin.add(stream.rtpdecodebin.videoconvert)

        stream.rtpdecodebin.videoscale = Gst.ElementFactory.make('videoscale', 'videoscale')
        stream.rtpdecodebin.add(stream.rtpdecodebin.videoscale)

        stream.rtpdecodebin.capsfilter = Gst.ElementFactory.make('capsfilter', 'capsfilter')
        stream.rtpdecodebin.capsfilter.set_property('caps', mixer.videocaps)
        stream.rtpdecodebin.add(stream.rtpdecodebin.capsfilter)

        stream.rtpdecodebin.dec.link(stream.rtpdecodebin.videorate)
        stream.rtpdecodebin.videorate.link(stream.rtpdecodebin.videoconvert)
        stream.rtpdecodebin.videoconvert.link(stream.rtpdecodebin.videoscale)
        stream.rtpdecodebin.videoscale.link(stream.rtpdecodebin.capsfilter)

    elif stream.media == 'audio':
        stream.rtpdecodebin.audiorate = Gst.ElementFactory.make('audiorate', 'audiorate')
        stream.rtpdecodebin.add(stream.rtpdecodebin.audiorate)

        stream.rtpdecodebin.audioconvert = Gst.ElementFactory.make('audioconvert', 'audioconvert')
        stream.rtpdecodebin.add(stream.rtpdecodebin.audioconvert)

        stream.rtpdecodebin.audioresample = Gst.ElementFactory.make('audioresample', 'audioresample')
        stream.rtpdecodebin.add(stream.rtpdecodebin.audioresample)

        stream.rtpdecodebin.capsfilter = Gst.ElementFactory.make('capsfilter', 'capsfilter')
        stream.rtpdecodebin.capsfilter.set_property('caps', mixer.audiocaps)
        stream.rtpdecodebin.add(stream.rtpdecodebin.capsfilter)

        stream.rtpdecodebin.dec.link(stream.rtpdecodebin.audiorate)
        stream.rtpdecodebin.audiorate.link(stream.rtpdecodebin.audioconvert)
        stream.rtpdecodebin.audioconvert.link(stream.rtpdecodebin.audioresample)
        stream.rtpdecodebin.audioresample.link(stream.rtpdecodebin.capsfilter)

    sinkpad = stream.rtpdecodebin.depay.get_static_pad('sink')
    stream.rtpdecodebin.gsinkpad = Gst.GhostPad('sink', sinkpad)
    stream.rtpdecodebin.add_pad(stream.rtpdecodebin.gsinkpad)

    srcpad = stream.rtpdecodebin.capsfilter.get_static_pad('src')
    stream.rtpdecodebin.gsrcpad = Gst.GhostPad('src', srcpad)
    stream.rtpdecodebin.add_pad(stream.rtpdecodebin.gsrcpad)

    stream.rtpdecodebin.set_locked_state(True)
    stream.rtpdecodebin.set_state(Gst.State.PAUSED)
    mixer.pipeline.add(stream.rtpdecodebin)

    stream.remote_ip = kwargs.get('remote_ip') or '127.0.0.1'
    stream.remote_port = kwargs.get('remote_port') or 6000
    stream.rtcpsink = Gst.ElementFactory.make('udpsink', '%s_rtcpsink' % stream.name)
    stream.rtcpsink.set_property('port', stream.remote_port)
    stream.rtcpsink.set_property('host', stream.remote_ip)
    stream.rtcpsink.set_property('async', False)
    stream.rtcpsink.set_property('sync', False)

    mixer.pipeline.add(stream.rtcpsink)

    rtcpsink_sinkpad = stream.rtcpsink.get_static_pad('sink')
    recv_rtpbin_rtcp_srcpad = mixer.recv_rtpbin.get_request_pad('send_rtcp_src_%s' % stream.session)
    recv_rtpbin_rtcp_srcpad.link(rtcpsink_sinkpad)

    stream.rtcpsink.sync_state_with_parent()

    stream.rtpsrcbin = Gst.Bin('%s_rtpsrcbin' % stream.name)

    stream.local_ip = kwargs.get('local_ip') or '127.0.0.1'
    stream.local_port = kwargs.get('local_port') or 5000
    stream.rtpsrcbin.rtpsrc = Gst.ElementFactory.make('udpsrc', '%s_rtpsrc' % stream.name)
    stream.rtpsrcbin.rtpsrc.set_property('port', stream.local_port)
    stream.rtpsrcbin.rtpsrc.set_property('address', stream.local_ip)
    stream.rtpsrcbin.rtpsrc.set_property('caps', stream.caps)
    stream.rtpsrcbin.add(stream.rtpsrcbin.rtpsrc)

    stream.rtpsrcbin.rtcpsrc = Gst.ElementFactory.make('udpsrc', '%s_rtcpsrc' % stream.name)
    stream.rtpsrcbin.rtcpsrc.set_property('port', stream.local_port + 1) # FIXME: use rtcp-mux
    stream.rtpsrcbin.rtcpsrc.set_property('address', stream.local_ip)
    stream.rtpsrcbin.add(stream.rtpsrcbin.rtcpsrc)

    mixer.pipeline.add(stream.rtpsrcbin)

    rtpsrc_srcpad = stream.rtpsrcbin.rtpsrc.get_static_pad('src')
    stream.rtpsrcbin.rtp_gsrcpad = Gst.GhostPad('rtp_src', rtpsrc_srcpad)
    stream.rtpsrcbin.add_pad(stream.rtpsrcbin.rtp_gsrcpad)

    recv_rtpbin_rtp_sinkpad = mixer.recv_rtpbin.get_request_pad('recv_rtp_sink_%s' % stream.session)
    stream.rtpsrcbin.rtp_gsrcpad.link(recv_rtpbin_rtp_sinkpad)

    rtcpsrc_srcpad = stream.rtpsrcbin.rtcpsrc.get_static_pad('src')
    stream.rtpsrcbin.rtcp_gsrcpad = Gst.GhostPad('rtcp_src', rtcpsrc_srcpad)
    stream.rtpsrcbin.add_pad(stream.rtpsrcbin.rtcp_gsrcpad)

    recv_rtpbin_rtcp_sinkpad = mixer.recv_rtpbin.get_request_pad('recv_rtcp_sink_%s' % stream.session)
    stream.rtpsrcbin.rtcp_gsrcpad.link(recv_rtpbin_rtcp_sinkpad)

    stream.rtpsrcbin.sync_state_with_parent()

    stream.debug and debug_graph(mixer.pipeline, 'debug_mixer_stream_%s_init' % stream.session)

    return stream

def do_mixer_stream_dispose(mixer, stream):
    with mixer.lock:
        _do_mtunsafe_unlink_rtpbin_from_rtpdecodebin(stream)
        _do_mtunsafe_unlink_rtpdecodebin_from_avmixer(mixer, stream)

        if stream.media == 'video':
            _do_mtunsafe_resize_video_streams(mixer)

        if stream.media == 'video':
            mixer.streams.pop(mixer.session_count, None)
            mixer.video_streams.pop(mixer.session_count, None)

        elif stream.media == 'audio':
            mixer.streams.pop(mixer.session_count, None)
            mixer.audio_streams.pop(mixer.session_count, None)

    stream.rtpsrcbin.set_state(Gst.State.NULL)
    mixer.pipeline.remove(stream.rtpsrcbin)

    stream.rtpdecodebin.set_state(Gst.State.NULL)
    mixer.pipeline.remove(stream.rtpdecodebin)

    stream.rtcpsink.set_state(Gst.State.NULL)
    mixer.pipeline.remove(stream.rtcpsink)

    stream.caps = None
    stream.rtpsrcbin = None
    stream.rtpdecodebin = None
    stream.rtcpsink = None
    stream.disposed = True

    stream.debug and debug_graph(mixer.pipeline, 'debug_mixer_stream_%s_dispose' % stream.session)

def _do_mtunsafe_link_rtpbin_to_rtpdecodebin(stream, rtpbin_srcpad):
    rtpdecodebin_sinkpad = stream.rtpdecodebin.get_static_pad('sink')

    if rtpdecodebin_sinkpad.is_linked():
        peerpad = rtpdecodebin_sinkpad.get_peer()
        peerpad.set_active(False)
        peerpad.unlink(rtpdecodebin_sinkpad)

    rtpbin_srcpad.link(rtpdecodebin_sinkpad)

def _do_mtunsafe_unlink_rtpbin_from_rtpdecodebin(stream):
    rtpdecodebin_sinkpad = stream.rtpdecodebin.get_static_pad('sink')

    if rtpdecodebin_sinkpad.is_linked():
        peerpad = rtpdecodebin_sinkpad.get_peer()
        peerpad.set_active(False)
        peerpad.unlink(rtpdecodebin_sinkpad)

def _do_mtunsafe_link_rtpdecodebin_to_avmixer(mixer, stream):
    rtpdecodebin_srcpad = stream.rtpdecodebin.get_static_pad('src')

    if not rtpdecodebin_srcpad.is_linked():
        if stream.media == 'video':
            videosrc_capsfilter_srcpad = mixer.videosrc_capsfilter.get_static_pad('src')

            if videosrc_capsfilter_srcpad.is_linked():
                videosrc_srcpad = mixer.videosrc.get_static_pad('src')
                videomixer_sinkpad = videosrc_capsfilter_srcpad.get_peer()
                mixer.videosrc.set_locked_state(True)
                videosrc_srcpad.set_active(False)
                videosrc_capsfilter_srcpad.unlink(videomixer_sinkpad)

            else:
                videomixer_sinkpad_template = mixer.videomixer.get_pad_template('sink_%u')
                videomixer_sinkpad = mixer.videomixer.request_pad(sinkpad_template, None, None)

            rtpdecodebin_srcpad.link(videomixer_sinkpad)

        elif stream.media == 'audio':
            audiosrc_capsfilter_srcpad = mixer.audiosrc_capsfilter.get_static_pad('src')

            if audiosrc_capsfilter_srcpad.is_linked():
                audiosrc_srcpad = mixer.audiosrc.get_static_pad('src')
                audiomixer_sinkpad = audiosrc_capsfilter_srcpad.get_peer()
                mixer.audiosrc.set_locked_state(True)
                audiosrc_srcpad.set_active(False)
                audiosrc_capsfilter_srcpad.unlink(audiomixer_sinkpad)

            else:
                audiomixer_sinkpad_template = mixer.audiomixer.get_pad_template('sink_%u')
                audiomixer_sinkpad = mixer.audiomixer.request_pad(sinkpad_template, None, None)

            rtpdecodebin_srcpad.link(audiomixer_sinkpad)

def _do_mtunsafe_unlink_rtpdecodebin_from_avmixer(mixer, stream):
    rtpdecodebin_srcpad = stream.rtpdecodebin.get_static_pad('src')

    if rtpdecodebin_srcpad.is_linked():
        avmixer_sinkpad = rtpdecodebin_srcpad.get_peer()
        avmixer = avmixer_sinkpad.get_parent_element()
        avmixer_sinkpad.set_active(False)
        rtpdecodebin_srcpad.unlink(avmixer_sinkpad)

        if stream.media == 'video':
            if len(avmixer.sinkpads) > 1:
                avmixer.remove_pad(avmixer_sinkpad)

            else:
                videosrc_srcpad = mixer.videosrc.get_static_pad('src')
                videosrc_capsfilter_srcpad = mixer.videosrc_capsfilter.get_static_pad('src')
                videosrc_capsfilter_srcpad.link(avmixer_sinkpad)
                mixer.videosrc.set_locked_state(False)
                videosrc_srcpad.set_active(True)
                mixer.videosrc.sync_state_with_parent()
                mixer.videosrc_capsfilter.sync_state_with_parent()
                avmixer_sinkpad.set_active(True)
                avmixer.sync_state_with_parent()

        elif stream.media == 'audio':
            avmixer.remove_pad(avmixer_sinkpad)

            if not len(avmixer.sinkpads):
                audiosrc_srcpad = mixer.audiosrc.get_static_pad('src')
                audiosrc_capsfilter_srcpad = mixer.audiosrc_capsfilter.get_static_pad('src')
                audiomixer_sinkpad = mixer.audiomixer.get_request_pad('sink_0')
                audiosrc_capsfilter_srcpad.link(audiomixer_sinkpad)
                mixer.audiosrc.set_locked_state(False)
                audiosrc_srcpad.set_active(True)
                mixer.audiosrc.sync_state_with_parent()
                mixer.audiosrc_capsfilter.sync_state_with_parent()

def _do_mtunsafe_resize_video_streams(mixer):
    video_streams_count = len(mixer.videomixer.sinkpads)
    if mixer.last_resize_video_streams_count != video_streams_count:
        if video_streams_count > 1:
            width = mixer.video_width / 2
            height = mixer.video_height / 2

        else:
            width = mixer.video_width
            height = mixer.video_height

        caps = Gst.caps_from_string(
            'video/x-raw,format=%s,framerate=%s,width=%s,height=%s' % (
                mixer.video_format, mixer.video_framerate, width, height))

        index = 0
        for sinkpad in mixer.videomixer.sinkpads:
            peerpad = sinkpad.get_peer()

            if not peerpad:
                continue

            if hasattr(peerpad, 'get_target'):
                capsfilter = peerpad.get_target().get_parent_element()
            else:
                capsfilter = peerpad.get_parent_element()

            capsfilter.set_property('caps', caps)

            if index == 0 or index == 2:
                sinkpad.set_property('xpos', 0)
            elif index == 1 or index == 3:
                sinkpad.set_property('xpos', width)

            if index == 0 or index == 1:
                sinkpad.set_property('ypos', 0)
            elif index == 2 or index == 3:
                sinkpad.set_property('ypos', height)

            index += 1

        mixer.last_resize_video_streams_count = index + 1

def _on_mixer_recv_rtpbin_pad_added(rtpbin, srcpad, mixer):
    name_args = srcpad.get_name().split('_')
    if len(name_args) != 6: return

    mixer.debug and print('_on_mixer_recv_rtpbin_pad_added', srcpad.get_name())

    # name_args format:
    # [0: 'send' or 'recv', 1: 'rtp' or 'rtcp', 2: 'src' or 'sink', 3: SESSION, 4: SSRC, 5: PAYLOAD]
    # e.g. recv_rtp_src_0_367391323_101

    session = int(name_args[3])

    with mixer.lock:
        stream = mixer.streams[session]

        if not stream:
            print('ERROR: stream %s not found', session)
            return

        _do_mtunsafe_link_rtpbin_to_rtpdecodebin(stream, srcpad)
        _do_mtunsafe_link_rtpdecodebin_to_avmixer(mixer, stream)

        if stream.media == 'video':
            _do_mtunsafe_resize_video_streams(mixer)

    stream.debug and debug_graph(mixer.pipeline, 'debug_mixer_stream_%s_start' % session)

def _on_mixer_recv_rtpbin_pad_removed(rtpbin, srcpad, mixer):
    name_args = srcpad.get_name().split('_')
    if len(name_args) != 6: return

    mixer.debug and print('_on_mixer_recv_rtpbin_pad_removed', srcpad.get_name())

    # name_args format:
    # [0: 'send' or 'recv', 1: 'rtp' or 'rtcp', 2: 'src' or 'sink', 3: SESSION, 4: SSRC, 5: PAYLOAD]
    # e.g. recv_rtp_src_0_367391323_101

    with mixer.lock:
        # unlink stream
        pass

if __name__ == '__main__':
    Gst.init(None)
    Gst.debug_set_active(True)
    Gst.debug_set_default_threshold(Gst.DebugLevel.FIXME)
    mixer = do_mixer_init(debug=True, default_pattern='snow', default_wave='red-noise')

    stream_0 = None
    stream_1 = None
    stream_2 = None
    stream_3 = None

    def do_mixer_stream_init_0():
        global mixer
        global stream_0

        stream_0 = do_mixer_stream_init(mixer,
            media='video',
            clock_rate=90000,
            encoding_name='VP8',
            payload=101,
            local_port=5000,
            remote_port=6000)

    def do_mixer_stream_dispose_0():
        global mixer
        global stream_0

        # Gst.debug_set_default_threshold(Gst.DebugLevel.INFO)
        print('stream_0', stream_0)
        do_mixer_stream_dispose(mixer, stream_0)

    def do_mixer_stream_init_1():
        global mixer
        global stream_1

        stream_1 = do_mixer_stream_init(mixer,
            media='audio',
            clock_rate=48000,
            encoding_name='OPUS',
            payload=100,
            local_port=5002,
            remote_port=6001)

    def do_mixer_stream_dispose_1():
        global mixer
        global stream_1

        print('stream_1', stream_1)
        do_mixer_stream_dispose(mixer, stream_1)

    def do_mixer_stream_init_2():
        global mixer
        global stream_2

        stream_2 = do_mixer_stream_init(mixer,
            media='video',
            clock_rate=90000,
            encoding_name='VP8',
            payload=101,
            local_port=5000,
            remote_port=6000)

    def do_mixer_stream_dispose_2():
        global mixer
        global stream_2

        print('stream_2', stream_2)
        do_mixer_stream_dispose(mixer, stream_2)

    def do_mixer_stream_init_3():
        global mixer
        global stream_3

        stream_3 = do_mixer_stream_init(mixer,
            media='audio',
            clock_rate=48000,
            encoding_name='OPUS',
            payload=100,
            local_port=5002,
            remote_port=6001)

    def do_mixer_stream_dispose_3():
        global mixer
        global stream_3

        print('stream_3', stream_3)
        do_mixer_stream_dispose(mixer, stream_3)

    Timer(0, do_mixer_start, args=[mixer]).start()
    Timer(2, do_mixer_stream_init_0).start()
    Timer(2, do_mixer_stream_init_1).start()
    Timer(10, do_mixer_stream_dispose_0).start()
    Timer(10, do_mixer_stream_dispose_1).start()
    Timer(15, debug_graph, args=[mixer.pipeline, 'debug_final']).start()

    GLib.MainLoop().run()
