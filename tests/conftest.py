import os
import shutil
import socket
import contextlib

import pytest


def docker_available() -> bool:
    return shutil.which("docker") is not None


@pytest.fixture(scope="session")
def has_docker():
    return docker_available()


@contextlib.contextmanager
def env_vars(env: dict):
    original = {k: os.environ.get(k) for k in env}
    os.environ.update({k: str(v) for k, v in env.items()})
    try:
        yield
    finally:
        for k, v in original.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


@pytest.fixture
def set_env():
    def _set(env: dict):
        return env_vars(env)

    return _set
