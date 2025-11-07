import pytest
import os
import json

from unittest.mock import patch, MagicMock
from flask import Flask

from pygarden.api.flask.routes import blueprint


@pytest.fixture
def app():
    """Create Flask app for testing"""
    app = Flask(__name__)
    app.register_blueprint(blueprint)
    app.config['TESTING'] = True
    return app


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


class TestHealthCheck:
    def test_health_check(self, client):
        """Test basic health check endpoint"""
        response = client.get('/healthcheck')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'OK'


class TestPostgresHealthCheck:
    @patch.dict(os.environ, {
        'DATABASE_DB_PG': 'testdb',
        'DATABASE_USER': 'testuser',
        'DATABASE_PW': 'testpass',
        'DATABASE_HOST': 'localhost',
        'DATABASE_PORT': '5432'
    })
    @patch('pygarden.api.flask.routes.psycopg2.connect')
    def test_postgres_healthcheck_success(self, mock_connect, client):
        """Test successful PostgreSQL connection"""
        # Mock database connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = ('PostgreSQL 13.0',)
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        response = client.get('/postgres_healthcheck')
        assert response.status_code == 200
        assert b"Database is running" in response.data

    def test_postgres_healthcheck_missing_env(self, client):
        """Test missing environment variables"""
        with patch.dict(os.environ, {}, clear=True):
            response = client.get('/postgres_healthcheck')
            assert response.status_code == 503
            assert b"Need to set either DATABASE_DB_PG" in response.data

    @patch.dict(os.environ, {
        'DATABASE_DB_PG': 'testdb',
        'DATABASE_USER': 'testuser',
        'DATABASE_PW': 'testpass',
        'DATABASE_HOST': 'localhost',
        'DATABASE_PORT': '5432'
    })
    @patch('pygarden.api.flask.routes.psycopg2.connect')
    def test_postgres_healthcheck_connection_error(self, mock_connect, client):
        """Test PostgreSQL connection error"""
        import psycopg2
        mock_connect.side_effect = psycopg2.Error("Connection failed")

        response = client.get('/postgres_healthcheck')
        assert response.status_code == 503
        assert b"Error connecting to PostgreSQL" in response.data


class TestRedisHealthCheck:
    @patch.dict(os.environ, {
        'REDIS_HOST': 'localhost',
        'REDIS_PORT': '6379'
    })
    @patch('pygarden.api.flask.routes.redis.Redis')
    def test_redis_healthcheck_success(self, mock_redis, client):
        """Test successful Redis connection"""
        mock_redis_instance = MagicMock()
        mock_redis_instance.hgetall.return_value = {'get': 'healthcheck'}
        mock_redis.return_value = mock_redis_instance

        response = client.get('/redis_healthcheck')
        assert response.status_code == 200
        assert b"Healthcheck good" in response.data

    def test_redis_healthcheck_missing_env(self, client):
        """Test missing Redis environment variables"""
        with patch.dict(os.environ, {}, clear=True):
            response = client.get('/redis_healthcheck')
            assert response.status_code == 503
            assert b"Need to set REDIS_HOST ENV variable" in response.data

    @patch.dict(os.environ, {
        'REDIS_HOST': 'localhost',
        'REDIS_PORT': '6379'
    })
    @patch('pygarden.api.flask.routes.redis.Redis')
    def test_redis_healthcheck_connection_error(self, mock_redis, client):
        """Test Redis connection error"""
        mock_redis.side_effect = Exception("Connection failed")

        response = client.get('/redis_healthcheck')
        assert response.status_code == 500
        assert b"There was an error, check your redis cluster" in response.data


class TestRabbitMQHealthCheck:
    @patch.dict(os.environ, {
        'RABBIT_MQ_HOST': 'http://localhost:15672',
        'RABBIT_MQ_PORT': '15672'
    })
    @patch('pygarden.api.flask.routes.requests.get')
    def test_rabbitmq_healthcheck_success(self, mock_get, client):
        """Test successful RabbitMQ health check"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        response = client.get('/rabbitmq_healthcheck')
        assert response.status_code == 200
        assert b"Healthcheck good" in response.data

    def test_rabbitmq_healthcheck_missing_env(self, client):
        """Test missing RabbitMQ environment variables"""
        with patch.dict(os.environ, {}, clear=True):
            response = client.get('/rabbitmq_healthcheck')
            assert response.status_code == 503
            assert b"Need to set RABBIT_MQ_HOST variable" in response.data


class TestCeleryHealthCheck:
    @patch.dict(os.environ, {'REDIS_BROKER': 'redis://localhost:6379/0'})
    @patch('pygarden.api.flask.routes.Celery')
    def test_celery_healthcheck_success(self, mock_celery, client):
        """Test successful Celery health check"""
        mock_celery_instance = MagicMock()
        mock_inspector = MagicMock()
        mock_inspector.ping.return_value = {'worker1': 'pong'}
        mock_celery_instance.control.inspect.return_value = mock_inspector
        mock_celery.return_value = mock_celery_instance

        response = client.get('/celery_healthcheck')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'success'

    @patch.dict(os.environ, {'REDIS_BROKER': 'redis://localhost:6379/0'})
    @patch('pygarden.api.flask.routes.Celery')
    def test_celery_healthcheck_no_workers(self, mock_celery, client):
        """Test Celery health check with no active workers"""
        mock_celery_instance = MagicMock()
        mock_inspector = MagicMock()
        mock_inspector.ping.return_value = None
        mock_celery_instance.control.inspect.return_value = mock_inspector
        mock_celery.return_value = mock_celery_instance

        response = client.get('/celery_healthcheck')
        assert response.status_code == 503
        data = json.loads(response.data)
        assert data['status'] == 'failure'


class TestSwaggerHealthCheck:
    def test_swagger_healthcheck_missing_env(self, client):
        """Test missing Swagger environment variable"""
        with patch.dict(os.environ, {}, clear=True):
            response = client.get('/swagger_healthcheck')
            assert response.status_code == 503
            assert b"Need to set SWAGGER_HOST ENV variable" in response.data
