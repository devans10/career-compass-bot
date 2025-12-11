from datetime import time
from typing import Callable, Optional

from apscheduler.schedulers.background import BackgroundScheduler


class ReminderScheduler:
    """Schedule weekly reminders for the bot."""

    def __init__(self, send_reminder: Callable[[], None], tz: Optional[str] = None) -> None:
        self.send_reminder = send_reminder
        self.scheduler = BackgroundScheduler(timezone=tz)

    def start_weekly(self, day_of_week: str = "fri", run_time: time = time(hour=15)) -> None:
        """Start a weekly job that triggers the provided callback."""

        self.scheduler.add_job(
            self.send_reminder,
            "cron",
            day_of_week=day_of_week,
            hour=run_time.hour,
            minute=run_time.minute,
        )
        self.scheduler.start()

    def shutdown(self) -> None:
        """Shut down the scheduler if running."""

        if self.scheduler.running:
            self.scheduler.shutdown()
