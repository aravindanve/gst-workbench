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
    mixer.debug_output = kwargs.get('debug_output', False)

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
    mixer.recv_rtpbin.set_property('autoremove', True) # FIXME: gc not removing elements, only pads are removed
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
    mixer.videomixer = Gst.ElementFactory.make('compositor', 'videomixer')
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

    if mixer.debug_output:
        mixer.videosink = Gst.ElementFactory.make('autovideosink', 'videosink')
        mixer.pipeline.add(mixer.videosink)

        multiqueue_srcpad_0 = mixer.multiqueue.get_static_pad('src_0')
        videosink_sinkpad = mixer.videosink.get_static_pad('sink')
        multiqueue_srcpad_0.link(videosink_sinkpad)

        mixer.audiosink = Gst.ElementFactory.make('autoaudiosink', 'audiosink')
        mixer.pipeline.add(mixer.audiosink)

        multiqueue_srcpad_1 = mixer.multiqueue.get_static_pad('src_1')
        audiosink_sinkpad = mixer.audiosink.get_static_pad('sink')
        multiqueue_srcpad_1.link(audiosink_sinkpad)

    else:
        mixer.video_clock_rate = kwargs.get('clock_rate') or 90000
        mixer.video_encoding_name = kwargs.get('encoding_name') or 'H264'
        mixer.video_payload = kwargs.get('payload') or 101

        mixer.audio_clock_rate = kwargs.get('clock_rate') or 48000
        mixer.audio_encoding_name = kwargs.get('encoding_name') or 'OPUS'
        mixer.audio_payload = kwargs.get('payload') or 100

        if mixer.video_encoding_name not in ['H264']:
            raise UnsupportedException('Unsupported video encoding: %s' % mixer.video_encoding_name)

        if mixer.audio_encoding_name not in ['OPUS']:
            raise UnsupportedException('Unsupported video encoding: %s' % mixer.audio_encoding_name)

        mixer.video_paycaps = Gst.caps_from_string(
            'application/x-rtp,media=video,clock-rate=%s,encoding-name=%s,payload=%s' % (
                mixer.video_clock_rate, mixer.video_encoding_name, mixer.video_payload))

        mixer.audio_paycaps = Gst.caps_from_string(
            'application/x-rtp,media=audio,clock-rate=%s,encoding-name=%s,payload=%s' % (
                mixer.audio_clock_rate, mixer.audio_encoding_name, mixer.audio_payload))

        if mixer.video_encoding_name == 'H264':
            mixer.multiqueue_videocapsfilter = Gst.ElementFactory.make('capsfilter', 'multiqueue_videocapsfilter')
            mixer.multiqueue_videocapsfilter.set_property('caps', mixer.videocaps)
            mixer.pipeline.add(mixer.multiqueue_videocapsfilter)

            multiqueue_srcpad_0 = mixer.multiqueue.get_static_pad('src_0')
            multiqueue_videocapsfilter_sinkpad = mixer.multiqueue_videocapsfilter.get_static_pad('sink')
            multiqueue_srcpad_0.link(multiqueue_videocapsfilter_sinkpad)

            mixer.video_enc = Gst.ElementFactory.make('x264enc', 'video_enc')
            mixer.video_enc.set_property('subme', 1) # fast
            mixer.pipeline.add(mixer.video_enc)

            mixer.multiqueue_videocapsfilter.link(mixer.video_enc)

            mixer.video_enc_capsfilter = Gst.ElementFactory.make('capsfilter', 'video_enc_capsfilter')
            mixer.video_enc_capsfilter.set_property('caps',  Gst.caps_from_string('video/x-h264,profile=high'))
            mixer.pipeline.add(mixer.video_enc_capsfilter)

            mixer.video_enc.link(mixer.video_enc_capsfilter)

            mixer.video_pay = Gst.ElementFactory.make('rtph264pay', 'video_pay')
            mixer.pipeline.add(mixer.video_pay)

            mixer.video_enc_capsfilter.link(mixer.video_pay)

        mixer.video_pay_capsfilter = Gst.ElementFactory.make('capsfilter', 'video_pay_capsfilter')
        mixer.video_pay_capsfilter.set_property('caps',  mixer.video_paycaps)
        mixer.pipeline.add(mixer.video_pay_capsfilter)

        mixer.video_pay.link(mixer.video_pay_capsfilter)

        if mixer.audio_encoding_name == 'OPUS':
            mixer.multiqueue_audiocapsfilter = Gst.ElementFactory.make('capsfilter', 'multiqueue_audiocapsfilter')
            mixer.multiqueue_audiocapsfilter.set_property('caps', mixer.audiocaps)
            mixer.pipeline.add(mixer.multiqueue_audiocapsfilter)

            multiqueue_srcpad_1 = mixer.multiqueue.get_static_pad('src_1')
            multiqueue_audiocapsfilter_sinkpad = mixer.multiqueue_audiocapsfilter.get_static_pad('sink')
            multiqueue_srcpad_1.link(multiqueue_audiocapsfilter_sinkpad)

            mixer.audioconvert = Gst.ElementFactory.make('audioconvert', 'audioconvert')
            mixer.pipeline.add(mixer.audioconvert)

            mixer.multiqueue_audiocapsfilter.link(mixer.audioconvert)

            mixer.audioresample = Gst.ElementFactory.make('audioresample', 'audioresample')
            mixer.pipeline.add(mixer.audioresample)

            mixer.audioconvert.link(mixer.audioresample)

            mixer.audioresample_capsfilter = Gst.ElementFactory.make('capsfilter', 'audioresample_capsfilter')
            mixer.audioresample_capsfilter.set_property('caps',  Gst.caps_from_string(
                'audio/x-raw,format=S16LE,rate=48000,layout=interleaved,channels=%s' % (
                    mixer.audio_channels)))

            mixer.pipeline.add(mixer.audioresample_capsfilter)

            mixer.audioresample.link(mixer.audioresample_capsfilter)

            mixer.audio_enc = Gst.ElementFactory.make('opusenc', 'audio_enc')
            mixer.pipeline.add(mixer.audio_enc)

            mixer.audioresample_capsfilter.link(mixer.audio_enc)

            mixer.audio_enc_capsfilter = Gst.ElementFactory.make('capsfilter', 'audio_enc_capsfilter')
            mixer.audio_enc_capsfilter.set_property('caps',  Gst.caps_from_string('audio/x-opus'))
            mixer.pipeline.add(mixer.audio_enc_capsfilter)

            mixer.audio_enc.link(mixer.audio_enc_capsfilter)

            mixer.audio_pay = Gst.ElementFactory.make('rtpopuspay', 'audio_pay')
            mixer.pipeline.add(mixer.audio_pay)

            mixer.audio_enc_capsfilter.link(mixer.audio_pay)

        mixer.audio_pay_capsfilter = Gst.ElementFactory.make('capsfilter', 'audio_pay_capsfilter')
        mixer.audio_pay_capsfilter.set_property('caps',  mixer.audio_paycaps)
        mixer.pipeline.add(mixer.audio_pay_capsfilter)

        mixer.audio_pay.link(mixer.audio_pay_capsfilter)

        mixer.send_rtpbin = Gst.ElementFactory.make('rtpbin', 'send_rtpbin')
        mixer.send_rtpbin.set_property('drop-on-latency', True)
        mixer.pipeline.add(mixer.send_rtpbin)

        video_pay_capsfilter_srcpad = mixer.video_pay_capsfilter.get_static_pad('src')
        send_rtpbin_rtp_sinkpad_0 = mixer.send_rtpbin.get_request_pad('send_rtp_sink_0')
        video_pay_capsfilter_srcpad.link(send_rtpbin_rtp_sinkpad_0)

        audio_pay_capsfilter_srcpad = mixer.audio_pay_capsfilter.get_static_pad('src')
        send_rtpbin_rtp_sinkpad_1 = mixer.send_rtpbin.get_request_pad('send_rtp_sink_1')
        audio_pay_capsfilter_srcpad.link(send_rtpbin_rtp_sinkpad_1)

        mixer.video_remote_ip = kwargs.get('video_remote_ip') or '127.0.0.1'
        mixer.video_remote_port = kwargs.get('video_remote_port') or 3000
        mixer.send_rtcpsrc_0 = Gst.ElementFactory.make('udpsrc', 'send_rtcp_src_0')
        mixer.send_rtcpsrc_0.set_property('port', mixer.video_remote_port)
        mixer.send_rtcpsrc_0.set_property('address', mixer.video_remote_ip)
        mixer.pipeline.add(mixer.send_rtcpsrc_0)

        send_rtcpsrc_0_srcpad = mixer.send_rtcpsrc_0.get_static_pad('src')
        send_rtpbin_rtcp_sinkpad_0 = mixer.send_rtpbin.get_request_pad('recv_rtcp_sink_0')
        send_rtcpsrc_0_srcpad.link(send_rtpbin_rtcp_sinkpad_0)

        mixer.audio_remote_ip = kwargs.get('audio_remote_ip') or '127.0.0.1'
        mixer.audio_remote_port = kwargs.get('audio_remote_port') or 3001
        mixer.send_rtcpsrc_1 = Gst.ElementFactory.make('udpsrc', 'send_rtcp_src_1')
        mixer.send_rtcpsrc_1.set_property('port', mixer.audio_remote_port)
        mixer.send_rtcpsrc_1.set_property('address', mixer.audio_remote_ip)
        mixer.pipeline.add(mixer.send_rtcpsrc_1)

        send_rtcpsrc_1_srcpad = mixer.send_rtcpsrc_1.get_static_pad('src')
        send_rtpbin_rtcp_sinkpad_1 = mixer.send_rtpbin.get_request_pad('recv_rtcp_sink_1')
        send_rtcpsrc_1_srcpad.link(send_rtpbin_rtcp_sinkpad_1)

        mixer.video_local_ip = kwargs.get('video_local_ip') or '127.0.0.1'
        mixer.video_local_port = kwargs.get('video_local_port') or 4000
        mixer.send_rtpsink_0 = Gst.ElementFactory.make('udpsink', 'send_rtp_sink_0')
        mixer.send_rtpsink_0.set_property('port', mixer.video_local_port)
        mixer.send_rtpsink_0.set_property('host', mixer.video_local_ip)
        mixer.pipeline.add(mixer.send_rtpsink_0)

        mixer.send_rtcpsink_0 = Gst.ElementFactory.make('udpsink', 'send_rtcpsink_0')
        mixer.send_rtcpsink_0.set_property('port', mixer.video_local_port + 1) # FIXME: use rtcp-mux
        mixer.send_rtcpsink_0.set_property('host', mixer.video_local_ip)
        mixer.send_rtcpsink_0.set_property('async', False)
        mixer.send_rtcpsink_0.set_property('sync', False)
        mixer.pipeline.add(mixer.send_rtcpsink_0)

        send_rtpbin_rtp_srcpad_0 = mixer.send_rtpbin.get_static_pad('send_rtp_src_0')
        send_rtpsrc_sinkpad_0 = mixer.send_rtpsink_0.get_static_pad('sink')
        send_rtpbin_rtp_srcpad_0.link(send_rtpsrc_sinkpad_0)

        send_rtpbin_rtcp_srcpad_0 = mixer.send_rtpbin.get_request_pad('send_rtcp_src_0')
        send_rtcpsrc_sinkpad_0 = mixer.send_rtcpsink_0.get_static_pad('sink')
        send_rtpbin_rtcp_srcpad_0.link(send_rtcpsrc_sinkpad_0)

        mixer.audio_local_ip = kwargs.get('audio_local_ip') or '127.0.0.1'
        mixer.audio_local_port = kwargs.get('audio_local_port') or 4002
        mixer.send_rtpsink_1 = Gst.ElementFactory.make('udpsink', 'send_rtp_sink_1')
        mixer.send_rtpsink_1.set_property('port', mixer.audio_local_port)
        mixer.send_rtpsink_1.set_property('host', mixer.audio_local_ip)
        mixer.pipeline.add(mixer.send_rtpsink_1)

        mixer.send_rtcpsink_1 = Gst.ElementFactory.make('udpsink', 'send_rtcpsink_1')
        mixer.send_rtcpsink_1.set_property('port', mixer.audio_local_port + 1) # FIXME: use rtcp-mux
        mixer.send_rtcpsink_1.set_property('host', mixer.audio_local_ip)
        mixer.send_rtcpsink_1.set_property('async', False)
        mixer.send_rtcpsink_1.set_property('sync', False)
        mixer.pipeline.add(mixer.send_rtcpsink_1)

        send_rtpbin_rtp_srcpad_1 = mixer.send_rtpbin.get_static_pad('send_rtp_src_1')
        send_rtpsrc_sinkpad_1 = mixer.send_rtpsink_1.get_static_pad('sink')
        send_rtpbin_rtp_srcpad_1.link(send_rtpsrc_sinkpad_1)

        send_rtpbin_rtcp_srcpad_1 = mixer.send_rtpbin.get_request_pad('send_rtcp_src_1')
        send_rtcpsrc_sinkpad_1 = mixer.send_rtcpsink_1.get_static_pad('sink')
        send_rtpbin_rtcp_srcpad_1.link(send_rtcpsrc_sinkpad_1)

    mixer.recv_rtpbin.connect('pad-added', _on_mixer_recv_rtpbin_pad_added, mixer)
    mixer.recv_rtpbin.connect('pad-added', _on_mixer_recv_rtpbin_pad_removed, mixer)

    mixer.pipeline.set_state(Gst.State.PAUSED)

    _do_mtunsafe_resize_streams(mixer)

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

    mixer.debug and debug_graph(mixer.pipeline, 'debug_mixer_dispose')

