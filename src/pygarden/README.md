# PyGarden Scheduler

A tiny wrapper around [APScheduler](https://apscheduler.readthedocs.io/) that gives you a **singleton background scheduler** with **persistent jobs** via SQLAlchemy. It’s designed for “set it and forget it” recurring tasks inside PyGarden services.

---

## Scheduler Features

-  Singleton `BackgroundScheduler` (no duplicate schedulers)
-  Persistent jobs with `SQLAlchemyJobStore`
-  One-liner `auto_start_job()` to (re)create recurring jobs
-  `auto_stop_job()` and `shutdown_scheduler()` helpers
-  `auto_report_status()` to list jobs & next run times
- ️ Config via environment variables

---

## Scheduler Quickstart

```python
from pygarden.scheduler import Scheduler
from pygarden.logz import create_logger

logger = create_logger()

def my_task(name):
    print(f"hello {name}")

with Scheduler() as sch:
    sch.start_job(
        task=my_task,
        args=("garden",),
        job_id="garden_task",
        interval_value={"seconds": 10},
    )
        
print(sch.report_status())

# 2) See what’s scheduled
print(sch.auto_report_status())
# -> [{'id': 'hello_garden', 'next_run_time': '2025-08-15 14:30:00+00:00'}, ...]

# 3) Stop a job later
sch.auto_stop_job("garden_task")

# 4) Shut down the scheduler (e.g., on service shutdown)
sch.shutdown_scheduler(wait=False, clear=True)
```

#### get_scheduler() -> BackgroundScheduler

- Returns the shared singleton scheduler. Creates and starts it on first call (using SCHEDULER_DB_URL).

```python
from pygarden.scheduler import get_scheduler

scheduler = get_scheduler()
```

#### auto_start_job(...) -> Job

- Create or replace a scheduled job. If job_id is omitted/empty, the task’s function name is used.

```python
auto_start_job(
    task,
    trigger='interval',
    interval_value=None,
    args=None,
    kwargs=None,
    job_id=None,
    end_date=None
) -> Job

# Use default SCHEDULER_INTERVAL (e.g., {"hours": 2})
auto_start_job(my_task, args=("garden",), job_id="every_2_hours")

# Override interval per job with a dict
auto_start_job(my_task, args=("alpha",), job_id="every_10s", interval_value={"seconds": 10})

# Or with a JSON string
auto_start_job(my_task, args=("beta",), job_id="every_minute", interval_value='{"minutes": 1}')
```

#### auto_stop_job(job_id) -> None

- Remove a scheduled job if it exists.

```python
auto_stop_job("every_minute")
```

#### auto_report_status() -> list[dict]

- Returns a lightweight list of {"id": ..., "next_run_time": ...} for all jobs and logs it.

```python
statuses = auto_report_status()
for s in statuses:
    print(s["id"], s["next_run_time"])
```

#### shutdown_scheduler(wait: bool = False, clear: bool = True) -> bool

- Shuts down the shared scheduler (if any). If clear=True, the singleton is reset so the next get_scheduler() call creates a fresh one.

```python
# Stop immediately; allow a brand new scheduler later
shutdown_scheduler(wait=False, clear=True)
```