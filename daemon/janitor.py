#-*- coding:utf-8 -*-
from daemon import Daemon
import time
import sqlite3
import signal

from data import config

__author__ = 'Daniel Alkemic Czuba <dc@danielczuba.pl>'


class JanitorDaemon(Daemon):
    collectors = []
    connection = None

    def __init__(self, pidfile, stdin='/dev/null', stdout='/dev/null', stderr='/dev/null', working_dir='/'):
        Daemon.__init__(self, pidfile, stdin, stdout, stderr, working_dir)
        self.connection = sqlite3.connect(config.SQLITE_PATH)

        # adding collectors to list
        for collector, collector_kwargs in config.COLLECTORS:
            self.collectors.append(collector(self.connection, **collector_kwargs))

    def _signal_hup(self, signum, frame):
        print 'Got HUP signal:', signum, frame

    def run(self):
        signal.signal(signal.SIGHUP, self._signal_hup)

        for collector in self.collectors:
            if not collector.is_installed():
                collector.install()

        while True:
            for collector in self.collectors:
                collector.collect()

            time.sleep(config.INTERVAL)
