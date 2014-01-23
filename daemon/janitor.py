__author__ = 'Daniel Alkemic Czuba <dc@danielczuba.pl>'

from daemon import Daemon
import time
import sqlite3
import signal
from collect import MemoryCollect
from data import config

conn = sqlite3.connect(config.SQLITE_PATH)

collectors = (
    MemoryCollect(conn),
)


class JanitorDaemon(Daemon):

    def _signal_hup(self, signum, frame):
        print 'Got HUP signal:', signum, frame

    def run(self):
        signal.signal(signal.SIGHUP, self._signal_hup)

        for collector in collectors:
            if not collector.is_installed():
                collector.install()

        while True:
            for collector in collectors:
                collector.collect()

            time.sleep(config.INTERVAL)
