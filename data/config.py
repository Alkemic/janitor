#-*- coding:utf-8 -*-
import os

from daemon.collect import MemoryCollect, CPULoadCollect, LoadAverageCollect, NetworkCollect

__author__ = 'Daniel Alkemic Czuba <dc@danielczuba.pl>'


PID_FILE = '/tmp/janitor.pid'
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SQLITE_FILE = 'janitor.db'
SQLITE_PATH = os.path.abspath(os.path.join(PROJECT_ROOT, 'data', SQLITE_FILE))

INTERVAL = 55

COLLECTORS = (
    (MemoryCollect, {}),
    (CPULoadCollect, {}),
    (LoadAverageCollect, {}),
    (NetworkCollect, {'interface': 'wlan0'}),
)

JANITOR_DATA_BIND_TO = ('', 9999)
