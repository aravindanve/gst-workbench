#!/usr/bin/env python3

import re
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
from uuid import uuid4

def debug_graph(debug, gstbin, filename):
    if not debug: return
    f = open('%s.dot' % filename, 'w')
    f.write(Gst.debug_bin_to_dot_data(gstbin, Gst.DebugGraphDetails.ALL))
    f.close()

def parse_capability(caps, capability):
    match = re.search(re.escape(capability) + r'=(?:\([^\)]+\))?([^,]+)', caps)
    return match.group(1).strip() if match else None

def get_video_codecs():
    return ['VP8', 'H264']

def get_audio_codecs():
    return ['OPUS']

class RequiredOptionException(Exception):
    pass

class UnsupportedException(Exception):
    pass

class RtpMixerOptions:
    def __init__(self, **kwargs):
        self.debug = kwargs.get('debug', False) # FIXME: change to debug_graph
        # self.preview = kwargs.get('debug_preview', False)
        self.videosrc_pattern = kwargs.get('videosrc_pattern', 'snow')
        self.videosrc_caps = kwargs.get('videosrc_caps', 'video/x-raw,format=I420,framerate=30/1,width=1280,height=720')
        self.audiosrc_wave = kwargs.get('audiosrc_wave', 'sine')
        self.audiosrc_caps = kwargs.get('audiosrc_caps', 'audio/x-raw,format=F32LE,rate=44100,channels=1,layout=interleaved')
        self.videomixer_background = kwargs.get('videomixer_background', 'black')

