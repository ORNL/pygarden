#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Flask API Routes for Health Checks
==================================

This module provides Flask blueprint routes for health checking various services
including PostgreSQL, MSSQL, Redis, RabbitMQ, Celery, and Swagger.

The health check endpoints validate connectivity and basic functionality of
external dependencies used by the application.

:author: Kyle Medlen
:version: 1.0
"""

import os
import sys
import psycopg
import requests
import redis

from flask import Blueprint
from flask import Flask, jsonify, request
from celery import Celery

from pygarden.logz import create_logger
logger = create_logger()

blueprint = Blueprint('flask', __name__)

@blueprint.route('/healthcheck', methods=['GET'])
def health_check():
    """ Basic health check endpoint.

    Provides a simple health check that returns OK status to verify
    the Flask application is running and responsive.

    :returns: JSON response with status OK and HTTP 200
    :rtype: tuple[flask.Response, int]

    **Example Response:**

    .. code-block:: json

        {"status": "OK"}
    """
    return jsonify(status="OK"), 200

@blueprint.route('/postgres_healthcheck', methods=['GET'])
def postgres_healthcheck():
    """ PostgreSQL database health check endpoint.

    Validates PostgreSQL database connectivity by attempting to connect
    and execute a version query. Checks for required environment variables
    and establishes a test connection.

    **Required Environment Variables:**

    - Database: ` `DATABASE_DB_PG` `, ` `DATABASE_DB` `, or ` `PG_DATABASE` `
    - User: ` `DATABASE_USER` `, ` `DATABASE_USER_PG` `, or ` `PG_USER` `
    - Password: ` `DATABASE_PW` `, ` `DATABASE_PW_PG` `, or ` `PG_PASSWORD` `
    - Host: ` `DATABASE_HOST` `, ` `DATABASE_HOST_PG` `, or ` `PG_HOST` `
    - Port: ` `DATABASE_PORT` `, ` `DATABASE_PORT_PW` `, or ` `PG_PORT` `

    :returns: Success message with HTTP 200 if database is accessible,
              error message with HTTP 503 if connection fails
    :rtype: tuple[str, int]

    :raises psycopg.Error: When database connection fails

    **Example Responses:**

    - Success: ` `"Database is running"` ` (200)
    - Error: ` `"Error connecting to PostgreSQL: <error_details>"` ` (503)
    """
    env_vars = ["DATABASE_DB_PG", "DATABASE_DB", "PG_DATABASE"]
    dbname = [var for var in env_vars if os.getenv(var) is not None]
    if not dbname:
        return "Need to set either DATABASE_DB_PG or DATABASE_DB ENV variables", 503
    elif len(dbname) > 1:
        logger.warn("Found multiple PostgreSQL ENV vars, using first one: " + str(dbname[0]))
    elif dbname[0] == 'postgres':
        logger.warn("Using default database name: " + dbname[0])
    else:
        logger.info("Database name set to: " + str(dbname[0]))

    env_vars = ["DATABASE_USER", "DATABASE_USER_PG", "PG_USER"]
    user = [var for var in env_vars if os.getenv(var) is not None]
    if not user:
        return "Need to set either DATABASE_USER_PG or DATABASE_USER ENV variables", 503
    elif len(user) > 1:
        logger.warn("Found multiple PostgreSQL ENV vars, using first one: " + str(user[0]))
    elif user[0] == 'postgres':
        logger.warn("Using default user: " + user[0])
    else:
        logger.info("Database User set to: " + str(user))

    env_vars = ["DATABASE_PW", "DATABASE_PW_PG", "PG_PASSWORD"]
    password = [var for var in env_vars if os.getenv(var) is not None]
    if not password:
        return "Need to set either DATABASE_PW_PG or DATABASE_PW ENV variables", 503
    elif password[0] == 'postgres':
        logger.warn("Using default password: " + password)
    else:
        logger.info("Database Password set to: " + str(password))

    env_vars = ["DATABASE_HOST", "DATABASE_HOST_PG", "PG_HOST"]
    host = [var for var in env_vars if os.getenv(var) is not None]
    if not host:
        return "Need to set either DATABASE_HOST_PG or DATABASE_HOST ENV variables", 503
    elif host[0] == 'localhost':
        logger.warn("Using default host: " + host)
    else:
        logger.info("Database host set to: " + str(host))

    env_vars = ["DATABASE_PORT", "DATABASE_PORT_PW", "PG_PORT"]
    port = [var for var in env_vars if os.getenv(var) is not None]
    if not port:
        return "Need to set either DATABASE_PORT_PG or DATABASE_PORT ENV variables", 503
    elif port[0] == 5432:
        logger.warn("Using default port: " + str(port))
    else:
        logger.info("Database port set to: " + str(port))

    try:
        conn = psycopg.connect(
            dbname=dbname,
            user=user,
            password=password,
            host=host, port=port
        )
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        db_version = cursor.fetchone()
        cursor.close()
        conn.close()
        if db_version:
            return "Database is running", 200
        else:
            return "Database does not seem to be running", 503

    except psycopg.Error as e:
        logger.critical("Error connecting to PostgreSQL:" + str(e))
        return "Error connecting to PostgreSQL:" + str(e), 503

@blueprint.route('/mssql_healthcheck', methods=['GET'])
def mssql_healthcheck():
    """ Microsoft SQL Server database health check endpoint.

   Validates MSSQL database connectivity by attempting to connect
   and execute a version query. Note: Currently uses psycopg which
   is incorrect for MSSQL - should use pymssql or pyodbc.

   **Required Environment Variables:**

   - Database: ` `DATABASE_DB_MS` ` or ` `DATABASE_DB` `
   - User: ` `DATABASE_USER_MS` ` or ` `DATABASE_USER` `
   - Password: ` `DATABASE_PW_MS` ` or ` `DATABASE_PW` `
   - Host: ` `DATABASE_HOST_MS` ` or ` `DATABASE_HOST` `
   - Port: ` `DATABASE_PORT_MS` ` or ` `DATABASE_PORT_MS` `

   :returns: Success message with HTTP 200 if database is accessible,
             error message with HTTP 503 if connection fails
   :rtype: tuple[str, int]

   :raises psycopg.Error: When database connection fails

   .. warning::
      This function incorrectly uses psycopg for MSSQL connections.
      Should be updated to use pymssql or pyodbc.
   """
    env_vars = ["DATABASE_DB_MS", "DATABASE_DB"]
    dbname = [var for var in env_vars if os.getenv(var) is not None]
    if not dbname:
        return "Need to set either DATABASE_DB_MS or DATABASE_DB ENV variables", 503
    elif dbname[0] == 'CommonDB':
        logger.warn("Using default database name: " + dbname)
    else:
        logger.info("Database name set to: " + str(dbname))

    env_vars = ["DATABASE_USER_MS", "DATABASE_USER"]
    user = [var for var in env_vars if os.getenv(var) is not None]
    if not user:
        return "Need to set either DATABASE_USER_MS or DATABASE_USER ENV variables", 503
    elif user[0] == 'sa':
        logger.warn("Using default user: " + user)
    else:
        logger.info("Database User set to: " + str(user))

    env_vars = ["DATABASE_PW_MS", "DATABASE_PW"]
    password = [var for var in env_vars if os.getenv(var) is not None]
    if not password:
        return "Need to set either DATABASE_PW_MS or DATABASE_PW ENV variables", 503
    elif password[0] == '5nowDog5':
        logger.warn("Using default password: " + password)
    else:
        logger.info("Database Password set to: " + str(password))

    env_vars = ["DATABASE_HOST_MS", "DATABASE_HOST"]
    host = [var for var in env_vars if os.getenv(var) is not None]
    if not host:
        return "Need to set either DATABASE_HOST_MS or DATABASE_HOST ENV variables", 503
    elif host[0] == 'localhost':
        logger.warn("Using default host: " + host)
    else:
        logger.info("Database host set to: " + str(host))

    env_vars = ["DATABASE_PORT_MS", "DATABASE_PORT_MS"]
    port = [var for var in env_vars if os.getenv(var) is not None]
    if not port:
        return "Need to set either DATABASE_PORT_MS or DATABASE_PORT ENV variables", 503
    elif port[0] == 1433:
        logger.warn("Using default port: " + str(port))
    else:
        logger.info("Database port set to: " + str(port))

    try:
        conn = psycopg.connect(
            dbname=dbname,
            user=user,
            password=password,
            host=host,
            port=port
        )
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        db_version = cursor.fetchone()
        cursor.close()
        conn.close()
        if db_version:
            return "Database is running", 200
        else:
            return "Database does not seem to be running", 503

    except psycopg.Error as e:
        logger.critical("Error connecting to PostgreSQL:" + str(e))
        return "Error connecting to PostgreSQL:" + str(e), 503

@blueprint.route('/rabbitmq_healthcheck', methods=['GET'])
def rabbitmq_healthcheck():
    """ RabbitMQ message broker health check endpoint.

