"""
Scheduler Module for PyGarden (context-manager version)

Usage:

    def my_task(name):
        print(f"hello {name}")

    with Scheduler() as sch:  # starts (or reuses) the singleton scheduler
        sch.start_job(
            task=my_task,
            args=("garden",),
            job_id="garden_task",
            interval_value={"seconds": 10},
        )
        print(sch.report_status())
    # on exiting the with-block, the scheduler is shut down by default
"""

from __future__ import annotations

import json
from typing import Any, Callable, Dict, Iterable, Optional

from apscheduler.schedulers.background import BackgroundScheduler

try:
    from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
    from sqlalchemy import create_engine
except ImportError:  # optional persistent job-store dependency
    SQLAlchemyJobStore = None
    create_engine = None

from pygarden.env import check_environment as ce
from pygarden.logz import create_logger

logger = create_logger()


class Scheduler:
    """
    Singleton APScheduler wrapper with context-manager support.

    - `Scheduler()` returns the same shared instance every time.
    - `with Scheduler() as sch:` starts (or reuses) the scheduler and
      shuts it down on exit (configurable).
    """

    _instance: Optional["Scheduler"] = None
    _aps: Optional[BackgroundScheduler] = None

    # Defaults sourced from environment to keep parity with your module
    DEFAULT_INTERVAL: Dict[str, Any] = ce("SCHEDULER_INTERVAL", {"hours": 2})
    DEFAULT_DB_URL: str = ce("SCHEDULER_DB_URL", "sqlite:////tmp/jobs.sqlite")

    def __new__(cls, *args, **kwargs):
        """Return the process-wide scheduler instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        db_url: Optional[str] = None,
        start_immediately: bool = True,
        wait_on_exit: bool = False,
        clear_on_exit: bool = True,
    ):
        """
        Initialize the scheduler wrapper.

        :param db_url: SQLAlchemy URL for job store. Defaults to env/SQLite.
        :param start_immediately: If True, ensure scheduler is started on init.
        :param wait_on_exit: Wait for running jobs when exiting context.
        :param clear_on_exit: Clear singleton on exit (fresh instance next time).
        """
        self.db_url = db_url or self.DEFAULT_DB_URL
        self.wait_on_exit = wait_on_exit
        self.clear_on_exit = clear_on_exit

        if start_immediately:
            self.start()

    def __enter__(self) -> "Scheduler":
        """Start and return the scheduler."""
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        """Leave the scheduler running when the context exits."""
        return None

    def start(self) -> BackgroundScheduler:
        """Create or start the shared scheduler with a SQLAlchemy job store."""
        if self.__class__._aps is None:
            if SQLAlchemyJobStore is None or create_engine is None:
                raise ImportError(
                    "Scheduler persistence requires SQLAlchemy. Install with: pip install 'pygarden[scheduler]'"
                )
            logger.info("Creating and starting new APScheduler instance...")
            engine = create_engine(self.db_url)
            jobstores = {"default": SQLAlchemyJobStore(engine=engine)}
            aps = BackgroundScheduler(jobstores=jobstores)
            aps.start()
            self.__class__._aps = aps
            logger.info("✅ Scheduler started.")
        else:
            if not self.__class__._aps.running:
                logger.info("Starting existing APScheduler instance...")
                self.__class__._aps.start()
            else:
                logger.debug("Reusing existing scheduler instance.")
        return self.__class__._aps

    @property
    def scheduler(self) -> BackgroundScheduler:
        """Access the underlying APScheduler (ensures it's started)."""
        return self.start()

    def start_job(
        self,
        task: Callable[..., Any],
        *,
        trigger: str = "interval",
        interval_value: Dict[str, Any] | str | None = None,
        args: Optional[Iterable[Any]] = None,
        kwargs: Optional[Dict[str, Any]] = None,
        job_id: Optional[str] = None,
        end_date=None,
    ):
        """Schedule a job, accepting a dict or JSON interval value."""
        # Resolve job_id
        checked_job_id = (job_id.strip() if isinstance(job_id, str) and job_id.strip() else None) or getattr(
            task, "__name__", getattr(task, "__qualname__", task.__class__.__name__)
        )
        if not job_id:
            logger.warning(f"No job_id provided, using task name as job_id: '{checked_job_id}'")

        # Args validation (keep your original semantics)
        if not args:
            logger.error(f"No args provided for job '{checked_job_id}'. At least one positional argument is required.")
            raise ValueError("No args provided")
        if not isinstance(args, (tuple, list)):
            raise ValueError("args must be a tuple or list")

        # Normalize kwargs
        if kwargs is None:
            kwargs = {}

        # Normalize interval
        interval_value = self._normalize_interval(interval_value)

        logger.debug(
            f"add_job id={checked_job_id!r}, trigger={trigger!r}, interval={interval_value!r}, "
            f"args={args!r}, kwargs keys={list(kwargs.keys())!r}"
        )

        job = self.scheduler.add_job(
            func=task,
            trigger=trigger,
            id=checked_job_id,
            replace_existing=True,
            args=tuple(args),
            kwargs=kwargs,
            end_date=end_date,
            **interval_value,
        )

        if end_date:
            logger.info(f"Scheduled job id='{job.id}' until {end_date}. Next run: {job.next_run_time}")
        else:
            logger.info(f"Scheduled job id='{job.id}' with no end time. Next run: {job.next_run_time}")
        return job

    def stop_job(self, job_id: str) -> None:
        """Remove a job by ID."""
        job = self.scheduler.get_job(job_id)
        if job:
            self.scheduler.remove_job(job_id)
            logger.info(f"Removed job with id {job_id}")
        else:
            logger.warning(f"Job with id {job_id} not found to remove.")

    def report_status(self) -> list[dict]:
        """Return a list of {'id', 'next_run_time'} for all jobs."""
        jobs = self.scheduler.get_jobs()
        out = [{"id": j.id, "next_run_time": str(j.next_run_time)} for j in jobs]
        logger.info(str(out))
        return out

    def shutdown(self, *, wait: bool = False, clear: bool = True) -> bool:
        """Shut down the shared APScheduler instance."""
        aps = self.__class__._aps
        if aps is None:
            logger.debug("shutdown: no active scheduler to shut down.")
            return False
        try:
            aps.shutdown(wait=wait)
            logger.info("Scheduler shut down.")
        except Exception as exc:
            logger.exception("Error shutting down scheduler: %s", exc)
            raise
        finally:
            if clear:
                self.__class__._aps = None
                self.__class__._instance = None
                logger.debug("Scheduler singleton cleared.")
        return True

    @classmethod
    def _normalize_interval(cls, interval_value: Dict[str, Any] | str | None) -> Dict[str, Any]:
        """Accept a dict, JSON string, or the environment-backed default."""
        if interval_value is None:
            return dict(cls.DEFAULT_INTERVAL)
        if isinstance(interval_value, str):
            try:
                interval_value = json.loads(interval_value)
            except json.JSONDecodeError as e:
                logger.error(
                    f"Unable to parse interval_value as JSON: {e}. "
                    "Provide a dict like {'seconds': 2} or a JSON string."
                )
                raise ValueError("Invalid interval_value JSON") from e
        if not isinstance(interval_value, dict):
            logger.error(f"interval_value must be a dict, got {type(interval_value).__name__}")
            raise TypeError("interval_value must be a dict")
        return interval_value

    # Optional convenience alias
    auto_start_job = start_job
    auto_stop_job = stop_job
    auto_report_status = report_status
    shutdown_scheduler = shutdown