def _parse_mixer_rtpbin_pad_info_from_name(pad_name):
    pad_name_parts = pad_name.split('_')
    info = {}

    if len(pad_name_parts) >= 4:
        info['direction'] = pad_name_parts[0]
        info['protocol'] = pad_name_parts[1]
        info['type'] = pad_name_parts[2]
        info['session'] = int(pad_name_parts[3])

    if len(pad_name_parts) >= 6:
        info['ssrc'] = pad_name_parts[4]
        info['payload'] = int(pad_name_parts[5])

    return info

def _on_mixer_recv_rtpbin_pad_added(rtpbin, pad, mixer):
    pad_name = pad.get_name()
    pad_info = _parse_mixer_rtpbin_pad_info_from_name(pad_name)

    if 'ssrc' not in pad_info: return

    mixer.debug and print('_on_mixer_recv_rtpbin_pad_added', pad_name)

    session = pad_info.get('session')
    _on_mixer_stream_start(mixer, session, pad)

def _on_mixer_recv_rtpbin_pad_removed(rtpbin, pad, mixer):
    pad_name = pad.get_name()
    pad_info = _parse_mixer_rtpbin_pad_info_from_name(pad_name)

    if 'ssrc' not in pad_info: return

    mixer.debug and print('_on_mixer_recv_rtpbin_pad_removed', pad_name)

