#-*- coding:utf-8 -*-
import re
import sqlite3

__author__ = 'Daniel Alkemic Czuba <dc@danielczuba.pl>'


class BaseCollect(object):
    """
    Base class
    """

    connection = None
    cursor = None
    table_name = None

    def __init__(self, connection):
        """
        :type connection sqlite3.Connection
        """
        if not isinstance(connection, sqlite3.Connection):
            raise Exception('connection must be instance of sqlite3.Connection')

        self.connection = connection
        self.cursor = connection.cursor()

    def is_installed(self):
        """
        This method is called before collection loop, to check if this collector has it's tables, files, etc created or
        installed. If return False, then method self.install() will be called
        """
        sql = 'SELECT name FROM sqlite_master WHERE type=\'table\' AND name=\'%s\';' % self.table_name
        result = self.cursor.execute(sql).fetchone()
        return result and result.__len__() > 0

    def install(self):
        """
        This method installs collector
        """
        pass

    def collect(self):
        """
        Method called in big while(True) loop, to gather and save data to db
        """
        pass

    def get_data(self, time='1 month', interval=10):
        """
        Method used to retreive data
        """
        pass


class CPUCollect(BaseCollect):
    table_name = 'cpu_usage'

    column_description = (
        ('la1', 'Load avg. from last 1 min.'),
        ('la5', 'Load avg. from last 5 min.'),
        ('la15', 'Load avg. from last 15 min.'),
    )

    def install(self):
        sql = 'create table %s (' \
              '  id INTEGER PRIMARY KEY AUTOINCREMENT, ' \
              '  physical_total INTEGER, ' \
              '  physical_used INTEGER, ' \
              '  physical_buffers INTEGER, ' \
              '  physical_cache INTEGER, ' \
              '  swap_total INTEGER, ' \
              '  swap_used INTEGER, ' \
              '  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP' \
              ');' % self.table_name
        self.cursor.execute(sql)
        self.connection.commit()

    def get_load_avg(self):
        with open('/proc/meminfo', 'r') as fh:
            la = fh.read()
            la_dict = re.match('(?P<la1>\d+\.\d+) (?P<la5>\d+\.\d+) (?P<la15>\d+\.\d+) .*', la).groupdict()

        return la_dict['la 1'], la_dict['la5'], la_dict['la15']


class MemoryCollect(BaseCollect):
    table_name = 'memory_usage'

    column_description = (
        ('physical_total', 'Total physical memory'),
        ('physical_used', 'Memory used'),
        ('physical_buffers', 'Memory used for buffers'),
        ('physical_cache', 'Memory used for cache'),
        ('swap_total', 'Total available SWAP'),
        ('swap_used', 'Used SWAP')
    )

    def install(self):
        sql = 'create table %s (' \
              '  id INTEGER PRIMARY KEY AUTOINCREMENT, ' \
              '  physical_total INTEGER, ' \
              '  physical_used INTEGER, ' \
              '  physical_buffers INTEGER, ' \
              '  physical_cache INTEGER, ' \
              '  swap_total INTEGER, ' \
              '  swap_used INTEGER, ' \
              '  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP' \
              ');' % self.table_name
        self.cursor.execute(sql)
        self.connection.commit()

    def collect(self):
        swap_total, swap_used, mem_total, mem_free, mem_buffers, mem_cache = self.get_memory_usage()

        data_to_insert = (self.table_name, mem_total, mem_free, mem_buffers, mem_cache, swap_total, swap_used)

        self.cursor.execute('insert into %s (physical_total, physical_used, physical_buffers, physical_cache, '
                            'swap_total, swap_used) VALUES (%i, %i, %i, %i, %i, %i)' % data_to_insert)
        self.connection.commit()

    def get_memory_usage(self):
        with open('/proc/meminfo', 'r') as f:
            mem_total = mem_free = mem_buffers = mem_cache = swap_total = swap_free = None
            for line in f:
                if line.startswith('SwapTotal:'):
                    swap_total = int(line.split()[1])
                elif line.startswith('SwapFree:'):
                    swap_free = int(line.split()[1])
                elif line.startswith('MemTotal:'):
                    mem_total = int(line.split()[1])
                elif line.startswith('MemFree:'):
                    mem_free = int(line.split()[1])
                elif line.startswith('Cached:'):
                    mem_cache = int(line.split()[1])
                elif line.startswith('Buffers:'):
                    mem_buffers = int(line.split()[1])

                if mem_buffers is not None and mem_cache is not None and mem_free is not None and mem_total is not None and swap_total is not None and swap_free is not None:
                    break

            return swap_total, swap_total - swap_free, mem_total, mem_free, mem_buffers, mem_cache

    def get_data(self, time='1 month', interval=10):
        sql = 'select ' \
              '  cast(avg(physical_total)/1024 as integer) as physical_total, ' \
              '  cast(avg(physical_used)/1024 as integer) as physical_used, ' \
              '  cast(avg(physical_buffers)/1024 as integer) as physical_buffers, ' \
              '  cast(avg(physical_cache)/1024 as integer) as physical_cache, ' \
              '  cast(avg(swap_total)/1024 as integer) as swap_total, ' \
              '  cast(avg(swap_used)/1024 as integer) as swap_used, ' \
              '  strftime(\'%%Y-%%m-%%d %%H:\', created_at) || ' \
              '    (strftime(\'%%M\', created_at)/%(interval)s) || \'0\' as timestamp ' \
              'from %(table_name)s ' \
              'group by strftime(\'%%Y%%m%%d%%H0\', created_at) + ' \
              '  strftime(\'%%M\', created_at)/%(interval)s;' % {'interval': interval, 'table_name': self.table_name}

        result = self.cursor.execute(sql).fetchall()

        return {
            'column_description': self.column_description + (('timestamp', 'Average for timestamp'),),
            'data': result
        }
