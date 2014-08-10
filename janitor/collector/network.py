# -*- coding:utf-8 -*-
from datetime import timedelta, datetime

from janitor.collector.base import BaseCollect
from janitor.utils import json_dumps

INSTALL_SQL = (
    'create table %s ('
    '  id INTEGER PRIMARY KEY AUTOINCREMENT, '
    '  rx_bytes INTEGER, '
    '  tx_bytes INTEGER, '
    '  rx_packets INTEGER, '
    '  tx_packets INTEGER, '
    '  rx_bytes_delta INTEGER, '
    '  tx_bytes_delta INTEGER, '
    '  rx_packets_delta INTEGER, '
    '  tx_packets_delta INTEGER, '
    '  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
    ');'
)
INSERT_SQL = (
    'insert into %s ('
    '  rx_bytes, tx_bytes, rx_packets, tx_packets, '
    '  rx_bytes_delta, tx_bytes_delta, rx_packets_delta, tx_packets_delta) '
    'VALUES (%i, %i, %i, %i, %i, %i, %i, %i)'
)

FETCH_DATA_SQL = (
    'select '
    ' strftime(\'%%Y-%%m-%%d %%H:\', created_at) || '
    '   (strftime(\'%%M\', created_at)/%(interval)s) || '
    '   \'0:00\' as timestamp, '
    '  round(rx_bytes/1024, 2) as rx_bytes, '
    '  round(tx_bytes/1024, 2) as tx_bytes, '
    '  round(rx_packets/1024, 2) as rx_packets, '
    '  round(tx_packets/1024, 2) as tx_packets, '
    '  round(sum(rx_bytes_delta)/1024, 2) as rx_bytes, '
    '  round(sum(tx_bytes_delta)/1024, 2) as tx_bytes, '
    '  sum(rx_packets_delta) as rx_packets, '
    '  sum(tx_packets_delta)as tx_packets '
    'from %(table_name)s '
    'where DATE(created_at) > \'%(limit_date)s\' '
    'group by strftime(\'%%Y%%m%%d%%H0\', created_at) + '
    '  strftime(\'%%M\', created_at)/%(interval)s;'
)


class NetworkCollect(BaseCollect):
    time_list = None

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

    def __init__(self, connection, alerts=None, interface='eth0'):
        self.interface = interface
        self.network_stats = self.get_interface_stats()
        super(NetworkCollect, self).__init__(connection, alerts)

    def get_interface_stats(self):
        self.network_stats_fd.seek(0)
        for line in self.network_stats_fd.readlines()[2:]:
            line = line.split(':')
            if line[0].strip() == self.interface:
                counters = line[1].split()
                return {
                    'rx_bytes': int(counters[0]),
                    'tx_bytes': int(counters[8]),
                    'rx_packets': int(counters[1]),
                    'tx_packets': int(counters[9]),
                }

        raise Exception('The interface `%s` is missing!' % self.interface)

    def get_delta_stats(self):
        current_network_stats = self.get_interface_stats()
        delta_stats = {
            '%s_delta' % k: current_network_stats[k] - self.network_stats[k]
            for k in self.network_stats
        }
        self.network_stats = current_network_stats
        return delta_stats['rx_bytes_delta'], \
            delta_stats['tx_bytes_delta'], \
            delta_stats['rx_packets_delta'], \
            delta_stats['tx_packets_delta']

    def get_current_stats(self):
        return self.network_stats['rx_bytes'], \
            self.network_stats['tx_bytes'], \
            self.network_stats['rx_packets'], \
            self.network_stats['tx_packets']

    def collect(self):
        self.cursor.execute(INSERT_SQL % (
            (self.table_name,) +
            self.get_current_stats() +
            self.get_delta_stats())
        )

        self.get_interface_stats()

    def install(self):
        sql = INSTALL_SQL % self.table_name
        self.cursor.execute(sql)
        self.connection.commit()

    def get_data(self, limit=30, interval=10):
        limit_date = datetime.now()-timedelta(days=limit)
        sql = FETCH_DATA_SQL % {
            'interval': interval,
            'table_name': self.table_name,
            'limit_date': limit_date.strftime('%Y-%m-%d'),
        }

        return self.prepare_result(self.cursor.execute(sql).fetchall())

    def get_chart_js(self, limit=30, interval=10):
        column_definition = ''
        for column_type, column_name in self.get_data_columns_description():
            column_definition += "data.addColumn('%s', '%s');\n" % (
                column_type, column_name,
            )

        chart_js_string = """
        var data = new google.visualization.DataTable();
        %(column_definition)s
        data.addRows(%(json_data)s);

        var options = {
          title: '%(chart_name)s'
        };

        var chart_%(table_name)s = new google.visualization.LineChart(
            document.getElementById('chart_%(table_name)s')
        );
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
