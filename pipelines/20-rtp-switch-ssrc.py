#!/usr/bin/env python3

import gi
import signal
import sys

gi.require_version('Gst', '1.0')

from gi.repository import Gst, GLib

SRC_CAPS_VP8 = 'application/x-rtp,media=video,clock-rate=90000,encoding-name=VP8,payload=101'

class Switcher:
    def __init__(self):
        print('Switcher.__init__')
        pipeline = Gst.Pipeline('switcher')

        src0 = Gst.ElementFactory.make('videotestsrc')
        src0.set_property('is-live', True)
        src0.set_property('pattern', 'snow')
        pipeline.add(src0)

        rtpbin = Gst.ElementFactory.make('rtpbin', 'rtpbin')
        rtpbin.set_property('autoremove', True)
        pipeline.add(rtpbin)

        rtpsrc = Gst.ElementFactory.make('udpsrc', 'rtpsrc')
        rtpsrc.set_property('port', 5000)
        rtpsrc.set_property('caps', Gst.caps_from_string(SRC_CAPS_VP8))
        pipeline.add(rtpsrc)

        rtcpsrc = Gst.ElementFactory.make('udpsrc', 'rtcpsrc')
        rtcpsrc.set_property('port', 5001)
        pipeline.add(rtcpsrc)

        vp8depay = Gst.ElementFactory.make('rtpvp8depay', 'vp8depay')
        vp8dec = Gst.ElementFactory.make('vp8dec', 'vp8dec')
        pipeline.add(vp8depay, vp8dec)

        # init and configure rtcpsink
        rtcpsink = Gst.ElementFactory.make('udpsink', 'rtcpsink')
        rtcpsink.set_property('port', 5002)
        rtcpsink.set_property('host', '127.0.0.1')
        rtcpsink.set_property('async', False)
        rtcpsink.set_property('sync', False)
        pipeline.add(rtcpsink)

        selector = Gst.ElementFactory.make('input-selector', 'selector')
        pipeline.add(selector)

        videosink = Gst.ElementFactory.make('autovideosink', 'videosink')
        pipeline.add(videosink)

        selector.link(videosink)
        src0.link_filtered(selector, Gst.caps_from_string(
            'video/x-raw,format=I420,width=640,height=360'))
        vp8depay.link(vp8dec)
        vp8dec.link(selector)
        Gst.Pad.link(
            Gst.Element.get_static_pad(rtpsrc, 'src'),
            Gst.Element.get_request_pad(rtpbin, 'recv_rtp_sink_0'))

        Gst.Pad.link(
            Gst.Element.get_static_pad(rtcpsrc, 'src'),
            Gst.Element.get_request_pad(rtpbin, 'recv_rtcp_sink_0'))

        Gst.Pad.link(
            Gst.Element.get_request_pad(rtpbin, 'send_rtcp_src_0'),
            Gst.Element.get_static_pad(rtcpsink, 'sink'))

        # connect event listeners
        bus = pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect('message', self.on_message)
        rtpbin.connect('pad-added', self.on_rtpbin_pad_added, vp8depay, selector)

        f = open('../dots/18-initial.dot', 'w')
        f.write(Gst.debug_bin_to_dot_data(pipeline, Gst.DebugGraphDetails.ALL))
        f.close()

        pipeline.set_state(Gst.State.PLAYING)
        self.pipeline = pipeline
        self.destroyed = False

    def on_rtpbin_pad_added(self, rtpbin, pad, depay, selector):
        print('Switcher.on_rtpbin_pad_added')
        sinkpad = Gst.Element.get_static_pad(depay, 'sink')
        if sinkpad.is_linked():
            Gst.Pad.unlink(sinkpad.get_peer(), sinkpad)
        Gst.Pad.link(pad, sinkpad)
        selector.set_property('active-pad', selector.sinkpads[-1])

        f = open('../dots/18-rtp-pad-added.dot', 'w')
        f.write(Gst.debug_bin_to_dot_data(
            self.pipeline, Gst.DebugGraphDetails.ALL))
        f.close()

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
            self.pipeline.get_bus().remove_signal_watch()
            self.pipeline = None
            self.destroyed = True

if __name__ == '__main__':
    Gst.init(None)
    Gst.debug_set_active(True)
    Gst.debug_set_default_threshold(3)
    switcher = Switcher()

    def on_sigint(sig, frame):
        print('Received SIGINT, exiting...')
        switcher.destroy()
        sys.exit(0)

    signal.signal(signal.SIGINT, on_sigint)
    GLib.MainLoop().run()
