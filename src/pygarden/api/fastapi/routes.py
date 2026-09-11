"""FastAPI routes for service health checks."""

import os

from fastapi import APIRouter
from fastapi.responses import JSONResponse, PlainTextResponse

from pygarden.env import check_environment as ce

router = APIRouter(tags=["health"])


@router.get("/healthcheck")
def health_check():
    return {"status": "OK"}


@router.get("/postgres_healthcheck", response_class=PlainTextResponse)
def postgres_healthcheck():
    try:
        import psycopg
    except ImportError:
        return PlainTextResponse(
            'PostgreSQL health check requires the "postgres" extra',
            status_code=503,
        )

    dbname = ce("DATABASE_DB_PG", ce("DATABASE_DB", ce("PG_DATABASE")))
    user = ce("DATABASE_USER", ce("DATABASE_USER_PG", ce("PG_USER")))
    password = ce("DATABASE_PW", ce("DATABASE_PW_PG", ce("PG_PASSWORD")))
    host = ce("DATABASE_HOST", ce("DATABASE_HOST_PG", ce("PG_HOST")))
    port = ce("DATABASE_PORT", ce("DATABASE_PORT_PG", ce("PG_PORT")))

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
    try:
        import pymssql
    except ImportError:
        return PlainTextResponse(
            'MSSQL health check requires the "mssql" extra',
            status_code=503,
        )

    dbname = ce("DATABASE_DB_MS", ce("DATABASE_DB"))
    user = ce("DATABASE_USER_MS", ce("DATABASE_USER"))
    password = ce("DATABASE_PW_MS", ce("DATABASE_PW"))
    host = ce("DATABASE_HOST_MS", ce("DATABASE_HOST"))
    port = ce("DATABASE_PORT_MS", ce("DATABASE_PORT"))

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
    try:
        import requests
    except ImportError:
        return PlainTextResponse(
            'RabbitMQ health check requires the "requests" package',
            status_code=503,
        )

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
    try:
        import redis
    except ImportError:
        return PlainTextResponse(
            'Redis health check requires the "redis" package',
            status_code=503,
        )

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
    from celery import Celery

    return Celery(broker=os.getenv("REDIS_BROKER"))


@router.get("/celery_healthcheck")
def celery_healthcheck():
    try:
        celery = make_celery()
        inspector = celery.control.inspect()
        active_workers = inspector.ping()
    except ImportError:
        return JSONResponse(
            {
                "status": "failure",
                "message": 'Celery health check requires the "celery" package',
            },
            status_code=503,
        )
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
