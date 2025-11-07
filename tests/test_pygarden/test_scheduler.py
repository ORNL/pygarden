# tests/test_scheduler.py
import types
import json
import pytest

from pygarden.scheduler import Scheduler

class FakeJob:
    def __init__(self, id, next_run_time="2030-01-01 00:00:00"):
        self.id = id
        self.next_run_time = next_run_time

class FakeAPS:
    def __init__(self, jobstores=None):
        self.jobstores = jobstores or {}
        self.started = False
        self.running = False
        self.jobs = {}
        self.add_job_calls = []
        self.shutdown_calls = []

    def start(self):
        self.started = True
        self.running = True

    def shutdown(self, wait=False):
        self.running = False
        self.shutdown_calls.append(wait)

    def add_job(self, *, func, trigger, id, replace_existing, args, kwargs, end_date=None, **interval):
        # replace_existing behavior
        if not replace_existing and id in self.jobs:
            raise RuntimeError("Job exists")
        job = FakeJob(id)
        self.jobs[id] = job
        self.add_job_calls.append(
            dict(func=func, trigger=trigger, id=id, args=args, kwargs=kwargs,
                 end_date=end_date, interval=interval, replace_existing=replace_existing)
        )
        return job

    def get_job(self, job_id):
        return self.jobs.get(job_id)

    def remove_job(self, job_id):
        self.jobs.pop(job_id, None)

    def get_jobs(self):
        return list(self.jobs.values())


class FakeJobStore:
    def __init__(self, engine=None):
        self.engine = engine


@pytest.fixture(autouse=True)
def isolate_singleton():
    # ensure a fresh singleton for each test
    Scheduler._instance = None
    Scheduler._aps = None
    yield
    # cleanup in case a test forgets to shutdown
    Scheduler._aps = None
    Scheduler._instance = None


@pytest.fixture
def patched_internals(monkeypatch):
    # Patch BackgroundScheduler, SQLAlchemyJobStore, and create_engine
    fake_aps_instances = []

    def fake_background_scheduler(*, jobstores):
        aps = FakeAPS(jobstores=jobstores)
        fake_aps_instances.append(aps)
        return aps

    # Patch into the module under test
    import pygarden.scheduler as mod

    monkeypatch.setattr(mod, "BackgroundScheduler", lambda **kw: fake_background_scheduler(**kw))
    monkeypatch.setattr(mod, "SQLAlchemyJobStore", lambda **kw: FakeJobStore(**kw))
    monkeypatch.setattr(mod, "create_engine", lambda url: f"engine://{url}")

    # Ensure defaults from env are stable
    monkeypatch.setattr(Scheduler, "DEFAULT_DB_URL", "sqlite:////tmp/test_jobs.sqlite", raising=True)
    monkeypatch.setattr(Scheduler, "DEFAULT_INTERVAL", {"seconds": 7}, raising=True)

    return types.SimpleNamespace(
        fake_aps_instances=fake_aps_instances,
        module=mod,
    )


def test_singleton_identity(patched_internals):
    a = Scheduler(start_immediately=False)
    b = Scheduler(start_immediately=False)
    assert a is b

def test_start_creates_and_starts_aps(patched_internals):
    sch = Scheduler(start_immediately=False)
    assert Scheduler._aps is None

    aps = sch.start()
    assert aps.started and aps.running
    assert Scheduler._aps is aps

def test_context_manager_starts_only(patched_internals):
    with Scheduler() as sch:
        assert sch.scheduler.running

    # after exit, it should still be running
    assert Scheduler._aps is not None
    assert Scheduler._aps.running is True

    # clean up explicitly for test isolation
    sch.shutdown(wait=False, clear=True)
    assert Scheduler._aps is None
    assert Scheduler._instance is None

