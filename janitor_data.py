#!/usr/bin/env python
__author__ = 'Daniel Alkemic Czuba <dc@danielczuba.pl>'

import sys
import sqlite3
from daemon.collect import MemoryCollect
from data import config


def main(argv):
    conn = sqlite3.connect(config.SQLITE_PATH)

    collectors = (
        MemoryCollect(conn),
    )

    for collector in collectors:
        print collector.get_data()

if __name__ == '__main__':
    main(sys.argv)
