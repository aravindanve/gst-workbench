#!/usr/bin/env python3

import re
import signal
import sys
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib

DEFAULT_UDP_HOST = '127.0.0.1'
DEFAULT_SRC_PATTERN = 'snow'
DEFAULT_SRC_CAPS = 'video/x-raw,format=I420,width=640,height=360'

def create_pipeline(name):
    return Gst.Pipeline(name)

def create_udpsrc(bin, name, port, host=DEFAULT_UDP_HOST, caps=None):
    udpsrc = Gst.ElementFactory.make('udpsrc', name)
    udpsrc.set_property('port', port)
    udpsrc.set_property('address', host)

    if caps:
        udpsrc.set_property('caps', Gst.caps_from_string(caps))

    bin.add(udpsrc)
    return udpsrc

def create_udpsink(
        bin, name, port, host=DEFAULT_UDP_HOST, sync=False, _async=False):
    udpsink = Gst.ElementFactory.make('udpsink', name)
    udpsink.set_property('port', port)
    udpsink.set_property('host', host)
    udpsink.set_property('async', False)
    udpsink.set_property('sync', False)
    bin.add(udpsink)
    return udpsink

def create_rtpsrcbin(bin, name, caps, port, host=DEFAULT_UDP_HOST):
    rtpsrcbin = Gst.Bin(name)
    bin.add(rtpsrcbin)

    rtpsrc_name = '%s_rtpsrc' % name
    rtpsrcbin.rtpsrc = create_udpsrc(rtpsrcbin, rtpsrc_name, port, host, caps)

    rtcpsrc_name = '%s_rtcpsrc' % name
    rtpsrcbin.rtcpsrc = create_udpsrc(rtpsrcbin, rtcpsrc_name, port + 1, host)

    rtcpsink_name = '%s_rtcpsink' % name
    rtpsrcbin.rtcpsink = create_udpsink(
        rtpsrcbin, rtcpsink_name, port + 2, host)

    return rtpsrcbin

def create_rtpbin(pipeline, name):
    rtpbin = Gst.ElementFactory.make('rtpbin', 'rtpbin')
    rtpbin.set_property('autoremove', True)
    pipeline.add(rtpbin)
    return rtpbin

def link_rtpsrcbin_to_rtpbin(rtpsrcbin, rtpbin, session=0):
    grtpsrcpad = Gst.GhostPad.new(
        'recv_rtp_src', rtpsrcbin.rtpsrc.get_static_pad('src'))

    rtpsrcbin.add_pad(grtpsrcpad)
    grtpsrcpad.link(rtpbin.get_request_pad('recv_rtp_sink_%d' % session))

    grtcpsrcpad = Gst.GhostPad.new(
        'recv_rtcp_src', rtpsrcbin.rtcpsrc.get_static_pad('src'))

    rtpsrcbin.add_pad(grtcpsrcpad)
    grtcpsrcpad.link(rtpbin.get_request_pad('recv_rtcp_sink_%d' % session))

    grtcpsinkpad = Gst.GhostPad.new(
        'send_rtcp_sink', rtpsrcbin.rtcpsink.get_static_pad('sink'))

    rtpsrcbin.add_pad(grtcpsinkpad)
    rtpbin.get_request_pad('send_rtcp_src_%d' % session).link(grtcpsinkpad)

def create_defaultsrc(bin, pattern=DEFAULT_SRC_PATTERN, caps=DEFAULT_SRC_CAPS):
    defaultsrc = Gst.ElementFactory.make('videotestsrc')
    defaultsrc.set_property('is-live', True)
    defaultsrc.set_property('pattern', pattern)
    bin.add(defaultsrc)
    return defaultsrc

def create_selector(bin, name):
    selector = Gst.ElementFactory.make('input-selector', name)
    bin.add(selector)
    return selector

def create_selectorbin(
        bin, name, pattern=DEFAULT_SRC_PATTERN, caps=DEFAULT_SRC_CAPS):
    selectorbin = Gst.Bin(name)
    bin.add(selectorbin)

    selectorbin.defaultsrc = create_defaultsrc(selectorbin, pattern, caps)
    selectorbin.selector = create_selector(selectorbin, '%s_selector' % name)
    selectorbin.defaultsrc.link_filtered(
        selectorbin.selector, Gst.caps_from_string(caps))

    return selectorbin

def link_selectorbin_to_element(selectorbin, element):
    gsrcpad = Gst.GhostPad.new(
        'src', selectorbin.selector.get_static_pad('src'))

    selectorbin.add_pad(gsrcpad)
    gsrcpad.link(element.get_static_pad('sink'))

def create_rtpvp8decodebin(bin, name, activated=False):
    rtpdecodebin = Gst.Bin(name)
    bin.add(rtpdecodebin)

    rtpdecodebin.depay = Gst.ElementFactory.make(
        'rtpvp8depay', '%s_depay' % name)

    rtpdecodebin.dec = Gst.ElementFactory.make(
        'vp8dec', '%s_dec' % name)

    rtpdecodebin.add(rtpdecodebin.depay)
    rtpdecodebin.add(rtpdecodebin.dec)

    gsinkpad = Gst.GhostPad.new(
        'sink', rtpdecodebin.depay.get_static_pad('sink'))

    gsrcpad = Gst.GhostPad.new(
        'src', rtpdecodebin.dec.get_static_pad('src'))

    if activated:
        gsinkpad.set_active(True)
        gsrcpad.set_active(True)
        rtpdecodebin.set_state(Gst.State.PLAYING)

    rtpdecodebin.add_pad(gsinkpad)
    rtpdecodebin.add_pad(gsrcpad)

    rtpdecodebin.depay.link(rtpdecodebin.dec)
    return rtpdecodebin

