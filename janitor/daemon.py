# -*- coding:utf-8 -*-
"""
Main janitor daemon file
"""
import time
import sqlite3
import signal

from janitor.utils import Daemon
import config


class JanitorDaemon(Daemon):
    """
    Main janitor daemon class
    """
    collectors = []
    connection = None

    def __init__(self, pidfile, stdin='/dev/null', stdout='/dev/null',
                 stderr='/dev/null', working_dir='/'):
        Daemon.__init__(self, pidfile, stdin, stdout, stderr, working_dir)
        self.connection = sqlite3.connect(config.SQLITE_PATH)

        # adding collectors to list
        for name, collector in config.COLLECTORS.items():
            collector, collector_kwargs = collector
            self.collectors.append(
                collector(self.connection, **collector_kwargs))

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

            for collector in self.collectors:
                collector.check_for_alerts()

            time.sleep(config.INTERVAL)
