# -*- coding:utf-8 -*-
from datetime import datetime

from .base import BaseNotification


class SimpleFileNotification(BaseNotification):
    """
    Log notifications into simple file
    """
    def __init__(self, filename):
        self.file = open(filename, 'a+')

    def send_notification(self, sender, message):
        self.file.write(
            "[%s] %s: %s\n" % (
                datetime.now().isoformat(),
                str(sender),
                message,
            )
        )

        self.file.flush()
