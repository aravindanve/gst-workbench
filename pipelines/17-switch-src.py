#!/usr/bin/env python3

import gi
import signal
import sys
from threading import Thread, Event

gi.require_version('Gst', '1.0')

from gi.repository import Gst, GLib

class IntervalTimer(Thread):
    def __init__(self, callback, interval=0.5, stopFlag=Event()):
        super().__init__()
        self.callback = callback
        self.stopFlag = stopFlag

    def run(self):
        while not self.stopFlag.wait(0.5):
            self.callback()

class Switcher:
    def __init__(self):
        print('Switcher.__init__')
        pipeline = Gst.Pipeline('switcher')

        src0 = Gst.ElementFactory.make('videotestsrc')
        src0.set_property('is-live', 'true')
        src0.set_property('pattern', 'snow')
        pipeline.add(src0)

        src1 = Gst.ElementFactory.make('videotestsrc')
        src1.set_property('is-live', 'true')
        src1.set_property('pattern', 'pinwheel')
        pipeline.add(src1)

        selector = Gst.ElementFactory.make('input-selector', 'selector')
        pipeline.add(selector)

        videosink = Gst.ElementFactory.make('autovideosink', 'videosink')
        pipeline.add(videosink)

        selector.link(videosink)
        src0.link_filtered(selector, Gst.caps_from_string(
            'video/x-raw,width=640,height=360'))
        src1.link_filtered(selector, Gst.caps_from_string(
            'video/x-raw,width=640,height=360'))

        # connect event listeners
        bus = pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect('message', self.on_message)

        def switch():
            active_pad = selector.get_property('active-pad')
            print(active_pad)
            for pad in selector.sinkpads:
                if pad != active_pad:
                    selector.set_property('active-pad', pad)
                    break

        timerStopFlag = Event()
        timer = IntervalTimer(switch, 2, timerStopFlag)
        timer.start()

        # start pipeline
        pipeline.set_state(Gst.State.PLAYING)
        self.pipeline = pipeline
        self.destroyed = False
        self.timerStopFlag = timerStopFlag
        self.timer = timer

    def on_message(self, bus, message):
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
            self.timerStopFlag.set()

if __name__ == '__main__':
    Gst.init(None)
    switcher = Switcher()

    def on_sigint(sig, frame):
        print('Received SIGINT, exiting...')
        switcher.destroy()
        sys.exit(0)

    signal.signal(signal.SIGINT, on_sigint)
    GLib.MainLoop().run()
