import os

import psycopg
import pymssql
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from pygarden.api.fastapi.routes import router


@pytest.fixture
def app():
    """Create FastAPI app for testing"""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    """Create test client"""
    return TestClient(app)


class TestHealthCheck:
    def test_health_check(self, client):
        """Test basic health check endpoint"""
        response = client.get('/healthcheck')
        assert response.status_code == 200
        assert response.json()['status'] == 'OK'


class TestPostgresHealthCheck:
    @patch.dict(os.environ, {
        'DATABASE_DB_PG': 'testdb',
        'DATABASE_USER': 'testuser',
        'DATABASE_PW': 'testpass',
        'DATABASE_HOST': 'localhost',
        'DATABASE_PORT': '5432'
    })
    @patch('psycopg.connect')
    def test_postgres_healthcheck_success(self, mock_connect, client):
        """Test successful PostgreSQL connection"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = ('PostgreSQL 13.0',)
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        response = client.get('/postgres_healthcheck')
        assert response.status_code == 200
        assert "Database is running" in response.text

    def test_postgres_healthcheck_missing_env(self, client):
        """Test missing PostgreSQL environment variables"""
        with patch.dict(os.environ, {}, clear=True):
            response = client.get('/postgres_healthcheck')
            assert response.status_code == 503
            assert "Need to set either DATABASE_DB_PG" in response.text

    @patch.dict(os.environ, {
        'DATABASE_DB_PG': 'testdb',
        'DATABASE_USER': 'testuser',
        'DATABASE_PW': 'testpass',
        'DATABASE_HOST': 'localhost',
        'DATABASE_PORT': '5432'
    })
    @patch('psycopg.connect')
    def test_postgres_healthcheck_connection_error(self, mock_connect, client):
        """Test PostgreSQL connection error"""
        mock_connect.side_effect = psycopg.Error("Connection failed")

        response = client.get('/postgres_healthcheck')
        assert response.status_code == 503
        assert "Error connecting to PostgreSQL" in response.text


class TestMSSQLHealthCheck:
    @patch.dict(os.environ, {
        'DATABASE_DB_MS': 'testdb',
        'DATABASE_USER_MS': 'testuser',
        'DATABASE_PW_MS': 'testpass',
        'DATABASE_HOST_MS': 'localhost',
        'DATABASE_PORT_MS': '1433'
    })
    @patch('pymssql.connect')
    def test_mssql_healthcheck_success(self, mock_connect, client):
        """Test successful MSSQL connection"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = ('Microsoft SQL Server',)
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        response = client.get('/mssql_healthcheck')
        assert response.status_code == 200
        assert "Database is running" in response.text

    def test_mssql_healthcheck_missing_env(self, client):
        """Test missing MSSQL environment variables"""
        with patch.dict(os.environ, {}, clear=True):
            response = client.get('/mssql_healthcheck')
            assert response.status_code == 503
            assert "Need to set either DATABASE_DB_MS" in response.text

    @patch.dict(os.environ, {
        'DATABASE_DB_MS': 'testdb',
        'DATABASE_USER_MS': 'testuser',
        'DATABASE_PW_MS': 'testpass',
        'DATABASE_HOST_MS': 'localhost',
        'DATABASE_PORT_MS': '1433'
    })
    @patch('pymssql.connect')
    def test_mssql_healthcheck_connection_error(self, mock_connect, client):
        """Test MSSQL connection error"""
        mock_connect.side_effect = pymssql.Error("Connection failed")

        response = client.get('/mssql_healthcheck')
        assert response.status_code == 503
        assert "Error connecting to MSSQL" in response.text


class TestRedisHealthCheck:
    @patch.dict(os.environ, {
        'REDIS_HOST': 'localhost',
        'REDIS_PORT': '6379'
    })
    @patch('redis.Redis')
    def test_redis_healthcheck_success(self, mock_redis, client):
        """Test successful Redis connection"""
        mock_redis_instance = MagicMock()
        mock_redis_instance.hgetall.return_value = {'get': 'healthcheck'}
        mock_redis.return_value = mock_redis_instance

        response = client.get('/redis_healthcheck')
        assert response.status_code == 200
        assert "Healthcheck good" in response.text

    def test_redis_healthcheck_missing_env(self, client):
        """Test missing Redis environment variables"""
        with patch.dict(os.environ, {}, clear=True):
            response = client.get('/redis_healthcheck')
            assert response.status_code == 503
            assert "Need to set REDIS_HOST ENV variable" in response.text

    @patch.dict(os.environ, {
        'REDIS_HOST': 'localhost',
        'REDIS_PORT': '6379'
    })
    @patch('redis.Redis')
    def test_redis_healthcheck_connection_error(self, mock_redis, client):
        """Test Redis connection error"""
        mock_redis.side_effect = Exception("Connection failed")

        response = client.get('/redis_healthcheck')
        assert response.status_code == 500
        assert "There was an error, check your redis cluster" in response.text


class TestRabbitMQHealthCheck:
    @patch.dict(os.environ, {
        'RABBIT_MQ_HOST': 'http://localhost:15672',
        'RABBIT_MQ_PORT': '15672'
    })
    @patch('requests.get')
    def test_rabbitmq_healthcheck_success(self, mock_get, client):
        """Test successful RabbitMQ health check"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        response = client.get('/rabbitmq_healthcheck')
        assert response.status_code == 200
        assert "Healthcheck good" in response.text

    def test_rabbitmq_healthcheck_missing_env(self, client):
        """Test missing RabbitMQ environment variables"""
        with patch.dict(os.environ, {}, clear=True):
            response = client.get('/rabbitmq_healthcheck')
            assert response.status_code == 503
            assert "Need to set RABBIT_MQ_HOST variable" in response.text


class TestCeleryHealthCheck:
    @patch.dict(os.environ, {'REDIS_BROKER': 'redis://localhost:6379/0'})
    @patch('celery.Celery')
    def test_celery_healthcheck_success(self, mock_celery, client):
        """Test successful Celery health check"""
        mock_celery_instance = MagicMock()
        mock_inspector = MagicMock()
        mock_inspector.ping.return_value = {'worker1': 'pong'}
        mock_celery_instance.control.inspect.return_value = mock_inspector
        mock_celery.return_value = mock_celery_instance

        response = client.get('/celery_healthcheck')
        assert response.status_code == 200
        assert response.json()['status'] == 'success'

    @patch.dict(os.environ, {'REDIS_BROKER': 'redis://localhost:6379/0'})
    @patch('celery.Celery')
    def test_celery_healthcheck_no_workers(self, mock_celery, client):
        """Test Celery health check with no active workers"""
        mock_celery_instance = MagicMock()
        mock_inspector = MagicMock()
        mock_inspector.ping.return_value = None
        mock_celery_instance.control.inspect.return_value = mock_inspector
        mock_celery.return_value = mock_celery_instance

        response = client.get('/celery_healthcheck')
        assert response.status_code == 503
        assert response.json()['status'] == 'failure'


class TestSwaggerHealthCheck:
    def test_swagger_healthcheck_missing_env(self, client):
        """Test missing Swagger environment variable"""
        with patch.dict(os.environ, {}, clear=True):
            response = client.get('/swagger_healthcheck')
            assert response.status_code == 503
            assert "Need to set SWAGGER_HOST ENV variable" in response.text
