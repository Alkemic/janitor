# -*- coding:utf-8 -*-
import os

from janitor.collector import (
    MemoryCollect,
    CPULoadCollect,
    LoadAverageCollect,
    NetworkCollect,
)
from janitor.alarm.ram import RamAlert
from janitor.notification.mail import EmailNotification
from janitor.notification.file import SimpleFileNotification


PID_FILE = '/tmp/janitor.pid'
PROJECT_ROOT = os.path.dirname(__file__)
SQLITE_FILE = 'janitor.db'
SQLITE_PATH = os.path.abspath(os.path.join(PROJECT_ROOT, SQLITE_FILE))

INTERVAL = 55

EMAIL_CONFIG = {
    'use_tls': True,
    'host': 'smtp.example.com',
    'port': 587,
    'user': 'user@example.com',
    'password': 'password',
    'from': 'Janitor <mail@example.com>',
    'receiver': 'Someone <mail@example.com>',
}

email_notification = EmailNotification(EMAIL_CONFIG)
file_notification = SimpleFileNotification(
    os.path.join(PROJECT_ROOT, 'log/alerts.log')
)

ram_alert = RamAlert([file_notification], 90)

COLLECTORS = {
    'memory': (MemoryCollect, {'alerts': [ram_alert]}),
    'cpu_load': (CPULoadCollect, {}),
    'load_average': (LoadAverageCollect, {}),
    'network_wlan0': (NetworkCollect, {'interface': 'wlan0'}),
}

JANITOR_DATA_BIND_TO = ('', 9999)
