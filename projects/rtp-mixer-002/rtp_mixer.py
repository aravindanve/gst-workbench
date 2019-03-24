#!/usr/bin/env python3

import sys
import signal
import re
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
from utils.interval_timer import set_timeout, clear_timeout
from collections import namedtuple

def parse_from_caps(caps, key):
    match = re.search(re.escape(key) + r'=(?:\([^\)]+\))?([^,]+)', caps)
    return match.group(1).strip() if match else None

def create_pipeline(name):
    return Gst.Pipeline.new(name)

def create_rtpbin(parentbin, name):
    rtpbin = Gst.ElementFactory.make('rtpbin', name)
    rtpbin.set_property('autoremove', True)
    parentbin.add(rtpbin)
    return rtpbin

def create_defvideosrc(parentbin, name, pattern):
    defvideosrc = Gst.ElementFactory.make('videotestsrc', name)
    defvideosrc.set_property('is-live', True)
    defvideosrc.set_property('pattern', pattern)
    parentbin.add(defvideosrc)
    return defvideosrc

def create_defaudiosrc(parentbin, name, wave):
    defaudiosrc = Gst.ElementFactory.make('audiotestsrc', name)
    defaudiosrc.set_property('is-live', True)
    defaudiosrc.set_property('wave', wave)
    parentbin.add(defaudiosrc)
    return defaudiosrc

def create_videomixer(parentbin, name):
    videomixer = Gst.ElementFactory.make('videomixer', name)
    videomixer.set_property('background', 'black')
    parentbin.add(videomixer)
    return videomixer

def create_audiomixer(parentbin, name):
    audiomixer = Gst.ElementFactory.make('audiomixer', name)
    parentbin.add(audiomixer)
    return audiomixer

def create_videosink(parentbin, name):
    videosink = Gst.ElementFactory.make('autovideosink', name)
    parentbin.add(videosink)
    return videosink

def create_audiosink(parentbin, name):
    audiosink = Gst.ElementFactory.make('autoaudiosink', name)
    parentbin.add(audiosink)
    return audiosink

def create_udpsrc(parentbin, name, port, address, caps=None):
    udpsrc = Gst.ElementFactory.make('udpsrc', name)
    udpsrc.set_property('port', port)
    udpsrc.set_property('address', address)

    if caps:
        udpsrc.set_property('caps', Gst.caps_from_string(caps))

    parentbin.add(udpsrc)
    return udpsrc

def create_udpsink(parentbin, name, port, host, sync=False, _async=False):
    udpsink = Gst.ElementFactory.make('udpsink', name)
    udpsink.set_property('port', port)
    udpsink.set_property('host', host)
    udpsink.set_property('async', False)
    udpsink.set_property('sync', False)

    udpsink.set_state(Gst.State.PLAYING)
    parentbin.add(udpsink)
    return udpsink

def create_rtpsrcbin(parentbin, name, caps, port, address):
    rtpsrcbin = Gst.Bin(name)

    rtp_udpsrc_name = '%s_rtp_udpsrc' % name
    rtpsrcbin.rtp_udpsrc = create_udpsrc(
        rtpsrcbin, rtp_udpsrc_name, port, address, caps)

    # FIXME: use rtcp-mux
    rtcp_udpsrc_name = '%s_rtcp_udpsrc' % name
    rtpsrcbin.rtcp_udpsrc = create_udpsrc(
        rtpsrcbin, rtcp_udpsrc_name, port + 1, address)

    rtpsrcbin.set_state(Gst.State.PAUSED)
    parentbin.add(rtpsrcbin)

    return rtpsrcbin

def create_selector(parentbin, name):
    selector = Gst.ElementFactory.make('input-selector', name)
    parentbin.add(selector)
    return selector

