from __future__ import print_function, absolute_import, unicode_literals, division

import datetime

from mock import patch

from alppaca.delaytrigger import DelayTrigger
from alppaca.compat import unittest
from test_utils import FixedDateTime


class DelayTriggerTest(unittest.TestCase):

    @patch('datetime.datetime', FixedDateTime)
    @patch('alppaca.delaytrigger.DateTrigger.__init__')
    def test_should_compute_time_delta_for_datetrigger_for_a_given_date(self, datetrigger_mock):

        DelayTrigger(10)

        datetrigger_mock.assert_called_with(run_date=datetime.datetime(1970, 1, 1, 0, 0, 10))

    @patch('alppaca.delaytrigger.DateTrigger.__init__')
    def test_should_call_datetrigger_with_none_if_called_with_negative_delta(self, datetrigger_mock):

        DelayTrigger(-10)

        datetrigger_mock.assert_called_with(run_date=None)