def do_mixer_stream_init(mixer, **kwargs):
    stream = Stream()

    stream.debug = kwargs.get('debug', mixer.debug)

    stream.disposed = False

    stream.media = kwargs.get('media') or 'video'
    stream.clock_rate = kwargs.get('clock_rate') or 90000
    stream.encoding_name = kwargs.get('encoding_name') or 'VP8'
    stream.payload = kwargs.get('payload') or 101

    if stream.media != 'video' and stream.media != 'audio':
        raise UnsupportedException('Unsupported media: %s' % media)

    if stream.media == 'video' and stream.encoding_name not in ['VP8', 'H264']:
        raise UnsupportedException('Unsupported %s encoding: %s' % (stream.media, stream.encoding_name))

    if stream.media == 'audio' and stream.encoding_name not in ['OPUS']:
        raise UnsupportedException('Unsupported %s encoding: %s' % (stream.media, stream.encoding_name))

    with mixer.lock:
        if stream.media == 'video':
            if len(mixer.video_streams) >= 4:
                raise UnsupportedException('Maximum of 4 video streams supported')
            else:
                mixer.streams[mixer.session_count] = stream
                mixer.video_streams[mixer.session_count] = stream

        elif stream.media == 'audio':
            if len(mixer.audio_streams) >= 6:
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
    stream.rtpdecodebin_linked = False

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

    rtpdecodebin_sinkpad = stream.rtpdecodebin.depay.get_static_pad('sink')
    stream.rtpdecodebin.gsinkpad = Gst.GhostPad('sink', rtpdecodebin_sinkpad)
    stream.rtpdecodebin.add_pad(stream.rtpdecodebin.gsinkpad)

    rtpdecodebin_srcpad = stream.rtpdecodebin.capsfilter.get_static_pad('src')
    stream.rtpdecodebin.gsrcpad = Gst.GhostPad('src', rtpdecodebin_srcpad)
    stream.rtpdecodebin.add_pad(stream.rtpdecodebin.gsrcpad)

    stream.rtpdecodebin.set_locked_state(True)
    stream.rtpdecodebin.set_state(Gst.State.PAUSED)
    mixer.pipeline.add(stream.rtpdecodebin)

    stream.rtpdecodetee = Gst.ElementFactory.make('tee', '%s_rtpdecodetee' % stream.name)
    stream.rtpdecodetee.set_locked_state(True)
    stream.rtpdecodetee.set_state(Gst.State.PAUSED)
    mixer.pipeline.add(stream.rtpdecodetee)

    stream.rtpdecodetee.capsfilter = stream.rtpdecodebin.capsfilter

    stream.fakesink = Gst.ElementFactory.make('fakesink', '%s_fakesink' % stream.name)
    stream.fakesink.set_locked_state(True)
    mixer.pipeline.add(stream.fakesink)

    rtpdecodetee_sinkpad = stream.rtpdecodetee.get_static_pad('sink')
    rtpdecodetee_srcpad = stream.rtpdecodetee.get_request_pad('src_0')

    fakesink_sinkpad = stream.fakesink.get_static_pad('sink')
    fakesink_sinkpad.set_active(False)

    stream.rtpdecodebin.gsrcpad.link(rtpdecodetee_sinkpad)
    rtpdecodetee_srcpad.link(fakesink_sinkpad)

    stream.remote_ip = kwargs.get('remote_ip') or '127.0.0.1'
    stream.remote_port = kwargs.get('remote_port') or 6000
    stream.recv_rtcpsink = Gst.ElementFactory.make('udpsink', '%s_recv_rtcpsink' % stream.name)
    stream.recv_rtcpsink.set_property('port', stream.remote_port)
    stream.recv_rtcpsink.set_property('host', stream.remote_ip)
    stream.recv_rtcpsink.set_property('async', False)
    stream.recv_rtcpsink.set_property('sync', False)

    mixer.pipeline.add(stream.recv_rtcpsink)

    recv_rtcpsink_sinkpad = stream.recv_rtcpsink.get_static_pad('sink')
    recv_rtpbin_rtcp_srcpad = mixer.recv_rtpbin.get_request_pad('send_rtcp_src_%s' % stream.session)
    recv_rtpbin_rtcp_srcpad.link(recv_rtcpsink_sinkpad)

    stream.recv_rtcpsink.sync_state_with_parent()

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

    recv_rtpsrc_srcpad = stream.rtpsrcbin.rtpsrc.get_static_pad('src')
    stream.rtpsrcbin.rtp_gsrcpad = Gst.GhostPad('rtp_src', recv_rtpsrc_srcpad)
    stream.rtpsrcbin.add_pad(stream.rtpsrcbin.rtp_gsrcpad)

    recv_rtpbin_rtp_sinkpad = mixer.recv_rtpbin.get_request_pad('recv_rtp_sink_%s' % stream.session)
    stream.rtpsrcbin.rtp_gsrcpad.link(recv_rtpbin_rtp_sinkpad)

    recv_rtcpsrc_srcpad = stream.rtpsrcbin.rtcpsrc.get_static_pad('src')
    stream.rtpsrcbin.rtcp_gsrcpad = Gst.GhostPad('rtcp_src', recv_rtcpsrc_srcpad)
    stream.rtpsrcbin.add_pad(stream.rtpsrcbin.rtcp_gsrcpad)

    recv_rtpbin_rtcp_sinkpad = mixer.recv_rtpbin.get_request_pad('recv_rtcp_sink_%s' % stream.session)
    stream.rtpsrcbin.rtcp_gsrcpad.link(recv_rtpbin_rtcp_sinkpad)

    stream.rtpsrcbin.sync_state_with_parent()

    stream.debug and debug_graph(mixer.pipeline, 'debug_mixer_stream_%s_init' % stream.session)

    return stream

