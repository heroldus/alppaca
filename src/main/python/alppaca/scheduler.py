from __future__ import print_function, absolute_import, unicode_literals, division

import datetime
import isodate
import json
import logging
import six
from random import uniform

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
import pytz

from alppaca.delaytrigger import DelayTrigger


class Scheduler(object):
    """ Scheduler for refreshing credentials.

        By default it will fetch the credentials and then schedule itself to
        update them based on the expiration date. Some randomness is involved
        to avoid collisions. In case of failure to fetch credentials a back-off
        and safety behaviour is initiated.

        It is based on the apscheduler package.

    """

    def __init__(self, credentials, credentials_provider):
        self.logger = logging.getLogger(__name__)
        self.credentials = credentials

        self.credentials_provider = credentials_provider
        self.backoff = None
        self.scheduler = BackgroundScheduler()
        self.scheduler.add_listener(self.job_executed_event_listener, EVENT_JOB_EXECUTED)
        self.scheduler.add_listener(self.job_failed_event_listener, EVENT_JOB_ERROR)
        self.scheduler.start()

    def job_executed_event_listener(self, event):
        self.logger.info("Successfully completed credentials refresh")

    def job_failed_event_listener(self, event):
        self.logger.error("Failed to refresh credentials: %s", event.exception)

    def do_backoff(self):
        """ Perform back-off and safety. """
        if self.backoff is None:
            self.logger.info("Initialize back-off and safety behaviour")
            self.backoff = backoff_refresh_generator()
        refresh_delta = six.next(self.backoff)
        self.build_trigger(refresh_delta)

    def refresh_credentials(self):
        """ Refresh credentials and schedule next refresh."""
        self.logger.info("about to fetch credentials")

        try:
            cached_credentials = self.credentials_provider.get_credentials_for_all_roles()
        except Exception:
            self.logger.exception("Error in credential provider:")
            cached_credentials = None

        if cached_credentials:
            self.update_credentials(cached_credentials)
        else:
            self.logger.info("No credentials found!")
            self.do_backoff()

    def update_credentials(self, cached_credentials):
        """ Update credentials and retrigger refresh """
        self.credentials.update(cached_credentials)
        self.logger.info("Got credentials: %s", self.credentials)
        refresh_delta = self.extract_refresh_delta()
        if refresh_delta < 0:
            self.logger.warn("Expiration date is in the past, enter backoff.")
            self.do_backoff()
        else:
            if self.backoff is not None:
                self.backoff = None
                self.logger.info("Exit backoff state.")
            refresh_delta = self.sample_new_refresh_delta(refresh_delta)
            self.build_trigger(refresh_delta)

    def extract_refresh_delta(self):
        """ Return shortest expiration time in seconds. """
        expiration = isodate.parse_datetime(extract_min_expiration(self.credentials))
        self.logger.info("Extracted expiration: %s", expiration)
        refresh_delta = total_seconds(expiration - datetime.datetime.now(tz=pytz.utc))
        return refresh_delta

    def sample_new_refresh_delta(self, refresh_delta):
        """ Sample a new refresh delta. """
        refresh_delta = int(uniform(refresh_delta * .5, refresh_delta * .9))
        return refresh_delta

    def build_trigger(self, refresh_delta):
        """ Actually add the trigger to the apscheduler. """
        self.logger.info("Setting up trigger to fire in %s seconds", refresh_delta)
        self.scheduler.add_job(func=self.refresh_credentials, trigger=DelayTrigger(refresh_delta))


def backoff_refresh_generator():
    """ Generate refresh deltas when in back-off and safety mode. """
    count = 0
    while True:
        yield count if count < 10 else 10
        count += 1


def extract_min_expiration(credentials):
    """ The smallest expiration date of all the available credentials. """
    return min([json.loads(value)['Expiration']
                for value in credentials.values()])


def total_seconds(timedelta):
    """ Convert timedelta to seconds as an integer. """
    return (timedelta.microseconds + (timedelta.seconds + timedelta.days * 24 * 3600) * 10**6) // 10**6