class RtpMixer:
    def __init__(self, **kwargs):
        opt = RtpMixerOptions(**kwargs)

        self.debug = opt.debug
        self.id = uuid4()
        self.name = 'rtpmixer_%s' % self.id
        self.disposed = False
        self.rtpsession_counter = 0
        self.rtpstreams = {}

        self.pipeline = Gst.Pipeline(self.name)

        self.rtpbin = Gst.ElementFactory.make('rtpbin', 'rtpbin0')
        self.rtpbin.set_property('autoremove', True)
        self.rtpbin.set_property('drop-on-latency', True)
        self.pipeline.add(self.rtpbin)

        self.videosrc = Gst.ElementFactory.make('videotestsrc', 'videosrc0')
        self.videosrc.set_property('is-live', True)
        self.videosrc.set_property('pattern', opt.videosrc_pattern)
        self.pipeline.add(self.videosrc)

        self.videosrc_capsfilter = Gst.ElementFactory.make('capsfilter', 'videosrc_capsfilter0')
        self.videosrc_capsfilter.set_property('caps', Gst.caps_from_string(opt.videosrc_caps))
        self.pipeline.add(self.videosrc_capsfilter)

        self.audiosrc = Gst.ElementFactory.make('audiotestsrc', 'audiosrc0')
        self.audiosrc.set_property('is-live', True)
        self.audiosrc.set_property('wave', opt.audiosrc_wave)
        self.pipeline.add(self.audiosrc)

        self.audiosrc_capsfilter = Gst.ElementFactory.make('capsfilter', 'audiosrc_capsfilter0')
        self.audiosrc_capsfilter.set_property('caps', Gst.caps_from_string(opt.audiosrc_caps))
        self.pipeline.add(self.audiosrc_capsfilter)

        self.videomixer = Gst.ElementFactory.make('videomixer', 'videomixer0')
        self.videomixer.set_property('background', opt.videomixer_background)
        self.pipeline.add(self.videomixer)

        self.audiomixer = Gst.ElementFactory.make('audiomixer', 'audiomixer0')
        self.pipeline.add(self.audiomixer)

        self.multiq = Gst.ElementFactory.make('multiqueue', 'multiq0')
        self.pipeline.add(self.multiq)

        # FIXME: replace autovideosink with rtpsink
        self.videosink = Gst.ElementFactory.make('autovideosink', 'videosink0')
        self.pipeline.add(self.videosink)

        # FIXME: replace autoaudiosink with rtpsink
        self.audiosink = Gst.ElementFactory.make('autoaudiosink', 'audiosink0')
        self.pipeline.add(self.audiosink)

        videomixer_srcpad = self.videomixer.get_static_pad('src')
        videoqueue_sinkpad = self.multiq.get_request_pad('sink_0')
        videoqueue_srcpad = self.multiq.get_static_pad('src_0')
        videosink_sinkpad = self.videosink.get_static_pad('sink')

        Gst.Pad.link(videomixer_srcpad, videoqueue_sinkpad)
        Gst.Pad.link(videoqueue_srcpad, videosink_sinkpad)
        Gst.Element.link(self.videosrc_capsfilter, self.videomixer)
        Gst.Element.link(self.videosrc, self.videosrc_capsfilter)

        audiomixer_srcpad = self.audiomixer.get_static_pad('src')
        audioqueue_sinkpad = self.multiq.get_request_pad('sink_1')
        audioqueue_srcpad = self.multiq.get_static_pad('src_1')
        audiosink_sinkpad = self.audiosink.get_static_pad('sink')

        Gst.Pad.link(audiomixer_srcpad, audioqueue_sinkpad)
        Gst.Pad.link(audioqueue_srcpad, audiosink_sinkpad)
        Gst.Element.link(self.audiosrc_capsfilter, self.audiomixer)
        Gst.Element.link(self.audiosrc, self.audiosrc_capsfilter)

        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect('message', self._on_bus_message)
        self.rtpbin.connect('pad-added', self._on_rtpbin_pad_added)
        self.rtpbin.connect('pad-removed', self._on_rtpbin_pad_removed)

        debug_graph(self.debug, self.pipeline, 'rtpmixer_init')

    def dispose(self):
        pass # FIXME

    def start(self):
        self.pipeline.set_state(Gst.State.PLAYING)

        debug_graph(self.debug, self.pipeline, 'rtpmixer_start')

    def stop(self):
        self.pipeline.set_state(Gst.State.PAUSED)

        debug_graph(self.debug, self.pipeline, 'rtpmixer_stop')

    def add_stream(self, **kwargs):
        return RtpStream(self, debug=self.debug, **kwargs)

    def remove_stream(self, rtpstream):
        return rtpstream.dispose()

    def find_stream_by_id(self, rtpstream_id):
        if rtpstream_id in self.rtpstreams:
            return self.rtpstreams[rtpstream_id]

    def _on_bus_message(self, bus, message):
        if message.type == Gst.MessageType.QOS:
            pass
        if message.type == Gst.MessageType.EOS:
            self.dispose()
        elif message.type == Gst.MessageType.ERROR:
            self.pipeline.set_state(Gst.State.NULL)
            err, debug = message.parse_error()
            print('message:ERROR %s' % err, debug)
        else:
            # print(message.type)
            pass

    def _on_rtpbin_pad_added(self, rtpbin, pad):
        self.debug and print('RtpMixer._on_rtpbin_pad_added()', pad.get_name())

        # format: '%u_%u_%u_%d_%d_%d'
        # arguments: recv/send, rtp/rtcp, src/sink, session, ssrc, pt
        # e.g. recv_rtp_src_0_367391323_101
        pad_name = pad.get_name()
        pad_segments = pad_name.split('_')
        session = int(pad_segments[3])

        if not len(pad_segments) == 6: return

        for rtpstream in self.rtpstreams.values():
            if rtpstream.session == session:
                return rtpstream._on_ssrc_srcpad_added(pad)

        raise Exception('RtpStream for session %d not found' % session)

    def _on_rtpbin_pad_removed(self, rtpbin, pad):
        pass # FIXME