def create_rtpdecodebin(bin, name, codec, activated=False):
    if codec == 'VP8':
        return create_rtpvp8decodebin(bin, name, activated)
    else:
        raise Exception('Unsupported codec %s' % codec)

def link_rtpbinsrcpad_to_selectorbin(rtpbinsrcpad, selectorbin):
    # parse codec
    caps = rtpbinsrcpad.get_current_caps().to_string()
    match = re.search(r'encoding\-name=(?:\([^\)]+\))([^,]+)', caps)
    codec = match.group(1).strip() if match else None

    if not hasattr(selectorbin, 'next_pad_index'):
        selectorbin.next_pad_index = 0

    index = selectorbin.next_pad_index
    selectorbin.next_pad_index += 1

    if not hasattr(selectorbin, 'rtpdecodebins'):
        selectorbin.rtpdecodebins = []

    rtpdecodebin = create_rtpdecodebin(
        selectorbin, 'rtpdecodebin%d' % index, codec, True)

    selectorbin.rtpdecodebins.append(rtpdecodebin)

    selectorsinkpad = selectorbin.selector.request_pad(
        selectorbin.selector.sinkpads[0].get_pad_template(), None, None)
    rtpdecodebinsrcpad = rtpdecodebin.get_static_pad('src')
    rtpdecodebinsinkpad = rtpdecodebin.get_static_pad('sink')
    grtpdecodebinsinkpad = Gst.GhostPad.new(
        'sink_%d' % index, rtpdecodebinsinkpad)

    grtpdecodebinsinkpad.set_active(True) # we are adding to a running element
    selectorbin.add_pad(grtpdecodebinsinkpad)

    rtpdecodebinsrcpad.link(selectorsinkpad)
    rtpbinsrcpad.link(grtpdecodebinsinkpad)

    selectorbin.selector.set_property('active-pad', selectorsinkpad)

    selectorbin.next_pad_index += 1

def debug_bin_graph(bin, name):
    f = open('%s.dot' % name, 'w')
    f.write(Gst.debug_bin_to_dot_data(bin, Gst.DebugGraphDetails.ALL))
    f.close()

class RtpMixer:
    def __init__(self):
        self.destroyed = False
        self.rtpsrc_index = 0
        self.pipeline = create_pipeline('rtp_mixer')
        self.rtpbin = create_rtpbin(self.pipeline, 'rtpbin')
        self.selectorbin = create_selectorbin(self.pipeline, 'selectorbin')

        # FIXME: use rtp sink after mixing
        videosink = Gst.ElementFactory.make('autovideosink')
        self.pipeline.add(videosink)

        link_selectorbin_to_element(self.selectorbin, videosink)

        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect('message', self.on_message)
        self.rtpbin.connect('pad-added', self.on_rtpbin_pad_added)

        debug_bin_graph(self.pipeline, 'pipeline-init')

    def add_rtpsrc(self, caps, port, host=DEFAULT_UDP_HOST):
        rtpsrcbin_name = 'rtpsrc%d' % self.rtpsrc_index
        rtpsrcbin = create_rtpsrcbin(
            self.pipeline, rtpsrcbin_name, caps, port, host)

        link_rtpsrcbin_to_rtpbin(rtpsrcbin, self.rtpbin, self.rtpsrc_index)

        debug_bin_graph(
            self.pipeline, 'pipeline-rtpsrc-%d' % self.rtpsrc_index)

        self.rtpsrc_index += 1

    def remove_rtpsrc(self):
        pass

    def start(self):
        self.pipeline.set_state(Gst.State.PLAYING)

    def stop(self):
        self.pipeline.set_state(Gst.State.PAUSED)

    def on_rtpbin_pad_added(self, rtpbin, srcpad):
        print('RtpMixer.on_rtpbin_pad_added()')
        link_rtpbinsrcpad_to_selectorbin(srcpad, self.selectorbin)

        debug_bin_graph(
            self.pipeline, 'pipeline-rtpsrcpad-%d' % (self.rtpsrc_index - 1))

    def on_message(self, bus, message):
        if message.type == Gst.MessageType.QOS:
            pass
        if message.type == Gst.MessageType.EOS:
            self.destroy()
        elif message.type == Gst.MessageType.ERROR:
            self.pipeline.set_state(Gst.State.NULL)
            err, debug = message.parse_error()
            print('message:ERROR %s' % err, debug)
        else:
            print(message.type)

    def destroy(self):
        if not self.destroyed:
            self.pipeline.set_state(Gst.State.NULL)
            self.bus.remove_signal_watch()
            self.rtpsrc_index = 0
            self.pipeline = None
            self.rtpbin = None
            self.selectorbin = None
            self.destroyed = True

if __name__ == '__main__':
    Gst.init(None)
    Gst.debug_set_active(True)
    # Gst.debug_set_default_threshold(Gst.DebugLevel.INFO)
    # Gst.debug_set_default_threshold(Gst.DebugLevel.DEBUG)
    rtpmixer = RtpMixer()

    rtpmixer_caps = '\
        application/x-rtp,\
        media=video,\
        clock-rate=90000,\
        encoding-name=VP8,\
        payload=101'

    rtpmixer.add_rtpsrc(rtpmixer_caps, 5000)
    rtpmixer.start()

    def on_sigint(sig, frame):
        print('Received SIGINT, exiting...')
        rtpmixer.destroy()
        sys.exit(0)

    signal.signal(signal.SIGINT, on_sigint)
    GLib.MainLoop().run()