def test_start_job_happy_path_uses_defaults_and_replaces(patched_internals):
    with Scheduler(clear_on_exit=True) as sch:
        def task(name):  # simple callable
            return f"hi {name}"

        job = sch.start_job(task=task, args=["garden"], job_id="jid")
        assert job.id == "jid"

        # interval defaults came from DEFAULT_INTERVAL fixture
        call = sch.scheduler.add_job_calls[-1]
        assert call["interval"] == {"seconds": 7}
        assert call["replace_existing"] is True

def test_start_job_accepts_json_interval(patched_internals):
    with Scheduler(clear_on_exit=True) as sch:
        def task(name): pass
        job = sch.start_job(task=task, args=("x",), job_id="json_job",
                            interval_value=json.dumps({"minutes": 5}))
        call = sch.scheduler.add_job_calls[-1]
        assert call["interval"] == {"minutes": 5}

def test_start_job_rejects_bad_interval_json(patched_internals):
    with Scheduler(clear_on_exit=True) as sch:
        def task(name): pass
        with pytest.raises(ValueError):
            sch.start_job(task=task, args=("x",), job_id="bad_json",
                          interval_value="{oops}")

def test_start_job_requires_args(patched_internals):
    with Scheduler(clear_on_exit=True) as sch:
        def task(): pass
        with pytest.raises(ValueError):
            sch.start_job(task=task, args=[], job_id="noargs")

def test_start_job_args_must_be_list_or_tuple(patched_internals):
    with Scheduler(clear_on_exit=True) as sch:
        def task(x): pass
        with pytest.raises(ValueError):
            sch.start_job(task=task, args="not-iterable-correctly", job_id="badargs")

def test_stop_job_existing_and_missing(patched_internals):
    with Scheduler(clear_on_exit=True) as sch:
        def task(x): pass
        sch.start_job(task=task, args=(1,), job_id="to_kill")
        assert sch.scheduler.get_job("to_kill") is not None

        sch.stop_job("to_kill")
        assert sch.scheduler.get_job("to_kill") is None

        # no exception on missing
        sch.stop_job("missing")

def test_report_status(patched_internals):
    with Scheduler(clear_on_exit=True) as sch:
        def task(x): pass
        sch.start_job(task=task, args=(1,), job_id="a")
        sch.start_job(task=task, args=(2,), job_id="b")
        status = sch.report_status()
        assert {s["id"] for s in status} == {"a", "b"}
        assert all("next_run_time" in s for s in status)

def test_shutdown_wait_and_clear_flags(patched_internals):
    sch = Scheduler(wait_on_exit=False, clear_on_exit=False)
    aps = sch.scheduler
    assert aps.running

    sch.shutdown(wait=True, clear=True)
    assert not aps.running
    assert aps.shutdown_calls[-1] is True
    assert Scheduler._aps is None
    assert Scheduler._instance is None

def test_aliases_preserved(patched_internals):
    with Scheduler(clear_on_exit=True) as sch:
        def task(x): pass

        # these should exist and delegate to primary methods
        assert Scheduler.auto_start_job is Scheduler.start_job
        assert Scheduler.auto_stop_job is Scheduler.stop_job
        assert Scheduler.auto_report_status is Scheduler.report_status
        assert Scheduler.shutdown_scheduler is Scheduler.shutdown

        sch.auto_start_job(task=task, args=(1,), job_id="alias")
        assert sch.scheduler.get_job("alias") is not None

def test_db_url_override_used_in_engine(patched_internals, monkeypatch):
    # capture what engine URL was passed into the jobstore
    seen = {}

    def capture_jobstore(engine=None):
        seen["engine"] = engine
        return FakeJobStore(engine=engine)

    monkeypatch.setattr(patched_internals.module, "SQLAlchemyJobStore", lambda **kw: capture_jobstore(**kw))

    sch = Scheduler(db_url="sqlite:////tmp/override.sqlite", start_immediately=False)
    sch.start()

    assert seen["engine"] == "engine://sqlite:////tmp/override.sqlite"
