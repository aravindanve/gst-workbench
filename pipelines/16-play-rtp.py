#!/usr/bin/env python3

import os
import gi
import signal
import sys

gi.require_version('Gst', '1.0')

from gi.repository import Gst, GObject, Gtk

mixer = None

class Mixer:
    def __init__(self):
        # create pipeline
        pipeline = Gst.Pipeline('rtp_client')

        # create and configure rtpsrc
        rtpsrc = Gst.ElementFactory.make('udpsrc', 'rtpsrc')
        rtpsrc.set_property('port', 5000)
        rtpsrc.set_property('caps',
            Gst.caps_from_string('application/x-rtp,media=video,clock-rate=90000,encoding-name=VP8,payload=101'))

        # create and configure rtcpsrc
        rtcpsrc = Gst.ElementFactory.make('udpsrc', 'rtcpsrc')
        rtcpsrc.set_property('port', 5001)

        # create and configure rtcpsink
        rtcpsink = Gst.ElementFactory.make('udpsink', 'rtcpsink')
        rtcpsink.set_property('port', 5002)
        rtcpsink.set_property('host', '127.0.0.1')
        rtcpsink.set_property('async', False)
        rtcpsink.set_property('sync', False)

        # add elements to pipeline
        pipeline.add(rtpsrc, rtcpsrc, rtcpsink)

        # other elements
        videodepay = Gst.ElementFactory.make('rtpvp8depay', 'videodepay')
        videodec = Gst.ElementFactory.make('vp8dec', 'videodec')
        videosink = Gst.ElementFactory.make('autovideosink', 'videosink')

        # add elements to pipeline
        pipeline.add(videodepay, videodec, videosink)

        videodepay.link(videodec)
        videodec.link(videosink)

        # create and configure rtpbin element
        rtpbin = Gst.ElementFactory.make('rtpbin', 'rtpbin')

        # add elements to pipeline
        pipeline.add(rtpbin)

        # link elements to rtp bin session 0
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
        rtpbin.connect('pad-added', self.on_pad_added, videodepay)

        # start pipeline
        pipeline.set_state(Gst.State.PLAYING)
        self.pipeline = pipeline

    def on_pad_added(self, rtpbin, new_pad, depay):
        Gst.Pad.link(new_pad, Gst.Element.get_static_pad(depay, 'sink'))

    def on_message(self, bus, message):
        if message.type == Gst.MessageType.EOS:
            self.pipeline.set_state(Gst.State.NULL)
            print('message:EOS')
        elif message.type == Gst.MessageType.STATE_CHANGED:
            # print('message:STATE_CHANGED', message.parse_state_changed())
            pass
        elif message.type == Gst.MessageType.STREAM_STATUS:
            # print('message:STREAM_STATUS', message.parse_stream_status())
            pass
        elif message.type == Gst.MessageType.STREAM_START:
            # print('message:STREAM_START')
            pass
        elif message.type == Gst.MessageType.ELEMENT:
            print('message:ELEMENT', message.src)
            pass
        elif message.type == Gst.MessageType.TAG:
            # print('message:TAG', message.parse_tag())
            pass
        elif message.type == Gst.MessageType.ASYNC_DONE:
            # print('message:ASYNC_DONE', message.parse_async_done())
            pass
        elif message.type == Gst.MessageType.QOS:
            # print('message:QOS', message.parse_qos())
            pass
        elif message.type == Gst.MessageType.ERROR:
            self.pipeline.set_state(Gst.State.NULL)
            err, debug = message.parse_error()
            print('message:ERROR %s' % err, debug)
        else:
            print(message.type)

    def destroy(self):
        self.pipeline.set_state(Gst.State.NULL)

def on_sigint(sig, frame):
    global mixer
    print('Received SIGINT, exiting...')
    if mixer != None:
        mixer.pipeline.get_bus().remove_signal_watch()
        mixer.destroy()
    sys.exit(0)

if __name__ == '__main__':
    signal.signal(signal.SIGINT, on_sigint)
    Gst.init(None)
    mixer = Mixer()
    GObject.MainLoop().run()
