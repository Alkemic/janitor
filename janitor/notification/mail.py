# -*- coding:utf-8 -*-
import smtplib
from email.mime.text import MIMEText

from .base import BaseNotification


class EmailNotification(BaseNotification):
    """
    Log notifications into simple file
    """
    def __init__(self, config):
        self.config = config

    def send_notification(self, sender, message):
        msg = MIMEText("Sender: %s" % sender)

        msg['Subject'] = "Notification: %s" % message
        if 'from' in self.config:
            msg['From'] = self.config['from']
        msg['To'] = self.config['receiver']

        server = smtplib.SMTP(self.config['host'], self.config['port'])
        server.ehlo()
        server.starttls()
        server.login(self.config['user'], self.config['password'])
        server.sendmail(
            self.config['user'],
            self.config['receiver'],
            msg.as_string(),
        )
        server.quit()
