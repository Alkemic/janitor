# -*- coding:utf-8 -*-
import re
from datetime import timedelta, datetime

from janitor.collector.base import BaseCollect

LA_PATTERN = '(?P<la1>\d+\.\d+) (?P<la5>\d+\.\d+) (?P<la15>\d+\.\d+) .*'

INSTALL_SQL = (
    'create table %s ('
    '  id INTEGER PRIMARY KEY AUTOINCREMENT, '
    '  la1 REAL, '
    '  la5 REAL, '
    '  la15 REAL, '
    '  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
    ');'
)

INSERT_SQL = 'insert into %s (la1, la5, la15) VALUES (%f, %f, %f)'

FETCH_DATA_SQL = (
    'select '
    ' strftime(\'%%Y-%%m-%%d %%H:\', created_at) || '
    '   (strftime(\'%%M\', created_at)/%(interval)s) || '
    '     \'0:00\' as timestamp, '
    '  round(avg(la1), 2) as la1, '
    '  round(avg(la5), 2) as la5, '
    '  round(avg(la15), 2) as la15 '
    'from %(table_name)s '
    'where DATE(created_at) > \'%(limit_date)s\' '
    'group by strftime(\'%%Y%%m%%d%%H0\', created_at) + '
    '  strftime(\'%%M\', created_at)/%(interval)s'
    ';'
)


class LoadAverageCollect(BaseCollect):
    chart_name = 'Load average'

    table_name = 'load_average'

    column_description = (
        ('la1', 'number', 'Load avg. from last 1 min.'),
        ('la5', 'number', 'Load avg. from last 5 min.'),
        ('la15', 'number', 'Load avg. from last 15 min.'),
    )

    def install(self):
        sql = INSTALL_SQL % self.table_name
        self.cursor.execute(sql)
        self.connection.commit()

    def get_load_avg(self):
        with open('/proc/loadavg', 'r') as fh:
            la = fh.read()
            la_dict = re.match(LA_PATTERN, la).groupdict()

        return float(la_dict['la1']), \
            float(la_dict['la5']), \
            float(la_dict['la15'])

    def collect(self):
        la1, la5, la15 = self.get_load_avg()

        data_to_insert = (self.table_name, la1, la5, la15)

        self.cursor.execute(INSERT_SQL % data_to_insert)
        self.connection.commit()

    def get_data(self, limit=30, interval=10):
        limit_date = datetime.now() - timedelta(days=limit)
        sql = FETCH_DATA_SQL % {
            'interval': interval,
            'table_name': self.table_name,
            'limit_date': limit_date.strftime('%Y-%m-%d')
        }

        return self.prepare_result(self.cursor.execute(sql).fetchall())
