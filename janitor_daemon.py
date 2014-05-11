#!/usr/bin/env python
#-*- coding:utf-8 -*-
import sys
from daemon.janitor import JanitorDaemon
from data import config

__author__ = 'Daniel Alkemic Czuba <dc@danielczuba.pl>'


if __name__ == '__main__':
    daemon = JanitorDaemon(config.PID_FILE, stdout='%s/log/stdout.log' % config.PROJECT_ROOT, stderr='%s/log/stderr.log' % config.PROJECT_ROOT)
    if len(sys.argv) == 2:
        if 'start' == sys.argv[1]:
            daemon.start()
            print 'Starting daemon \'%s\', pid: %i' % (sys.argv[0], daemon.get_pid())
        elif 'stop' == sys.argv[1]:
            daemon_pid = daemon.get_pid()
            if daemon_pid is not None:
                print 'Stopping daemon \'%s\', pid: %i' % (sys.argv[0], daemon.get_pid())
            else:
                print 'Error during stopping daemon!'
            daemon.stop()
        elif 'restart' == sys.argv[1]:
            daemon_pid = daemon.get_pid()
            if daemon_pid is not None:
                print 'Restarting daemon \'%s\', pid: %i' % (sys.argv[0], daemon.get_pid())
            else:
                print 'Error during restarting daemon!'
            daemon.restart()
        elif 'status' == sys.argv[1]:
            daemon_pid = daemon.get_pid()
            if daemon_pid is not None:
                print 'Daemon is running, pid: %i' % daemon.get_pid()
            else:
                print 'Daemon is not running.'
        else:
            print 'Unknown command'
            sys.exit(2)
        sys.exit(0)
    else:
        print 'usage: %s start|stop|restart|status' % sys.argv[0]
        sys.exit(2)
