## Scheduler

Install the persistent job-store dependency with
`pip install "pygarden[scheduler]"`.

pyGARDEN includes a lightweight wrapper around APScheduler in
`pygarden.scheduler.Scheduler`. It provides:

- A **singleton background scheduler**.
- Simple context-manager semantics.
- A SQLAlchemy-backed job store for persistence.

This makes it easy to schedule recurring tasks in your services without
having to wire up APScheduler yourself.

---

## Overview

The `Scheduler` class:

- Ensures only one shared APScheduler instance is created.
- Uses a SQLAlchemy job store configured from an environment variable.
- Provides convenience methods for:
  - Starting jobs.
  - Stopping jobs.
  - Reporting scheduler status.
  - Shutting down the scheduler.

Environment variables:

- `SCHEDULER_DB_URL`:
  - SQLAlchemy URL for the APScheduler job store
    (default: `sqlite:////tmp/jobs.sqlite`).
- `SCHEDULER_INTERVAL`:
  - Default job interval configuration, as a dict or JSON string.

---

## Basic usage

```python
from pygarden.scheduler import Scheduler


def my_task(name: str) -> None:
    print(f"hello {name}")


with Scheduler() as sch:
    sch.start_job(
        task=my_task,
        args=("garden",),
        job_id="garden_task",
        interval_value={"seconds": 10},
    )
    print(sch.report_status())
```

On exit from the `with` block, the scheduler is shut down (or kept
alive, depending on options).

---

## Job scheduling

Key method:

- `start_job(...)`:
  - Wraps `apscheduler.schedulers.background.BackgroundScheduler.add_job`.
  - Accepts:
    - `task`: callable to run.
    - `trigger`: trigger type (default: `"interval"`).
    - `interval_value`: dict or JSON string (e.g. `{"seconds": 10}`).
    - `args` / `kwargs`: passed to the task.
    - `job_id`: optional; defaults to the function name if omitted.
    - `end_date`: optional end time for the job.

Additional helpers:

- `stop_job(job_id)`:
  - Remove a job.
- `report_status()`:
  - Return a list of `{"id", "next_run_time"}` for all jobs.
- `shutdown(...)`:
  - Shut down the shared APScheduler instance and optionally clear the
    singleton.

---

## SQLAlchemy job store

Internally, the scheduler:

- Creates an Engine via `sqlalchemy.create_engine(SCHEDULER_DB_URL)`.
- Configures:
  - `apscheduler.jobstores.sqlalchemy.SQLAlchemyJobStore(engine=engine)`
- Starts a `BackgroundScheduler` with this jobstore.

This means:

- Jobs are persisted in the configured database.
- Multiple processes can share the same job store if needed.

You can point `SCHEDULER_DB_URL` at:

- SQLite (default).
- PostgreSQL or other SQLAlchemy-supported databases.
