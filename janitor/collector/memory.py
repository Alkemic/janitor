# -*- coding:utf-8 -*-
from datetime import timedelta, datetime

from janitor.collector.base import BaseCollect


CREATE_SQL = (
    'create table %s ('
    '  id INTEGER PRIMARY KEY AUTOINCREMENT, '
    '  physical_total INTEGER, '
    '  physical_used INTEGER, '
    '  physical_buffers INTEGER, '
    '  physical_cache INTEGER, '
    '  swap_total INTEGER, '
    '  swap_used INTEGER, '
    '  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
    ');'
)

INSERT_SQL = (
    'insert into %s ('
    '  physical_total, physical_used, physical_buffers,'
    '  physical_cache, swap_total, swap_used'
    ') '
    'VALUES (%i, %i, %i, %i, %i, %i)'
)

FETCH_DATA_SQL = (
    'select '
    ' strftime(\'%%Y-%%m-%%d %%H:\', created_at) || '
    '   (strftime(\'%%M\', created_at)/%(interval)s) || '
    '   \'0:00\' as timestamp, '
    '  cast(avg(physical_total)/1024 as integer) as physical_total, '
    '  cast(avg(physical_used)/1024 as integer) as physical_used, '
    '  cast(avg(physical_buffers)/1024 as integer) as physical_buffers, '
    '  cast(avg(physical_cache)/1024 as integer) as physical_cache, '
    '  cast(avg(swap_total)/1024 as integer) as swap_total, '
    '  cast(avg(swap_used)/1024 as integer) as swap_used '
    'from %(table_name)s '
    'where DATE(created_at) > \'%(limit_date)s\' '
    'group by strftime(\'%%Y%%m%%d%%H0\', created_at) + '
    '  strftime(\'%%M\', created_at)/%(interval)s'
    ';'
)


class MemoryCollect(BaseCollect):
    chart_name = 'Memory usage'

    table_name = 'memory_usage'

    column_description = (
        ('physical_total', 'number', 'Total physical memory'),
        ('physical_used', 'number', 'Memory used'),
        ('physical_buffers', 'number', 'Memory used for buffers'),
        ('physical_cache', 'number', 'Memory used for cache'),
        ('swap_total', 'number', 'Total available SWAP'),
        ('swap_used', 'number', 'Used SWAP'),
    )

    last_reading = ()

    def install(self):
        sql = CREATE_SQL % self.table_name
        self.cursor.execute(sql)
        self.connection.commit()

    def collect(self):
        swap_total, swap_used, mem_total, mem_free, mem_buffers, mem_cache = \
            self.get_memory_usage()

        data_to_insert = (
            self.table_name,
            mem_total,
            mem_free,
            mem_buffers,
            mem_cache, swap_total, swap_used,
        )

        self.cursor.execute(INSERT_SQL % data_to_insert)
        self.connection.commit()

    def get_memory_usage(self):
        swap_total = swap_total = swap_free = mem_total = mem_free = \
            mem_buffers = mem_cache = 0

        with open('/proc/meminfo', 'r') as f:
            mem_total = mem_free = mem_buffers = \
                mem_cache = swap_total = swap_free = None
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

                have_values = all((
                    mem_total, mem_free, mem_buffers,
                    mem_cache, swap_total, swap_free,
                ))
                if have_values:
                    break

            self.last_reading = (
                swap_total, swap_total - swap_free,
                mem_total, mem_free, mem_buffers, mem_cache,
            )

            return self.last_reading

    def get_data(self, limit=30, interval=10):
        limit_date = datetime.now()-timedelta(days=limit)
        sql = FETCH_DATA_SQL % {
            'interval': interval,
            'table_name': self.table_name,
            'limit_date': limit_date.strftime('%Y-%m-%d'),
        }

        return self.prepare_result(self.cursor.execute(sql).fetchall())

    def get_ram_usage(self):
        total_mem = self.last_reading[2]
        used_mem = (self.last_reading[2] - self.last_reading[3])
        return (used_mem * 1.0 / total_mem) * 100.0