def do_mixer_stream_dispose(mixer, stream):
    with mixer.lock:
        if stream.disposed: return

        stream.disposed = True
        _do_mtunsafe_unlink_rtpdecodebin_from_avmixer(mixer, stream)
        _do_mtunsafe_resize_streams(mixer)

    GLib.idle_add(_do_mixer_stream_dispose_cb, mixer, stream)

    stream.debug and debug_graph(mixer.pipeline, 'debug_mixer_stream_%s_dispose' % stream.session)

def _do_mixer_stream_dispose_cb(mixer, stream):
    stream.rtpsrcbin.set_state(Gst.State.NULL)
    mixer.pipeline.remove(stream.rtpsrcbin)

    stream.recv_rtcpsink.set_state(Gst.State.NULL)
    mixer.pipeline.remove(stream.recv_rtcpsink)

    stream.rtpdecodebin.set_state(Gst.State.NULL)
    mixer.pipeline.remove(stream.rtpdecodebin)

    stream.rtpdecodetee.set_state(Gst.State.NULL)
    mixer.pipeline.remove(stream.rtpdecodetee)

    stream.fakesink.set_state(Gst.State.NULL)
    mixer.pipeline.remove(stream.fakesink)

    stream.rtpsrcbin = None
    stream.recv_rtcpsink = None
    stream.rtpdecodebin = None
    stream.rtpdecodetee = None
    stream.fakesink = None

    stream.debug and debug_graph(mixer.pipeline, 'debug_mixer_stream_%s_dispose_cb' % stream.session)