def create_rtpdecodebin_vp8(parentbin, name):
    rtpdecodebin = Gst.Bin(name)

    rtpdecodebin.depay = Gst.ElementFactory.make(
        'rtpvp8depay', '%s_depay' % name)

    rtpdecodebin.dec = Gst.ElementFactory.make(
        'vp8dec', '%s_dec' % name)

    rtpdecodebin.add(rtpdecodebin.depay)
    rtpdecodebin.add(rtpdecodebin.dec)

    rtpdecodebin.selector = create_selector(
        rtpdecodebin, '%s_selector' % name)

    rtpdecodebin.selector.link(rtpdecodebin.depay)
    rtpdecodebin.depay.link(rtpdecodebin.dec)

    rtpdecodebin.set_state(Gst.State.PLAYING)
    parentbin.add(rtpdecodebin)

    return rtpdecodebin

def create_rtpdecodebin_h264():
    pass

def create_rtpdecodebin_opus():
    pass

def create_rtpdecodebin(parentbin, name, rtpstream):
    if rtpstream.media == 'video':
        if rtpstream.encoding_name == 'VP8':
            return create_rtpdecodebin_vp8(parentbin, name)
        elif rtpstream.encoding_name == 'H264':
            # FIXME: add support for h264 streams
            raise UnsupportedException(
                'Unsupported codec: %s' % rtpstream.encoding_name)
        else:
            raise UnsupportedException(
                'Unsupported codec: %s' % rtpstream.encoding_name)

    elif rtpstream.media == 'audio':
        if  rtpstream.encoding_name == 'OPUS':
            # FIXME: add support for opus streams
            raise UnsupportedException(
                'Unsupported codec: %s' % rtpstream.encoding_name)
        else:
            raise UnsupportedException(
                'Unsupported codec: %s' % rtpstream.encoding_name)

def link_elements(srcelement, sinkelement, caps_filter=None):
    if caps_filter:
        srcelement.link_filtered(
            sinkelement, Gst.caps_from_string(caps_filter))
    else:
        srcelement.link(sinkelement)

def link_rtpsrcbin_to_rtpbin(rtpsrcbin, rtpbin, session):
    grtpsrcpad = Gst.GhostPad.new(
        'recv_rtp_src',
        rtpsrcbin.rtp_udpsrc.get_static_pad('src'))

    grtcpsrcpad = Gst.GhostPad.new(
        'recv_rtcp_src',
        rtpsrcbin.rtcp_udpsrc.get_static_pad('src'))

    grtpsrcpad.set_active(True)
    grtcpsrcpad.set_active(True)

    rtpsrcbin.add_pad(grtpsrcpad)
    rtpsrcbin.add_pad(grtcpsrcpad)
    grtpsrcpad.link(rtpbin.get_request_pad('recv_rtp_sink_%d' % session))
    grtcpsrcpad.link(
        rtpbin.get_request_pad('recv_rtcp_sink_%d' % session))

    rtpsrcbin.set_state(Gst.State.PLAYING)

def link_rtcpsink_to_rtpbin(rtcpsink, rtpbin, session):
    Gst.Pad.link(
        rtpbin.get_request_pad('send_rtcp_src_%d' % session),
        rtcpsink.get_static_pad('sink'))

def link_rtpdecodebin_to_mixer(rtpdecodebin, mixer):
    gsrcpad = Gst.GhostPad.new(
        'src', rtpdecodebin.dec.get_static_pad('src'))

    gsrcpad.set_active(True)
    rtpdecodebin.add_pad(gsrcpad)

    sinkpad = mixer.request_pad(
        mixer.get_pad_template('sink_%u'), None, None)
    # mixer.sinkpads[0].get_pad_template(), None, None)

    gsrcpad.link(sinkpad)

def link_rtpbinsrcpad_to_rtpdecodebin(rtpbinsrcpad, rtpdecodebin):
    sinkpad = rtpdecodebin.selector.request_pad(
        rtpdecodebin.selector.get_pad_template('sink_%u'), None, None)

    gsinkpad = Gst.GhostPad.new(sinkpad.get_name(), sinkpad)
    gsinkpad.set_active(True)
    rtpdecodebin.add_pad(gsinkpad)

    rtpbinsrcpad.link(gsinkpad)
    rtpdecodebin.selector.set_property('active-pad', sinkpad)

