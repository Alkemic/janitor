# -*- coding:utf-8 -*-
from abc import abstractmethod, ABCMeta


class BaseAlert(object):
    """
    Abstract alert class
    """

    __metaclass__ = ABCMeta

    message = None

    collector_names = None

    notifers = None

    def __init__(self, notifers):
        self.notifers = notifers or []

    @abstractmethod
    def _check(self, collector):
        pass

    def check(self, collector):
        """
        Check if conditions are meet, and fire alert
        :param collector: Given collector
        :type collector: collector.base.BaseCollector
        :return: Do fire alert?
        :rtype: bool
        """
        self.collector = collector
        if self._check(collector):
            for notifer in self.notifers:
                notifer.send_notification(self, self.message)