class RtpStreamOptions:
    def __init__(self, **kwargs):
        self.debug = kwargs.get('debug', False)
        self.caps = kwargs.get('caps', None)
        self.local_ip = kwargs.get('local_ip', '127.0.0.1')
        self.local_port = kwargs.get('local_port', None)
        self.remote_ip = kwargs.get('remote_ip', '127.0.0.1')
        self.remote_port = kwargs.get('remote_port', None)

        if not self.caps:
            raise RequiredOptionException('caps is required')

        if not self.local_port:
            raise RequiredOptionException('local_port is required')

        if not self.remote_port:
            raise RequiredOptionException('remote_port is required')

        self.media = parse_capability(self.caps, 'media')
        self.payload = parse_capability(self.caps, 'payload')
        self.encoding_name = parse_capability(self.caps, 'encoding-name')

        if not self.media in ['video', 'audio']:
            raise UnsupportedException('Unsupported media: %s' % self.media)

        if self.media == 'video':
            if not self.encoding_name in get_video_codecs():
                raise UnsupportedException(
                    'Unsupported %s encoding: %s' % (media, encoding_name))

        if self.media == 'audio':
            if not self.encoding_name in get_audio_codecs():
                raise UnsupportedException(
                    'Unsupported %s encoding: %s' % (media, encoding_name))

