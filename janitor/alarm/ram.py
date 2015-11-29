# -*- coding:utf-8 -*-
from janitor.alarm.base import BaseAlert


class RamAlert(BaseAlert):
    @property
    def message(self):
        return 'Ram usage exceed %d%%' % self.percentage_limit

    def __init__(self, notifers, percentage_limit=90):
        self.percentage_limit = percentage_limit
        super(RamAlert, self).__init__(notifers)

    def _check(self, collector):

        used_ram = collector.last_reading[2] - (
            collector.last_reading[3] +  # free mem
            collector.last_reading[4] +  # buffers
            collector.last_reading[5]  # cache
        )
        if used_ram >= (self.percentage_limit/100) * collector.last_reading[2]:
            return True

        return False
