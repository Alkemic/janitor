# -*- coding:utf-8 -*-
from abc import abstractmethod, ABCMeta


class BaseNotification(object):
    """
    Base notification class
    """

    __metaclass__ = ABCMeta

    def __init__(self):
        raise NotImplementedError

    @abstractmethod
    def send_notification(self, sender, message):
        """
        Method to call to send notification

        :param message:
        :type message:
        :return:
        :rtype:
        """
        pass