def debug_gstbin_graph(gstbin, name):
    f = open('%s.dot' % name, 'w')
    f.write(Gst.debug_bin_to_dot_data(gstbin, Gst.DebugGraphDetails.ALL))
    # f.write(Gst.debug_bin_to_dot_data(gstbin, Gst.DebugGraphDetails.VERBOSE))
    f.close()

class UnsupportedException(Exception):
    pass

class RtpStream:
    pass

class RtpMixer:
    DEFAULT_BIND_ADDRESS='127.0.0.1'
    DEFAULT_VIDEO_SRC_PATTERN='snow'
    DEFAULT_VIDEO_SRC_CAPS='video/x-raw,format=I420,width=640,height=360'
    DEFAULT_AUDIO_SRC_WAVE='silence'
    DEFAULT_AUDIO_SRC_CAPS='audio/x-raw'

    def __init__(self):
        self.destroyed = False
        self.rtpsession_counter = 0
        self.rtpstreams = []
        self.pipeline = create_pipeline('rtpmixer')
        self.rtpbin = create_rtpbin(self.pipeline, 'rtpbin0')
        self.defvideosrc = create_defvideosrc(
            self.pipeline, 'defvideosrc0', self.DEFAULT_VIDEO_SRC_PATTERN)

        self.defaudiosrc = create_defaudiosrc(
            self.pipeline, 'defaudiosrc0', self.DEFAULT_AUDIO_SRC_WAVE)

        self.videomixer = create_videomixer(self.pipeline, 'videomixer0')
        self.audiomixer = create_audiomixer(self.pipeline, 'audiomixer0')

        # FIXME: add rtpsink in place of autosinks
        self.videosink = create_videosink(self.pipeline, 'videosink0')
        self.audiosink = create_audiosink(self.pipeline, 'audiosink0')

        link_elements(self.videomixer, self.videosink)
        link_elements(self.audiomixer, self.audiosink)
        link_elements(
            self.defvideosrc, self.videomixer, self.DEFAULT_VIDEO_SRC_CAPS)

        link_elements(
            self.defaudiosrc, self.audiomixer, self.DEFAULT_AUDIO_SRC_CAPS)

        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect('message', self.on_bus_message)
        self.rtpbin.connect('pad-added', self.on_rtpbin_pad_added)
        debug_gstbin_graph(self.pipeline, 'pipeline-init')

    def add_stream(
            self, caps, local_port, remote_port, remote_host,
            local_address=None):

        if local_address == None:
            local_address = self.DEFAULT_BIND_ADDRESS

        session = self.rtpsession_counter
        media = parse_from_caps(caps, 'media')
        payload = parse_from_caps(caps, 'payload')
        encoding_name = parse_from_caps(caps, 'encoding-name')

        if media != 'video' and media != 'audio':
            raise UnsupportedException(
                'Unsupported media: %s' % media)

        if media == 'video' and (
                encoding_name != 'VP8' and
                encoding_name != 'H264'):
            raise UnsupportedException(
                'Unsupported codec: %s' % encoding_name)

        if media == 'audio' and (
                encoding_name != 'OPUS'):
            raise UnsupportedException(
                'Unsupported codec: %s' % encoding_name)

        rtpsrcbin = create_rtpsrcbin(
            self.pipeline, 'rtpsrcbin%d' % session,
            caps, local_port, local_address)

        rtcpsink = create_udpsink(
            self.pipeline, 'rtcpsink%d' % session, remote_port, remote_host)

        rtpstream = RtpStream()
        rtpstream.session = session
        rtpstream.media = media
        rtpstream.payload = payload
        rtpstream.encoding_name = encoding_name
        rtpstream.rtpsrcbin = rtpsrcbin
        rtpstream.rtcpsink = rtcpsink

        link_rtpsrcbin_to_rtpbin(rtpsrcbin, self.rtpbin, session)
        link_rtcpsink_to_rtpbin(rtcpsink, self.rtpbin, session)

        debug_gstbin_graph(
            self.pipeline, 'pipeline-stream-added-%d' % session)

        self.rtpstreams.append(rtpstream)
        self.rtpsession_counter += 1

        return rtpstream

    def remove_stream(self):
        # FIXME: remove stream
        pass

    def start(self):
        self.pipeline.set_state(Gst.State.PLAYING)
        debug_gstbin_graph(self.pipeline, 'pipeline-start')

    def stop(self):
        self.pipeline.set_state(Gst.State.PAUSED)
        debug_gstbin_graph(self.pipeline, 'pipeline-stop')

    def destroy(self):
        if not self.destroyed:
            self.destroyed = True
            self.stop()
            self.bus.remove_signal_watch()
            self.pipeline.set_state(Gst.State.NULL)
            self.pipeline = None
            self.rtpbin = None
            self.defvideosrc = None
            self.defaudiosrc = None
            self.videomixer = None
            self.audiomixer = None
            self.videosink = None
            self.audiosink = None

    def on_rtpbin_pad_added(self, rtpbin, pad):
        print('RtpMixer.on_rtpbin_pad_added()', pad.get_name())

        # pad name format:
        # {send|recv}_{rtp|rtcp}_{src|sink}_{SESSION}_{SSRC}_{PAYLOAD}
        # e.g. recv_rtp_src_0_367391323_101
        pad_name_parts = pad.get_name().split('_')

        if not len(pad_name_parts) == 6:
            return

        session = int(pad_name_parts[3])
        rtpstream = None

        for stream in self.rtpstreams:
            print('stream', stream.session)
            if stream.session == session:
                rtpstream = stream
                break

        if rtpstream == None:
            raise Exception('Stream %d not found' % session)

        if not hasattr(rtpstream, 'rtpdecodebin'):
            rtpstream.rtpdecodebin = create_rtpdecodebin(
                self.pipeline, 'rtpdecodebin%d' % session, rtpstream)

            if rtpstream.media == 'video':
                link_rtpdecodebin_to_mixer(
                    rtpstream.rtpdecodebin, self.videomixer)
            elif rtpstream.media == 'audio':
                link_rtpdecodebin_to_mixer(
                    rtpstream.rtpdecodebin, self.audiomixer)
            else:
                raise UnsupportedException(
                    'Unsupported media: %s' % media)

        link_rtpbinsrcpad_to_rtpdecodebin(pad, rtpstream.rtpdecodebin)
        debug_gstbin_graph(
            self.pipeline, 'pipeline-stream-started-%d' % session)

    def on_bus_message(self, bus, message):
        debug_gstbin_graph(
            self.pipeline, 'pipeline-bus-message')
        if message.type == Gst.MessageType.QOS:
            pass
        if message.type == Gst.MessageType.EOS:
            self.destroy()
        elif message.type == Gst.MessageType.ERROR:
            self.pipeline.set_state(Gst.State.NULL)
            err, debug = message.parse_error()
            print('message:ERROR %s' % err, debug)
        else:
            # print(message.type)
            pass

if __name__ == '__main__':
    Gst.init(None)
    Gst.debug_set_active(True)
    Gst.debug_set_default_threshold(Gst.DebugLevel.FIXME)
    rtpmixer = RtpMixer()
    rtpmixer.start()
    timers = []

    def add_stream_0():
        rtpstream = rtpmixer.add_stream(**{
            'caps': '\
                application/x-rtp,\
                media=video,\
                clock-rate=90000,\
                encoding-name=VP8,\
                payload=101',
            'local_port': 5000,
            'remote_port': 6000,
            'remote_host': '127.0.0.1'
        })
        print(rtpstream)

    def remove_stream_0():
        pass

    def add_stream_1():
        pass

    def remove_stream_1():
        pass

    def on_sigint(sig=None, frame=None):
        for timer in timers:
            clear_timeout(timer)
        rtpmixer.destroy()
        sys.exit(0)

    timers.append(set_timeout(add_stream_0, 3))
    timers.append(set_timeout(add_stream_1, 6))
    timers.append(set_timeout(remove_stream_0, 10))
    timers.append(set_timeout(remove_stream_1, 12))

    signal.signal(signal.SIGINT, on_sigint)
    GLib.MainLoop().run()
