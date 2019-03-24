#!/usr/bin/env python3

from threading import Thread, Event, Timer

class IntervalTimer(Thread):
    def __init__(self, interval, callback, stopFlag=Event()):
        super().__init__()
        self.interval = interval
        self.callback = callback
        self.stopFlag = stopFlag

    def run(self):
        while not self.stopFlag.wait(self.interval):
            self.callback()

def set_interval(callback, interval):
    timer = IntervalTimer(interval, callback)
    timer.start()
    return timer.stopFlag

def clear_interval(stopFlag):
    stopFlag.set()

def set_timeout(callback, interval):
    timer = Timer(interval, callback)
    timer.start()
    return timer

def clear_timeout(timer):
    timer.cancel()
