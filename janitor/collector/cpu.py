# -*- coding:utf-8 -*-
"""
Classes collecting data about CPU
"""
import re
from datetime import timedelta, datetime

from janitor.collector.base import BaseCollect


class CPULoadCollect(BaseCollect):
    """
    Collect CPU load
    """
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

    def __init__(self, connection, alerts=None):
        self.time_list = self.get_time_list()
        super(CPULoadCollect, self).__init__(connection, alerts)

    @property
    def count_cores(self):
        """
        Return information about cores

        :return: Cores count
        :rtype: int
        """
        self.proc_stat_fd.seek(0)

        return sum(tuple(
            1
            for line in self.proc_stat_fd.readlines()
            if re.match('cpu\d+.*', line)
        ))

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
        # dirty fix, when we want to quickly read second time, we have problem,
        # because delta is 0
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
            delta_times[k] = [
                (t2 - t1)
                for t1, t2 in zip(self.time_list[k], current_time_list[k])
            ]

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
            dt_load = (idle_time / total_time) if total_time > 0 else 1
            cpu_loads[k] = 1 - (dt_load)

        return cpu_loads

    def sort_values(self, cpu, cpu0=None, cpu1=None, cpu2=None, cpu3=None,
                    cpu4=None, cpu5=None, cpu6=None, cpu7=None):
        """
        Small helper, I need tuple in correct order

        :param cpu:
        :type cpu:
        :param cpu0:
        :type cpu0:
        :param cpu1:
        :type cpu1:
        :param cpu2:
        :type cpu2:
        :param cpu3:
        :type cpu3:
        :param cpu4:
        :type cpu4:
        :param cpu5:
        :type cpu5:
        :param cpu6:
        :type cpu6:
        :param cpu7:
        :type cpu7:
        :return: Tuple
        :rtype: tuple
        """
        return cpu, cpu0, cpu1, cpu2, cpu3, cpu4, cpu5, cpu6, cpu7

    def collect(self):
        cpu, cpu0, cpu1, cpu2, cpu3, cpu4, cpu5, cpu6, cpu7 = \
            tuple(
                (p if p else 0) * 100.0
                for p in self.sort_values(**self.get_cpu_load())
            )

        data_to_insert = (
            self.table_name,
            cpu,
            cpu0,
            cpu1,
            cpu2,
            cpu3,
            cpu4,
            cpu5,
            cpu6,
            cpu7,
        )

        sql = 'insert into %s ' \
              '(cpu, cpu0, cpu1, cpu2, cpu3, cpu4, cpu5, cpu6, cpu7) ' \
              'values (%f, %f, %f, %f, %f, %f, %f, %f, %f);'

        self.cursor.execute(sql % data_to_insert)
        self.connection.commit()

    def get_data(self, limit=30, interval=10):
        limit_date = datetime.now()-timedelta(days=limit)
        params = {
            'interval': interval,
            'table_name': self.table_name,
            'limit_date': limit_date.strftime('%Y-%m-%d'),
        }

        sql = 'select ' \
              ' strftime(\'%%Y-%%m-%%d %%H:\', created_at) || ' \
              '   (strftime(\'%%M\', created_at)/%(interval)s) || ' \
              '   \'0:00\' as timestamp, ' \
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
              ';' % params

        return self.prepare_result(self.cursor.execute(sql).fetchall())