def _on_mixer_stream_start(mixer, session, srcpad):
    with mixer.lock:
        if not session in mixer.streams: return

        stream = mixer.streams[session]

        _do_mtunsafe_link_rtpbin_to_rtpdecodebin(stream, srcpad)
        _do_mtunsafe_link_rtpdecodebin_to_avmixer(mixer, stream)
        _do_mtunsafe_resize_streams(mixer)

    stream.debug and debug_graph(mixer.pipeline, 'debug_mixer_stream_%s_start' % session)

def _do_mtunsafe_link_rtpbin_to_rtpdecodebin(stream, rtpbin_srcpad):
    rtpdecodebin_sinkpad = stream.rtpdecodebin.get_static_pad('sink')

    if rtpdecodebin_sinkpad.is_linked():
        peerpad = rtpdecodebin_sinkpad.get_peer()
        peerpad.set_active(False)
        peerpad.unlink(rtpdecodebin_sinkpad)

    rtpbin_srcpad.link(rtpdecodebin_sinkpad)

def _do_mtunsafe_link_rtpdecodebin_to_avmixer(mixer, stream):
    if stream.rtpdecodetee.get_static_pad('src_1'): return

    rtpdecodetee_srcpad = stream.rtpdecodetee.get_request_pad('src_1')

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
            videomixer_sinkpad = mixer.videomixer.request_pad(videomixer_sinkpad_template, None, None)

        rtpdecodetee_srcpad.link(videomixer_sinkpad)

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
            audiomixer_sinkpad = mixer.audiomixer.request_pad(audiomixer_sinkpad_template, None, None)

        rtpdecodetee_srcpad.link(audiomixer_sinkpad)

    stream.rtpdecodebin.set_locked_state(False)
    stream.rtpdecodebin.sync_state_with_parent()

    stream.rtpdecodetee.set_locked_state(False)
    stream.rtpdecodetee.sync_state_with_parent()

    stream.fakesink.get_static_pad('sink').set_active(True)
    stream.fakesink.set_locked_state(False)
    stream.fakesink.sync_state_with_parent()

