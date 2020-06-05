# -*- coding: utf-8 -*-
import abc

from dao.dispos import DeploySaveResult


class BaseCollectorWebSocket(metaclass=abc.ABCMeta):
    STDOUT = 'stdout'

    @abc.abstractmethod
    def save_msg(self, msg):
        pass

    def format_event(self, event: dict):
        if self.STDOUT in event.keys():
            self.save_msg(event[self.STDOUT])


class ResultsCollectorWebSocket(BaseCollectorWebSocket):

    def __init__(self, websocket, *args, **kwargs):
        self.websocket = websocket

    def save_msg(self, msg):
        self.websocket.send_msg(msg, self.websocket.logId)


class ResultsCollectorBackground(BaseCollectorWebSocket):

    def __init__(self, background, *args, **kwargs):
        self.background = background

    def save_msg(self, data):
        DeploySaveResult.Model.insert(self.background, data)
