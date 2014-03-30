#!/usr/bin/env python
#-*- coding:utf-8 -*-

import sqlite3
import SocketServer

from data import config

__author__ = 'Daniel Alkemic Czuba <dc@danielczuba.pl>'


page_contents = """HTTP/1.1 200 OK
Content-Type:text/html


<html>
  <head>
    <script type="text/javascript" src="https://www.google.com/jsapi"></script>
    <script type="text/javascript">
      google.load("visualization", "1", {packages:["corechart"]});
      google.setOnLoadCallback(drawChart);
      function drawChart() {
        %s
      }
    </script>
    <style>
    div.chart{max-width: 1200px; height: 500px; margin: 9 auto;}
    </style>
  </head>
  <body>
    %s
  </body>
</html>
"""


class ChartHandler(SocketServer.BaseRequestHandler):
    connection = None
    collectors = []

    def handle(self):
        self.data = self.request.recv(1024).strip()
        print 'connection from: ', self.client_address[0]
        print self.data
        chart_divs = chart_jses = ''

        for collector in self.collectors:
            chart_jses += collector.get_chart_js(interval=10)
            chart_divs += collector.get_chart_div()

        self.request.sendall(page_contents % (chart_jses, chart_divs))


if __name__ == '__main__':
    SocketServer.TCPServer.allow_reuse_address = True

    ChartHandler.connection = sqlite3.connect(config.SQLITE_PATH)

    for collector, collector_kwargs in config.COLLECTORS:
        ChartHandler.collectors.append(collector(ChartHandler.connection, **collector_kwargs))

    server = SocketServer.TCPServer(config.JANITOR_DATA_BIND_TO, ChartHandler)

    server.serve_forever()