def _do_mtunsafe_unlink_rtpdecodebin_from_avmixer(mixer, stream):
    if not stream.rtpdecodetee.get_static_pad('src_1'): return

    rtpdecodetee_srcpad = stream.rtpdecodetee.get_static_pad('src_1')
    avmixer_sinkpad = rtpdecodetee_srcpad.get_peer()
    avmixer = avmixer_sinkpad.get_parent_element()

    rtpdecodetee_srcpad.unlink(avmixer_sinkpad)
    avmixer.remove_pad(avmixer_sinkpad)

    if not len(avmixer.sinkpads):
        if stream.media == 'video':
            videosrc_srcpad = mixer.videosrc.get_static_pad('src')
            videosrc_capsfilter_srcpad = mixer.videosrc_capsfilter.get_static_pad('src')
            videomixer_sinkpad = mixer.videomixer.get_request_pad('sink_0')
            videosrc_capsfilter_srcpad.link(videomixer_sinkpad)
            mixer.videosrc.set_locked_state(False)
            videosrc_srcpad.set_active(True)
            mixer.videosrc.sync_state_with_parent()
            mixer.videosrc_capsfilter.sync_state_with_parent()

        elif stream.media == 'audio':
            audiosrc_srcpad = mixer.audiosrc.get_static_pad('src')
            audiosrc_capsfilter_srcpad = mixer.audiosrc_capsfilter.get_static_pad('src')
            audiomixer_sinkpad = mixer.audiomixer.get_request_pad('sink_0')
            audiosrc_capsfilter_srcpad.link(audiomixer_sinkpad)
            mixer.audiosrc.set_locked_state(False)
            audiosrc_srcpad.set_active(True)
            mixer.audiosrc.sync_state_with_parent()
            mixer.audiosrc_capsfilter.sync_state_with_parent()

