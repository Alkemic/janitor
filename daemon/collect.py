#-*- coding:utf-8 -*-
import json
import re
import sqlite3

from datetime import timedelta, datetime, date

__author__ = 'Daniel Alkemic Czuba <dc@danielczuba.pl>'


class __JSONDateEncoder__(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return '**new Date(%i,%i,%i,%i,%i,%i)' % (obj.year, obj.month-1, obj.day, obj.hour, obj.minute, obj.second)
        if isinstance(obj, date):
            return '**new Date(%i,%i,%i)' % (obj.year, obj.month-1, obj.day)
        return json.JSONEncoder.default(self, obj)


def json_dumps(obj):
    """ A (simple)json wrapper that can wrap up python datetime and date
    objects into Javascript date objects.
    @param obj: the python object (possibly containing dates or datetimes) for
        (simple)json to serialize into JSON

    @returns: JSON version of the passed object
    """
    __jsdateregexp__ = re.compile(r'"\*\*(new Date\([0-9,]+\))"')
    out = __jsdateregexp__.sub(r'\1', json.dumps(obj, cls=__JSONDateEncoder__))
    return unicode(out).decode('utf-8')


class BaseCollect(object):
    """
    Base class
    """

    chart_name = None
    connection = None
    cursor = None
    table_name = None
    column_description = None

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
        raise Exception('You have to override `install` method in `%s` class' % self.__class__.__name__)

    def collect(self):
        """
        Method called in big while(True) loop, to gather and save data to db
        """
        raise Exception('You have to override `collect` method in `%s` class' % self.__class__.__name__)

    def get_data(self, limit=30, interval=10):
        """
        Method used to retrieve data
        """
        raise Exception('You have to override `get_data` method in `%s` class' % self.__class__.__name__)

    def get_data_columns_description(self):
        columns_description = (('datetime', 'Timestamp'), )

        for column_name, column_type, column_label in self.column_description:
            columns_description += ((column_type, column_label),)

        return columns_description

    def get_chart_js(self, limit=30, interval=10):
        column_definition = ''
        for column_type, column_name in self.get_data_columns_description():
            column_definition += "data.addColumn('%s', '%s');\n" % (column_type, column_name)

        chart_js_string = """
        var data = new google.visualization.DataTable();
        %(column_definition)s
        data.addRows(%(json_data)s);

        var options = {
          title: '%(chart_name)s'
        };

        var chart_%(table_name)s = new google.visualization.LineChart(document.getElementById('chart_%(table_name)s'));
        chart_%(table_name)s.draw(data, options);
        """

        return chart_js_string % {
            'column_definition': column_definition,
            'table_name': self.table_name,
            'json_data': json_dumps(self.get_data(limit, interval)),
            'chart_name': self.chart_name
        }

    def get_chart_div(self):
        return '<div id="chart_%s" class="chart"></div>' % self.table_name

    def prepare_result(self, fetched_rows):
        result = []

        for row in fetched_rows:
            row = list(row)
            row[0] = datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S')
            result.append(row)

        return result


class LoadAverageCollect(BaseCollect):
    chart_name = 'Load average'

    table_name = 'load_average'

    column_description = (
        ('la1', 'number', 'Load avg. from last 1 min.'),
        ('la5', 'number', 'Load avg. from last 5 min.'),
        ('la15', 'number', 'Load avg. from last 15 min.'),
    )

    def install(self):
        sql = 'create table %s (' \
              '  id INTEGER PRIMARY KEY AUTOINCREMENT, ' \
              '  la1 REAL, ' \
              '  la5 REAL, ' \
              '  la15 REAL, ' \
              '  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP' \
              ');' % self.table_name
        self.cursor.execute(sql)
        self.connection.commit()

    def get_load_avg(self):
        with open('/proc/loadavg', 'r') as fh:
            la = fh.read()
            la_dict = re.match('(?P<la1>\d+\.\d+) (?P<la5>\d+\.\d+) (?P<la15>\d+\.\d+) .*', la).groupdict()

        return float(la_dict['la1']), float(la_dict['la5']), float(la_dict['la15'])

    def collect(self):
        la1, la5, la15 = self.get_load_avg()

        data_to_insert = (self.table_name, la1, la5, la15)

        self.cursor.execute('insert into %s (la1, la5, la15) VALUES (%f, %f, %f)' % data_to_insert)
        self.connection.commit()

    def get_data(self, limit=30, interval=10):
        limit_date = datetime.now()-timedelta(days=limit)
        sql = 'select ' \
              ' strftime(\'%%Y-%%m-%%d %%H:\', created_at) || ' \
              '   (strftime(\'%%M\', created_at)/%(interval)s) || \'0:00\' as timestamp, ' \
              '  round(avg(la1), 2) as la1, ' \
              '  round(avg(la5), 2) as la5, ' \
              '  round(avg(la15), 2) as la15 ' \
              'from %(table_name)s ' \
              'where DATE(created_at) > \'%(limit_date)s\' ' \
              'group by strftime(\'%%Y%%m%%d%%H0\', created_at) + ' \
              '  strftime(\'%%M\', created_at)/%(interval)s' \
              ';' % {'interval': interval, 'table_name': self.table_name, 'limit_date': limit_date.strftime('%Y-%m-%d')}

        return self.prepare_result(self.cursor.execute(sql).fetchall())


class CPULoadCollect(BaseCollect):
    chart_name = 'CPU usage'

    table_name = 'cpu_usage'

    time_list = None

    proc_stat_fd = file("/proc/stat", "r")

    # in /proc/stat each core/thread is name as cpu#
    column_description = (
        ('cpu', 'number', 'Total percentage usage'),
        ('cpu0', 'number', '#1 percentage usage'),
        ('cpu1', 'number', '#2 percentage usage'),
        ('cpu2', 'number', '#3 percentage usage'),
        ('cpu3', 'number', '#4 percentage usage'),
        ('cpu4', 'number', '#5 percentage usage'),
        ('cpu5', 'number', '#6 percentage usage'),
        ('cpu6', 'number', '#7 percentage usage'),
        ('cpu7', 'number', '#8 percentage usage'),
    )

    def __init__(self, connection):
        self.time_list = self.get_time_list()
        super(CPULoadCollect, self).__init__(connection)

    def install(self):
        sql = 'create table %s (' \
              '  id INTEGER PRIMARY KEY AUTOINCREMENT, ' \
              '  cpu REAL, ' \
              '  cpu0 REAL, ' \
              '  cpu1 REAL NULL, ' \
              '  cpu2 REAL NULL, ' \
              '  cpu3 REAL NULL, ' \
              '  cpu4 REAL NULL, ' \
              '  cpu5 REAL NULL, ' \
              '  cpu6 REAL NULL, ' \
              '  cpu7 REAL NULL, ' \
              '  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP' \
              ');' % self.table_name
        self.cursor.execute(sql)
        self.connection.commit()

    def get_time_list(self):
        """
        http://www.linuxhowtos.org/System/procstat.htm
        """
        # dirty fix, when we want to quickly read secound time, we have problem, because delta is 0
        self.proc_stat_fd.seek(0)
        cpu_times = {}
        for line in self.proc_stat_fd.readlines():
            if not line.startswith('cpu'):
                continue

            columns = line.split(' ')
            cpu_times[columns[0]] = map(int, filter(None, columns[1:]))

        return cpu_times

    def get_delta_time(self):
        """
        Return difference of cpu stats between last call and current call
        """
        current_time_list = self.get_time_list()
        delta_times = {}
        for k in current_time_list.keys():
            delta_times[k] = [(t2 - t1) for t1, t2 in zip(self.time_list[k], current_time_list[k])]

        self.time_list = current_time_list

        return delta_times

    def get_cpu_load(self):
        """
        Returns load of all CPus in system
        """
        delta_times = self.get_delta_time()
        cpu_loads = {}
        for k in delta_times.keys():
            dt = list(delta_times[k])
            idle_time = float(dt[3])
            total_time = sum(dt)
            cpu_loads[k] = 1 - ((idle_time / total_time) if total_time > 0 else 1)

        return cpu_loads

    def sort_values(self, cpu, cpu0=None, cpu1=None, cpu2=None, cpu3=None, cpu4=None, cpu5=None, cpu6=None, cpu7=None):
        return cpu, cpu0, cpu1, cpu2, cpu3, cpu4, cpu5, cpu6, cpu7

    def collect(self):
        cpu, cpu0, cpu1, cpu2, cpu3, cpu4, cpu5, cpu6, cpu7 = tuple((p if p else 0) * 100.0 for p in self.sort_values(**self.get_cpu_load()))
        data_to_insert = (self.table_name, cpu, cpu0, cpu1, cpu2, cpu3, cpu4, cpu5, cpu6, cpu7)

        self.cursor.execute('insert into %s (cpu, cpu0, cpu1, cpu2, cpu3, cpu4, cpu5, cpu6, cpu7) '
                            'VALUES (%f, %f, %f, %f, %f, %f, %f, %f, %f)' % data_to_insert)
        self.connection.commit()

    def get_data(self, limit=30, interval=10):
        limit_date = datetime.now()-timedelta(days=limit)
        sql = 'select ' \
              ' strftime(\'%%Y-%%m-%%d %%H:\', created_at) || ' \
              '   (strftime(\'%%M\', created_at)/%(interval)s) || \'0:00\' as timestamp, ' \
              '  round(avg(cpu),2) as cpu, ' \
              '  round(avg(cpu0),2) as cpu0, ' \
              '  round(avg(cpu1),2) as cpu1, ' \
              '  round(avg(cpu2),2) as cpu2, ' \
              '  round(avg(cpu3),2) as cpu3, ' \
              '  round(avg(cpu4),2) as cpu4, ' \
              '  round(avg(cpu5),2) as cpu5, ' \
              '  round(avg(cpu6),2) as cpu6, ' \
              '  round(avg(cpu7),2) as cpu7 ' \
              'from %(table_name)s ' \
              'where DATE(created_at) > \'%(limit_date)s\' ' \
              'group by strftime(\'%%Y%%m%%d%%H0\', created_at) + ' \
              '  strftime(\'%%M\', created_at)/%(interval)s' \
              ';' % {'interval': interval, 'table_name': self.table_name, 'limit_date': limit_date.strftime('%Y-%m-%d')}

        return self.prepare_result(self.cursor.execute(sql).fetchall())


class MemoryCollect(BaseCollect):
    chart_name = 'Memory usage'

    table_name = 'memory_usage'

    column_description = (
        ('physical_total', 'number', 'Total physical memory'),
        ('physical_used', 'number', 'Memory used'),
        ('physical_buffers', 'number', 'Memory used for buffers'),
        ('physical_cache', 'number', 'Memory used for cache'),
        ('swap_total', 'number', 'Total available SWAP'),
        ('swap_used', 'number', 'Used SWAP')
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

    def get_data(self, limit=30, interval=10):
        limit_date = datetime.now()-timedelta(days=limit)
        sql = 'select ' \
              ' strftime(\'%%Y-%%m-%%d %%H:\', created_at) || ' \
              '   (strftime(\'%%M\', created_at)/%(interval)s) || \'0:00\' as timestamp, ' \
              '  cast(avg(physical_total)/1024 as integer) as physical_total, ' \
              '  cast(avg(physical_used)/1024 as integer) as physical_used, ' \
              '  cast(avg(physical_buffers)/1024 as integer) as physical_buffers, ' \
              '  cast(avg(physical_cache)/1024 as integer) as physical_cache, ' \
              '  cast(avg(swap_total)/1024 as integer) as swap_total, ' \
              '  cast(avg(swap_used)/1024 as integer) as swap_used ' \
              'from %(table_name)s ' \
              'where DATE(created_at) > \'%(limit_date)s\' ' \
              'group by strftime(\'%%Y%%m%%d%%H0\', created_at) + ' \
              '  strftime(\'%%M\', created_at)/%(interval)s' \
              ';' % {'interval': interval, 'table_name': self.table_name, 'limit_date': limit_date.strftime('%Y-%m-%d')}

        return self.prepare_result(self.cursor.execute(sql).fetchall())


class NetworkCollect(BaseCollect):
    time_list = None

    interface = 'eth0'

    network_stats_fd = open('/proc/net/dev', 'r')

    network_stats = None

    column_description = (
        ('rx_bytes', 'number', 'Total received data'),
        ('tx_bytes', 'number', 'Total transferred data'),
        ('rx_packets', 'number', 'Total received pockets'),
        ('tx_packets', 'number', 'Total transferred pockets'),
        ('rx_bytes_delta', 'number', 'Received data'),
        ('tx_bytes_delta', 'number', 'Transferred data'),
        ('rx_packets_delta', 'number', 'Received pockets'),
        ('tx_packets_delta', 'number', 'Transferred pockets'),
    )

    @property
    def table_name(self):
        return 'network_%s_usage' % self.interface

    @property
    def chart_name(self):
        return 'Network usage on %s' % self.interface

    def __init__(self, connection, interface='eth0'):
        self.interface = interface
        self.network_stats = self.get_interface_stats()
        super(NetworkCollect, self).__init__(connection)

    def get_interface_stats(self):
        self.network_stats_fd.seek(0)
        for line in self.network_stats_fd.readlines()[2:]:
            line = line.split(':')
            if line[0].strip() == self.interface:
                counters = line[1].split()
                return {'rx_bytes': int(counters[0]), 'tx_bytes': int(counters[8]), 'rx_packets': int(counters[1]),
                        'tx_packets': int(counters[9])}

        raise Exception('The interface `%s` is missing!' % self.interface)

    def get_delta_stats(self):
        current_network_stats = self.get_interface_stats()
        delta_stats = dict(('%s_delta' % k, current_network_stats[k] - self.network_stats[k]) for k in self.network_stats)
        self.network_stats = current_network_stats
        return delta_stats['rx_bytes_delta'], delta_stats['tx_bytes_delta'], delta_stats['rx_packets_delta'], \
               delta_stats['tx_packets_delta']

    def get_current_stats(self):
        return self.network_stats['rx_bytes'], self.network_stats['tx_bytes'], self.network_stats['rx_packets'], \
               self.network_stats['tx_packets']

    def collect(self):
        self.cursor.execute('insert into %s (rx_bytes, tx_bytes, rx_packets, tx_packets, rx_bytes_delta, tx_bytes_delta, rx_packets_delta, tx_packets_delta) '
                            'VALUES (%i, %i, %i, %i, %i, %i, %i, %i)' %
                            ((self.table_name,) + self.get_current_stats() + self.get_delta_stats()))

        self.get_interface_stats()

    def install(self):
        sql = 'create table %s (' \
              '  id INTEGER PRIMARY KEY AUTOINCREMENT, ' \
              '  rx_bytes INTEGER, ' \
              '  tx_bytes INTEGER, ' \
              '  rx_packets INTEGER, ' \
              '  tx_packets INTEGER, ' \
              '  rx_bytes_delta INTEGER, ' \
              '  tx_bytes_delta INTEGER, ' \
              '  rx_packets_delta INTEGER, ' \
              '  tx_packets_delta INTEGER, ' \
              '  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP' \
              ');' % self.table_name
        self.cursor.execute(sql)
        self.connection.commit()

    def get_data(self, limit=30, interval=10):
        limit_date = datetime.now()-timedelta(days=limit)
        sql = 'select ' \
              ' strftime(\'%%Y-%%m-%%d %%H:\', created_at) || ' \
              '   (strftime(\'%%M\', created_at)/%(interval)s) || \'0:00\' as timestamp, ' \
              '  round(rx_bytes/1024, 2) as rx_bytes, ' \
              '  round(tx_bytes/1024, 2) as tx_bytes, ' \
              '  round(rx_packets/1024, 2) as rx_packets, ' \
              '  round(tx_packets/1024, 2) as tx_packets, ' \
              '  round(sum(rx_bytes_delta)/1024, 2) as rx_bytes, ' \
              '  round(sum(tx_bytes_delta)/1024, 2) as tx_bytes, ' \
              '  sum(rx_packets_delta) as rx_packets, ' \
              '  sum(tx_packets_delta)as tx_packets ' \
              'from %(table_name)s ' \
              'where DATE(created_at) > \'%(limit_date)s\' ' \
              'group by strftime(\'%%Y%%m%%d%%H0\', created_at) + ' \
              '  strftime(\'%%M\', created_at)/%(interval)s' \
              ';' % {'interval': interval, 'table_name': self.table_name, 'limit_date': limit_date.strftime('%Y-%m-%d')}

        return self.prepare_result(self.cursor.execute(sql).fetchall())

    def get_chart_js(self, limit=30, interval=10):
        column_definition = ''
        for column_type, column_name in self.get_data_columns_description():
            column_definition += "data.addColumn('%s', '%s');\n" % (column_type, column_name)

        chart_js_string = """
        var data = new google.visualization.DataTable();
        %(column_definition)s
        data.addRows(%(json_data)s);

        var options = {
          title: '%(chart_name)s'
        };

        var chart_%(table_name)s = new google.visualization.LineChart(document.getElementById('chart_%(table_name)s'));
        chart_%(table_name)s.draw(data, options);
        """

        return chart_js_string % {
            'column_definition': column_definition,
            'table_name': self.table_name,
            'json_data': json_dumps(self.get_data(limit, interval)),
            'chart_name': self.chart_name
        }

    def get_chart_div(self):
        return '<div id="chart_%s" class="chart"></div>' \
               '<div id="chart_%s_total" class="chart"></div>' \
               % (self.table_name, self.table_name)
