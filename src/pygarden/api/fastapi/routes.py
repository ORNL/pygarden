"""FastAPI routes for service health checks."""

import os

import psycopg
import pymssql
import redis
import requests
from celery import Celery
from fastapi import APIRouter
from fastapi.responses import JSONResponse, PlainTextResponse

router = APIRouter(tags=["health"])


def _get_env(*names):
    for name in names:
        value = os.getenv(name)
        if value is not None:
            return value
    return None


@router.get("/healthcheck")
def health_check():
    return {"status": "OK"}


@router.get("/postgres_healthcheck", response_class=PlainTextResponse)
def postgres_healthcheck():
    dbname = _get_env("DATABASE_DB_PG", "DATABASE_DB", "PG_DATABASE")
    user = _get_env("DATABASE_USER", "DATABASE_USER_PG", "PG_USER")
    password = _get_env("DATABASE_PW", "DATABASE_PW_PG", "PG_PASSWORD")
    host = _get_env("DATABASE_HOST", "DATABASE_HOST_PG", "PG_HOST")
    port = _get_env("DATABASE_PORT", "DATABASE_PORT_PG", "PG_PORT")

    if dbname is None:
        return PlainTextResponse(
            "Need to set either DATABASE_DB_PG or DATABASE_DB ENV variables",
            status_code=503,
        )
    if user is None:
        return PlainTextResponse(
            "Need to set either DATABASE_USER_PG or DATABASE_USER ENV variables",
            status_code=503,
        )
    if password is None:
        return PlainTextResponse(
            "Need to set either DATABASE_PW_PG or DATABASE_PW ENV variables",
            status_code=503,
        )
    if host is None:
        return PlainTextResponse(
            "Need to set either DATABASE_HOST_PG or DATABASE_HOST ENV variables",
            status_code=503,
        )
    if port is None:
        return PlainTextResponse(
            "Need to set either DATABASE_PORT_PG or DATABASE_PORT ENV variables",
            status_code=503,
        )

    try:
        conn = psycopg.connect(
            dbname=dbname,
            user=user,
            password=password,
            host=host,
            port=port,
        )
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        db_version = cursor.fetchone()
        cursor.close()
        conn.close()
    except psycopg.Error as exc:
        return PlainTextResponse(
            f"Error connecting to PostgreSQL:{exc}",
            status_code=503,
        )

    if db_version:
        return PlainTextResponse("Database is running", status_code=200)
    return PlainTextResponse("Database does not seem to be running", status_code=503)


@router.get("/mssql_healthcheck", response_class=PlainTextResponse)
def mssql_healthcheck():
    dbname = _get_env("DATABASE_DB_MS", "DATABASE_DB")
    user = _get_env("DATABASE_USER_MS", "DATABASE_USER")
    password = _get_env("DATABASE_PW_MS", "DATABASE_PW")
    host = _get_env("DATABASE_HOST_MS", "DATABASE_HOST")
    port = _get_env("DATABASE_PORT_MS", "DATABASE_PORT")

    if dbname is None:
        return PlainTextResponse(
            "Need to set either DATABASE_DB_MS or DATABASE_DB ENV variables",
            status_code=503,
        )
    if user is None:
        return PlainTextResponse(
            "Need to set either DATABASE_USER_MS or DATABASE_USER ENV variables",
            status_code=503,
        )
    if password is None:
        return PlainTextResponse(
            "Need to set either DATABASE_PW_MS or DATABASE_PW ENV variables",
            status_code=503,
        )
    if host is None:
        return PlainTextResponse(
            "Need to set either DATABASE_HOST_MS or DATABASE_HOST ENV variables",
            status_code=503,
        )
    if port is None:
        return PlainTextResponse(
            "Need to set either DATABASE_PORT_MS or DATABASE_PORT ENV variables",
            status_code=503,
        )

    try:
        conn = pymssql.connect(
            server=host,
            user=user,
            password=password,
            database=dbname,
            port=port,
        )
        cursor = conn.cursor()
        cursor.execute("SELECT @@VERSION;")
        db_version = cursor.fetchone()
        cursor.close()
        conn.close()
    except pymssql.Error as exc:
        return PlainTextResponse(
            f"Error connecting to MSSQL:{exc}",
            status_code=503,
        )

    if db_version:
        return PlainTextResponse("Database is running", status_code=200)
    return PlainTextResponse("Database does not seem to be running", status_code=503)


@router.get("/rabbitmq_healthcheck", response_class=PlainTextResponse)
def rabbitmq_healthcheck():
    host = os.getenv("RABBIT_MQ_HOST")
    port = os.getenv("RABBIT_MQ_PORT")

    if host is None:
        return PlainTextResponse(
            "Need to set RABBIT_MQ_HOST variable",
            status_code=503,
        )
    if port is None:
        return PlainTextResponse(
            "Need to set RABBIT_MQ_PORT ENV variable",
            status_code=503,
        )

    response = requests.get(host)
    if response.status_code == 200:
        return PlainTextResponse("Healthcheck good", status_code=200)
    return PlainTextResponse("Healthcheck failed", status_code=response.status_code)


@router.get("/redis_healthcheck", response_class=PlainTextResponse)
def redis_healthcheck():
    host = os.getenv("REDIS_HOST")
    port = os.getenv("REDIS_PORT")

    if host is None:
        return PlainTextResponse(
            "Need to set REDIS_HOST ENV variable",
            status_code=503,
        )
    if port is None:
        return PlainTextResponse(
            "Need to set REDIS_PORT ENV variable",
            status_code=503,
        )

    try:
        client = redis.Redis(host=host, port=port, decode_responses=True)
        client.hset("test", mapping={"get": "healthcheck"})
        result = client.hgetall("test")
    except Exception:
        return PlainTextResponse(
            "There was an error, check your redis cluster",
            status_code=500,
        )

    if result == {}:
        return PlainTextResponse("Queried Redis, but data was empty", status_code=200)
    if result.get("get") == "healthcheck":
        return PlainTextResponse("Healthcheck good", status_code=200)
    return PlainTextResponse(
        "Redis may be running, but there was an unknown issue",
        status_code=200,
    )


def make_celery():
    return Celery(broker=os.getenv("REDIS_BROKER"))


@router.get("/celery_healthcheck")
def celery_healthcheck():
    try:
        celery = make_celery()
        inspector = celery.control.inspect()
        active_workers = inspector.ping()
    except Exception as exc:
        return JSONResponse(
            {"status": "failure", "message": str(exc)},
            status_code=500,
        )

    if not active_workers:
        return JSONResponse(
            {"status": "failure", "message": "No active workers found"},
            status_code=503,
        )

    return JSONResponse(
        {"status": "success", "message": "All workers are operational"},
        status_code=200,
    )


@router.get("/swagger_healthcheck", response_class=PlainTextResponse)
def swagger_healthcheck():
    if os.getenv("SWAGGER_HOST") is None:
        return PlainTextResponse(
            "Need to set SWAGGER_HOST ENV variable",
            status_code=503,
        )
    return PlainTextResponse("Swagger UI configured", status_code=200)
