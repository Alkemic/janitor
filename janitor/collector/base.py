# -*- coding:utf-8 -*-
import sqlite3
from abc import abstractmethod, ABCMeta
from datetime import datetime

from janitor.utils import json_dumps

CHART_JS = """
var data = new google.visualization.DataTable(),
    chart_div = document.getElementById('chart_%(table_name)s');
%(column_definition)s
data.addRows(%(json_data)s);

var options = {
  title: '%(chart_name)s'
};

var chart_%(table_name)s = new google
    .visualization.LineChart(chart_div);
chart_%(table_name)s.draw(data, options);
"""


class BaseCollect(object):
    """
    Base class
    """

    __metaclass__ = ABCMeta

    chart_name = None
    table_name = None
    column_description = None

    def __init__(self, connection, alerts=None):
        """
        :type connection sqlite3.Connection
        """
        if not isinstance(connection, sqlite3.Connection):
            raise Exception(
                'Connection must be instance of sqlite3.Connection'
            )

        alerts = alerts or []
        if not isinstance(alerts, (tuple, list)):
            alerts = [alerts]

        self.alerts = alerts
        self.connection = connection
        self.cursor = connection.cursor()

    def is_installed(self):
        """
        This method is called before collection loop, to check if this
        collector has it's tables, files, etc created or installed. If
        return False, then method self.install() will be called
        """
        sql = "SELECT name FROM sqlite_master WHERE type='table' AND " \
              "name='%s';" % self.table_name

        result = self.cursor.execute(sql).fetchone()
        return result and result.__len__() > 0

    @abstractmethod
    def install(self):
        """
        This method installs collector
        """
        pass

    @abstractmethod
    def collect(self):
        """
        Method called in big while(True) loop, to gather and save data to db
        """
        pass

    @abstractmethod
    def get_data(self, limit=30, interval=10):
        """
        Method used to retrieve data
        """
        pass

    def get_data_columns_description(self):
        columns_description = ('datetime', 'Timestamp'),

        for column_name, column_type, column_label in self.column_description:
            columns_description += ((column_type, column_label),)

        return columns_description

    def get_chart_js(self, limit=30, interval=10):
        column_definition = ''
        for column_type, column_name in self.get_data_columns_description():
            column_definition += "data.addColumn('%s', '%s');\n" % (
                column_type,
                column_name,
            )

        return CHART_JS % {
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

    def current_status(self):
        """
        Returns current status of data

        :return: List with status
        :rtype: list
        """

    def check_for_alerts(self):
        for alert in self.alerts:
            if alert.check(self):
                alert.alert()
