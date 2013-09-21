# -*- coding: utf-8 -*-

import pyaudio

from twisted.internet import reactor


WIDTH = 2
CHANNELS = 2
RATE = 44100

p = pyaudio.PyAudio()


def callback(in_data, frame_count, time_info, status):
    return (in_data, pyaudio.paContinue)


stream = p.open(format=p.get_format_from_width(WIDTH),
                channels=CHANNELS,
                rate=RATE,
                input=True,
                output=True,
                stream_callback=callback)
reactor.callWhenRunning(stream.start_stream)
reactor.run()