Validates RabbitMQ connectivity by making an HTTP request to the
   management API endpoint.

   **Required Environment Variables:**

   - ` `RABBIT_MQ_HOST` `: RabbitMQ management API host URL
   - ` `RABBIT_MQ_PORT` `: RabbitMQ management API port

   :returns: Success message with HTTP 200 if RabbitMQ is accessible,
             error message with HTTP 503 if connection fails
   :rtype: tuple[str, int]

   :raises requests.RequestException: When HTTP request fails

   **Example Responses:**

   - Success: ` `"Healthcheck good"` ` (200)
   - Error: ` `"Healthcheck failed"` ` (varies based on response code)
   """
    host = "RABBIT_MQ_HOST"
    if not os.getenv(host):
        return "Need to set RABBIT_MQ_HOST variable", 503
    elif host == 'localhost':
        logger.warn("Using default host: " + host)
    else:
        logger.info("RabbitMQ host set to: " + str(host))

    port = "RABBIT_MQ_PORT"
    if not os.getenv(port):
        return "Need to set RABBIT_MQ_PORT ENV variable", 503
    elif port == 15692:
        logger.warn("Using default port: " + str(port))
    else:
        logger.info("RabbitMQ port set to: " + str(port))

    r = requests.get(host)
    if r.status_code == 200:
        return "Healthcheck good", 200
    else:
        return "Healthcheck failed", r.status_code

@blueprint.route('/redis_healthcheck', methods=['GET'])
def redis_healthcheck():
    """ Redis cache health check endpoint.

    Validates Redis connectivity by attempting to set and retrieve
    a test key-value pair in a hash.

    **Required Environment Variables:**

    - ` `REDIS_HOST` `: Redis server hostname or IP address
    - ` `REDIS_PORT` `: Redis server port number

    :returns: Success message with HTTP 200 if Redis is accessible,
              error message with HTTP 500/503 if connection fails
    :rtype: tuple[str, int]

    :raises Exception: When Redis connection or operations fail

    **Example Responses:**

    - Success: ` `"Healthcheck good"` ` (200)
    - Empty data: ` `"Queried Redis, but data was empty"` ` (200)
    - Unknown issue: ` `"Redis may be running, but there was an unknown issue"` ` (200)
    - Error: ` `"There was an error, check your redis cluster"` ` (500)
    """
    host = "REDIS_HOST"
    if not os.getenv(host):
        return "Need to set REDIS_HOST ENV variable", 503
    elif host == 'localhost':
        logger.warn("Using default host: " + host)
    else:
        logger.info("RabbitMQ host set to: " + str(host))

    port = "REDIS_PORT"
    if not os.getenv(port):
        return "Need to set REDIS_PORT ENV variable", 503
    elif port == 6379:
        logger.warn("Using default port: " + str(port))
    else:
        logger.info("RabbitMQ port set to: " + str(port))
    try:
        r = redis.Redis(host=host, port=port, decode_responses=True)
        r.hset('test', mapping={'get': 'healthcheck'})
        res = r.hgetall('test')
        if res == {}:
            return "Queried Redis, but data was empty", 200
        elif 'get' in res and res['get'] == 'healthcheck':  # ✅ Check the actual data
            return "Healthcheck good", 200
        else:
            return "Redis may be running, but there was an unknown issue", 200
    except Exception:
        return "There was an error, check your redis cluster", 500

def make_celery():
    """
        Create and configure a Celery application instance.

        Creates a new Celery instance using the Redis broker URL from environment
        variables. Logs critical error if REDIS_BROKER environment variable is not set.

        **Required Environment Variables:**

        - ``REDIS_BROKER``: Redis broker URL for Celery (e.g., 'redis://localhost:6379/0')

        :returns: Configured Celery application instance
        :rtype: celery.Celery

        :raises: Logs critical error if REDIS_BROKER is not set, but still returns Celery instance

        **Example Usage:**

        .. code-block:: python

            celery_app = make_celery()
            inspector = celery_app.control.inspect()
        """
    if not os.getenv('REDIS_BROKER'):
        logger.critical("No REDIS_BROKER ENV variable found, please set it!")
    else:
        broker = os.getenv('REDIS_BROKER')
    return Celery(broker=os.getenv('REDIS_BROKER'))  # Replace with your broker URL

@blueprint.route('/celery_healthcheck')
def celery_healthcheck():
    """
        Celery worker health check endpoint.

        Validates Celery worker connectivity by creating a Celery instance and
        pinging active workers through the control inspector interface.

        **Required Environment Variables:**

        - ``REDIS_BROKER``: Redis broker URL for Celery communication

        :returns: JSON response indicating worker status with appropriate HTTP status code
        :rtype: tuple[flask.Response, int]

        :raises Exception: When Celery connection or inspection fails

        **Example Responses:**

        - Success: ``{"status": "success", "message": "All workers are operational"}`` (200)
        - No workers: ``{"status": "failure", "message": "No active workers found"}`` (503)
        - Error: ``{"status": "failure", "message": "<error_details>"}`` (500)

        **Response Schema:**

        .. code-block:: json

            {
                "status": "success|failure",
                "message": "descriptive message"
            }
        """
    try:
        celery = make_celery()  # Create a new Celery instance just for this check
        inspector = celery.control.inspect()
        active_workers = inspector.ping()

        if not active_workers:
            return jsonify({"status": "failure", "message": "No active workers found"}), 503

        return jsonify({"status": "success", "message": "All workers are operational"}), 200

    except Exception as e:
        return jsonify({"status": "failure", "message": str(e)}), 500

@blueprint.route('/swagger_healthcheck')
def swagger_healthcheck():
    """
        Swagger UI health check endpoint.

        Validates that the Swagger UI host environment variable is properly configured.
        Currently only checks for environment variable presence and logs the configuration.

        **Required Environment Variables:**

        - ``SWAGGER_HOST``: Swagger UI host URL or hostname

        :returns: Success message with HTTP 200 if environment variable is set,
                  error message with HTTP 503 if not configured
        :rtype: tuple[str, int]

        **Example Responses:**

        - Error: ``"Need to set SWAGGER_HOST ENV variable"`` (503)
        - Success: Function completes but doesn't return explicit success response

        """
    host = "SWAGGER_HOST"
    if not os.getenv(host):
        return "Need to set SWAGGER_HOST ENV variable", 503
    else:
        logger.info("swaggerui host set to: " + str(host))
        return "Swagger UI configured", 200
