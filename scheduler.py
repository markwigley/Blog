"""
Scheduler module.

Handles scheduling the weekly digest to run every Friday at 5pm.
"""

import logging
import signal
import sys
import time
from datetime import datetime
from typing import Callable, Optional

import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

import config

logger = logging.getLogger(__name__)


class DigestScheduler:
    """Schedules the weekly digest job."""

    def __init__(
        self,
        job_func: Callable,
        timezone: Optional[str] = None,
        day: Optional[str] = None,
        hour: Optional[int] = None,
        minute: Optional[int] = None,
    ):
        """
        Initialize the scheduler.

        Args:
            job_func: The function to run on schedule.
            timezone: Timezone for scheduling (default: config.TIMEZONE).
            day: Day of week to run (default: config.SCHEDULE_DAY).
            hour: Hour to run (default: from config.SCHEDULE_TIME).
            minute: Minute to run (default: from config.SCHEDULE_TIME).
        """
        self.job_func = job_func
        self.timezone = pytz.timezone(timezone or config.TIMEZONE)

        # Parse schedule time from config
        schedule_parts = config.SCHEDULE_TIME.split(":")
        default_hour = int(schedule_parts[0])
        default_minute = int(schedule_parts[1]) if len(schedule_parts) > 1 else 0

        self.day = day or config.SCHEDULE_DAY
        self.hour = hour if hour is not None else default_hour
        self.minute = minute if minute is not None else default_minute

        self.scheduler = BackgroundScheduler(timezone=self.timezone)
        self._setup_signal_handlers()

    def _setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            logger.info("Received shutdown signal, stopping scheduler...")
            self.stop()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    def start(self):
        """Start the scheduler."""
        # Create cron trigger for the specified day and time
        trigger = CronTrigger(
            day_of_week=self.day.lower()[:3],  # 'fri' for friday
            hour=self.hour,
            minute=self.minute,
            timezone=self.timezone,
        )

        self.scheduler.add_job(
            self.job_func,
            trigger=trigger,
            id="weekly_digest",
            name="Fourth Circuit Weekly Digest",
            replace_existing=True,
        )

        self.scheduler.start()

        logger.info(
            f"Scheduler started. Digest will run every {self.day.capitalize()} "
            f"at {self.hour:02d}:{self.minute:02d} {self.timezone}"
        )

        # Log next run time
        job = self.scheduler.get_job("weekly_digest")
        if job and job.next_run_time:
            logger.info(f"Next scheduled run: {job.next_run_time}")

    def stop(self):
        """Stop the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("Scheduler stopped")

    def run_now(self):
        """Run the job immediately (useful for testing)."""
        logger.info("Running digest job immediately...")
        self.job_func()

    def get_next_run_time(self) -> Optional[datetime]:
        """Get the next scheduled run time."""
        job = self.scheduler.get_job("weekly_digest")
        if job:
            return job.next_run_time
        return None

    def run_forever(self):
        """Keep the scheduler running indefinitely."""
        logger.info("Scheduler running. Press Ctrl+C to stop.")
        try:
            while True:
                time.sleep(60)  # Check every minute
        except (KeyboardInterrupt, SystemExit):
            self.stop()


def create_simple_scheduler(job_func: Callable) -> DigestScheduler:
    """
    Create a scheduler with default settings.

    Args:
        job_func: The function to run on schedule.

    Returns:
        Configured DigestScheduler instance.
    """
    return DigestScheduler(job_func)
