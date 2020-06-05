# -*- coding: utf-8 -*-


class PlayBookResultsCollectorWebSocket:
    STDOUT = 'stdout'

    def __init__(self, websocket, *args, **kwargs):
        self.websocket = websocket

    def save_msg(self, msg):
        self.websocket.send_msg(msg, self.websocket.logId)

    def format_event(self, event: dict):
        if self.STDOUT in event.keys():
            self.save_msg(event[self.STDOUT])