class RtpStream:
    def __init__(self, rtpmixer, **kwargs):
        opt = RtpStreamOptions(**kwargs)

        self.debug = opt.debug
        self.id = uuid4()
        self.name = 'rtpstream_%s' % self.id
        self.rtpmixer = rtpmixer
        self.session = rtpmixer.rtpsession_counter
        self.media = opt.media
        self.payload = opt.payload
        self.encoding_name = opt.encoding_name
        self.rtpdecodebin = None

        self.rtcpsink = Gst.ElementFactory.make('udpsink', 'rtcpsink%d' % self.session)
        self.rtcpsink.set_property('port', opt.remote_port)
        self.rtcpsink.set_property('host', opt.remote_ip)
        self.rtcpsink.set_property('async', False)
        self.rtcpsink.set_property('sync', False)

        self.rtcpsink.set_state(Gst.State.PLAYING)
        rtpmixer.pipeline.add(self.rtcpsink)

        self.rtpsrcbin = Gst.Bin('rtpsrcbin%d' % self.session)

        self.rtpsrcbin.rtpsrc = Gst.ElementFactory.make('udpsrc', 'rtpsrc0')
        self.rtpsrcbin.rtpsrc.set_property('port', opt.local_port)
        self.rtpsrcbin.rtpsrc.set_property('address', opt.local_ip)
        self.rtpsrcbin.rtpsrc.set_property('caps', Gst.caps_from_string(opt.caps))
        self.rtpsrcbin.add(self.rtpsrcbin.rtpsrc)

        self.rtpsrcbin.rtcpsrc = Gst.ElementFactory.make('udpsrc', 'rtcpsrc0')
        self.rtpsrcbin.rtcpsrc.set_property('port', opt.local_port + 1) # FIXME: use rtcp-mux
        self.rtpsrcbin.rtcpsrc.set_property('address', opt.local_ip)
        self.rtpsrcbin.add(self.rtpsrcbin.rtcpsrc)

        rtpsrcpad = self.rtpsrcbin.rtpsrc.get_static_pad('src')
        grtpsrcpad = Gst.GhostPad('rtp_src', rtpsrcpad)
        self.rtpsrcbin.add_pad(grtpsrcpad)

        rtcpsrcpad = self.rtpsrcbin.rtcpsrc.get_static_pad('src')
        grtcpsrcpad = Gst.GhostPad('rtcp_src', rtcpsrcpad)
        self.rtpsrcbin.add_pad(grtcpsrcpad)

        self.rtpsrcbin.set_state(Gst.State.PAUSED)
        rtpmixer.pipeline.add(self.rtpsrcbin)

        rtcpsinkpad = self.rtcpsink.get_static_pad('sink')
        sendrtcpsrcpad = rtpmixer.rtpbin.get_request_pad('send_rtcp_src_%d' % self.session)
        recvrtpsinkpad = rtpmixer.rtpbin.get_request_pad('recv_rtp_sink_%d' % self.session)
        recvrtcpsinkpad = rtpmixer.rtpbin.get_request_pad('recv_rtcp_sink_%d' % self.session)

        Gst.Pad.link(sendrtcpsrcpad, rtcpsinkpad)
        Gst.Pad.link(grtpsrcpad, recvrtpsinkpad)
        Gst.Pad.link(grtcpsrcpad, recvrtcpsinkpad)

        self.rtpsrcbin.set_state(Gst.State.PLAYING)
        debug_graph(self.debug, rtpmixer.pipeline, 'rtpstream_init_%d' % self.session)

        rtpmixer.rtpstreams[self.id] = self
        rtpmixer.rtpsession_counter += 1

    def dispose(self):
        pass # FIXME

    def _init_rtpdecodebin(self):
        if self.rtpdecodebin:
            raise Exception('RtpStream rtpdecodebin already initialized')

        self.rtpdecodebin = Gst.Bin('rtpdecodebin%d' % self.session)

        if self.encoding_name == 'VP8':
            self.rtpdecodebin.depay = Gst.ElementFactory.make('rtpvp8depay', 'depay0')
            self.rtpdecodebin.dec = Gst.ElementFactory.make('vp8dec', 'dec0')

        elif self.encoding_name == 'H264':
            self.rtpdecodebin.depay = Gst.ElementFactory.make('rtph264depay', 'depay0')
            self.rtpdecodebin.dec = Gst.ElementFactory.make('avdec_h264', 'dec0')

        elif self.encoding_name == 'OPUS':
            self.rtpdecodebin.depay = Gst.ElementFactory.make('rtpopusdepay', 'depay0')
            self.rtpdecodebin.dec = Gst.ElementFactory.make('opusdec', 'dec0')

        self.rtpdecodebin.add(self.rtpdecodebin.depay)
        self.rtpdecodebin.add(self.rtpdecodebin.dec)

        Gst.Element.link(self.rtpdecodebin.depay, self.rtpdecodebin.dec)

        if self.media == 'video':
            self.rtpdecodebin.videorate = Gst.ElementFactory.make('videorate', 'videorate0')
            self.rtpdecodebin.add(self.rtpdecodebin.videorate)

            self.rtpdecodebin.videoconvert = Gst.ElementFactory.make('videoconvert', 'videoconvert0')
            self.rtpdecodebin.add(self.rtpdecodebin.videoconvert)

            self.rtpdecodebin.videoscale = Gst.ElementFactory.make('videoscale', 'videoscale0')
            self.rtpdecodebin.add(self.rtpdecodebin.videoscale)

            decodecaps = Gst.caps_from_string('video/x-raw,framerate=30/1,format=I420,width=1280,height=720')
            self.rtpdecodebin.capsfilter = Gst.ElementFactory.make('capsfilter', 'capsfilter0')
            self.rtpdecodebin.capsfilter.set_property('caps', decodecaps)
            self.rtpdecodebin.add(self.rtpdecodebin.capsfilter)

            Gst.Element.link(self.rtpdecodebin.dec, self.rtpdecodebin.videorate)
            Gst.Element.link(self.rtpdecodebin.videorate, self.rtpdecodebin.videoconvert)
            Gst.Element.link(self.rtpdecodebin.videoconvert, self.rtpdecodebin.videoscale)
            Gst.Element.link(self.rtpdecodebin.videoscale, self.rtpdecodebin.capsfilter)

        elif self.media == 'audio':
            self.rtpdecodebin.audiorate = Gst.ElementFactory.make('audiorate', 'audiorate0')
            self.rtpdecodebin.add(self.rtpdecodebin.audiorate)

            self.rtpdecodebin.audioconvert = Gst.ElementFactory.make('audioconvert', 'audioconvert0')
            self.rtpdecodebin.add(self.rtpdecodebin.audioconvert)

            self.rtpdecodebin.audioresample = Gst.ElementFactory.make('audioresample', 'audioresample0')
            self.rtpdecodebin.add(self.rtpdecodebin.audioresample)

            decodecaps = Gst.caps_from_string('audio/x-raw,format=F32LE,rate=44100,channels=2')
            self.rtpdecodebin.capsfilter = Gst.ElementFactory.make('capsfilter', 'capsfilter0')
            self.rtpdecodebin.capsfilter.set_property('caps', decodecaps)
            self.rtpdecodebin.add(self.rtpdecodebin.capsfilter)

            Gst.Element.link(self.rtpdecodebin.dec, self.rtpdecodebin.audiorate)
            Gst.Element.link(self.rtpdecodebin.audiorate, self.rtpdecodebin.audioconvert)
            Gst.Element.link(self.rtpdecodebin.audioconvert, self.rtpdecodebin.audioresample)
            Gst.Element.link(self.rtpdecodebin.audioresample, self.rtpdecodebin.capsfilter)

        self.rtpdecodebin.set_state(Gst.State.PLAYING)
        self.rtpmixer.pipeline.add(self.rtpdecodebin)

        srcpad = self.rtpdecodebin.capsfilter.get_static_pad('src')
        gsrcpad = Gst.GhostPad.new('src', srcpad)
        gsrcpad.set_active(True)
        self.rtpdecodebin.add_pad(gsrcpad)

        if self.media == 'video':
            defaultsrcpad = self.rtpmixer.videosrc_capsfilter.get_static_pad('src')

        elif self.media == 'audio':
            defaultsrcpad = self.rtpmixer.audiosrc_capsfilter.get_static_pad('src')

        if defaultsrcpad.is_linked():
            sinkpad = defaultsrcpad.get_peer()
            defaultsrcpad.set_active(False)
            Gst.Pad.unlink(defaultsrcpad, sinkpad)

        elif self.media == 'video':
            sinkpad_template = self.rtpmixer.videomixer.get_pad_template('sink_%u')
            sinkpad = self.rtpmixer.videomixer.request_pad(sinkpad_template, None, None)

        elif self.media == 'audio':
            sinkpad_template = self.rtpmixer.audiomixer.get_pad_template('sink_%u')
            sinkpad = self.rtpmixer.audiomixer.request_pad(sinkpad_template, None, None)

        Gst.Pad.link(gsrcpad, sinkpad)

        debug_graph(self.debug, rtpmixer.pipeline, 'rtpstream_prestart_%d' % self.session)

    def _link_rtpdecodebin(self, srcpad):
        gsinkpad = self.rtpdecodebin.get_static_pad('sink')

        if not gsinkpad:
            sinkpad = self.rtpdecodebin.depay.get_static_pad('sink')
            gsinkpad = Gst.GhostPad.new('sink', sinkpad)
            gsinkpad.set_active(True)
            self.rtpdecodebin.add_pad(gsinkpad)

        if gsinkpad.is_linked():
            oldsrcpad = gsinkpad.get_peer()
            Gst.Pad.unlink(oldsrcpad, gsinkpad)

        Gst.Pad.link(srcpad, gsinkpad)

        print(self.rtpmixer.rtpbin.get_by_name('rtpjitterbuffer%d' % self.session))
        debug_graph(self.debug, rtpmixer.pipeline, 'rtpstream_start_%d' % self.session)

    def _on_ssrc_srcpad_added(self, srcpad):
        if not self.rtpdecodebin:
            self._init_rtpdecodebin()

        self._link_rtpdecodebin(srcpad)

    def _on_rtpbin_ssrc_srcpad_removed(self, rtpbin, pad):
        pass # FIXME

if __name__ == '__main__':
    Gst.init(None)
    Gst.debug_set_active(True)
    Gst.debug_set_default_threshold(Gst.DebugLevel.FIXME)
    rtpmixer = RtpMixer(debug=True)

    rtpmixer.start()

    videortpstream_caps = '\
        application/x-rtp,\
        media=video,\
        clock-rate=90000,\
        encoding-name=VP8,\
        payload=101'

    videortpstream = rtpmixer.add_stream(
        caps=videortpstream_caps,
        local_port=5000,
        remote_port=6000)

    audiortpstream_caps = '\
        application/x-rtp,\
        media=audio,\
        clock-rate=48000,\
        encoding-name=OPUS,\
        payload=100'

    audiortpstream = rtpmixer.add_stream(
        caps=audiortpstream_caps,
        local_port=5002,
        remote_port=6001)

    GLib.MainLoop().run()
