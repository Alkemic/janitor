#!/usr/bin/env python
#-*- coding:utf-8 -*-
import sys
import sqlite3
from daemon.collect import MemoryCollect
from data import config

__author__ = 'Daniel Alkemic Czuba <dc@danielczuba.pl>'


def main(argv):
    conn = sqlite3.connect(config.SQLITE_PATH)

    collectors = (
        MemoryCollect(conn),
    )

    for collector in collectors:
        print collector.get_data()

if __name__ == '__main__':
    main(sys.argv)