def _do_mtunsafe_resize_streams(mixer):
    if not hasattr(mixer, 'last_seen_video_streams_count'):
        mixer.last_seen_video_streams_count = 0

    current_video_streams_count = len(mixer.videomixer.sinkpads)

    if mixer.last_seen_video_streams_count != current_video_streams_count:
        if current_video_streams_count > 1:
            width = int(mixer.video_width / 2)
            height = int(mixer.video_height / 2)

        else:
            width = mixer.video_width
            height = mixer.video_height

        caps = Gst.caps_from_string(
            'video/x-raw,format=%s,framerate=%s,width=%s,height=%s' % (
                mixer.video_format, mixer.video_framerate, width, height))

        index = 0
        for sinkpad in mixer.videomixer.sinkpads:
            peerpad = sinkpad.get_peer()
            peerelement = peerpad.get_parent_element()

            if hasattr(peerelement, 'capsfilter'):
                capsfilter = peerelement.capsfilter
            else:
                capsfilter = mixer.videosrc_capsfilter

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

        mixer.last_seen_video_streams_count = index

if __name__ == '__main__':
    Gst.init(None)
    Gst.debug_set_active(True)
    Gst.debug_set_default_threshold(Gst.DebugLevel.FIXME)

    loop = GLib.MainLoop()
    refs = {}

    def do_action(name, action, *ref_names, **kwargs):
        global refs

        args = [refs[ref_name] for ref_name in ref_names]
        refs[name] = action(*args, **kwargs)

    Timer(0, do_action, args=['mixer', do_mixer_init], kwargs={
        'debug': True,
        'debug_output': False,
        'default_pattern': 'snow',
        'default_wave': 'red-noise',
        'video_local_port': 4000,
        'video_remote_port': 3000,
        'audio_local_port': 4002,
        'audio_remote_port': 3001 }).start()

    Timer(2, do_action, args=[None, do_mixer_start, 'mixer']).start()

    Timer(4, do_action, args=['stream_0', do_mixer_stream_init, 'mixer'], kwargs={
        'media': 'video',
        'clock_rate': 90000,
        'encoding_name': 'VP8',
        'payload': 101,
        'local_port': 5000,
        'remote_port': 6000 }).start()

    Timer(4, do_action, args=['stream_1', do_mixer_stream_init, 'mixer'], kwargs={
        'media': 'audio',
        'clock_rate': 48000,
        'encoding_name': 'OPUS',
        'payload': 100,
        'local_port': 5002,
        'remote_port': 6001 }).start()

    Timer(10, do_action, args=['stream_0', do_mixer_stream_dispose, 'mixer', 'stream_0']).start()
    Timer(10, do_action, args=['stream_1', do_mixer_stream_dispose, 'mixer', 'stream_1']).start()

    Timer(15, do_action, args=['stream_2', do_mixer_stream_init, 'mixer'], kwargs={
        'media': 'video',
        'clock_rate': 90000,
        'encoding_name': 'VP8',
        'payload': 101,
        'local_port': 5100,
        'remote_port': 6100 }).start()

    Timer(15, do_action, args=['stream_3', do_mixer_stream_init, 'mixer'], kwargs={
        'media': 'audio',
        'clock_rate': 48000,
        'encoding_name': 'OPUS',
        'payload': 100,
        'local_port': 5102,
        'remote_port': 6101 }).start()

    Timer(25, do_action, args=['stream_2', do_mixer_stream_dispose, 'mixer', 'stream_2']).start()
    Timer(25, do_action, args=['stream_3', do_mixer_stream_dispose, 'mixer', 'stream_3']).start()

    Timer(30, do_action, args=['stream_0', do_mixer_stream_init, 'mixer'], kwargs={
        'media': 'video',
        'clock_rate': 90000,
        'encoding_name': 'VP8',
        'payload': 101,
        'local_port': 5000,
        'remote_port': 6000 }).start()

    Timer(30, do_action, args=['stream_1', do_mixer_stream_init, 'mixer'], kwargs={
        'media': 'audio',
        'clock_rate': 48000,
        'encoding_name': 'OPUS',
        'payload': 100,
        'local_port': 5002,
        'remote_port': 6001 }).start()

    Timer(40, do_action, args=['stream_2', do_mixer_stream_init, 'mixer'], kwargs={
        'media': 'video',
        'clock_rate': 90000,
        'encoding_name': 'VP8',
        'payload': 101,
        'local_port': 5100,
        'remote_port': 6100 }).start()

    Timer(40, do_action, args=['stream_3', do_mixer_stream_init, 'mixer'], kwargs={
        'media': 'audio',
        'clock_rate': 48000,
        'encoding_name': 'OPUS',
        'payload': 100,
        'local_port': 5102,
        'remote_port': 6101 }).start()

    Timer(50, do_action, args=['stream_0', do_mixer_stream_dispose, 'mixer', 'stream_0']).start()
    Timer(50, do_action, args=['stream_1', do_mixer_stream_dispose, 'mixer', 'stream_1']).start()
    Timer(60, do_action, args=['stream_2', do_mixer_stream_dispose, 'mixer', 'stream_2']).start()
    Timer(60, do_action, args=['stream_3', do_mixer_stream_dispose, 'mixer', 'stream_3']).start()
    Timer(70, do_action, args=['mixer', do_mixer_dispose, 'mixer']).start()
    Timer(75, loop.quit).start()

    loop.run()
