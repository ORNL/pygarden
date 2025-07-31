"""Test MinioMixin class."""

import os
from unittest.mock import MagicMock, patch

import pytest
from moto import mock_aws
from pygarden.mixins.minio_mixin import MinioMixin


@pytest.fixture(scope="function", autouse=True)
def setup_environment(tmp_path):
    """Create a temporary directory and files for the test."""
    test_dir = tmp_path / "tests" / "data"
    test_dir.mkdir(parents=True, exist_ok=True)
    test_file_path = test_dir / "test.txt"
    test_file_path.write_text("content")
    retrieved_file_path = test_dir / "test_retrieved.txt"

    # Setting environment variables for the test
    os.environ["TEST_FILE_PATH"] = str(test_file_path)
    os.environ["RETRIEVED_FILE_PATH"] = str(retrieved_file_path)


@pytest.fixture(autouse=True, scope="function")
def aws_credentials():
    """Mocked AWS credentials."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_REGION"] = "us-east-1"


@mock_aws
class TestMinioMixin:
    """Test class for MinioMixin."""

    @pytest.fixture(autouse=True)
    def setup_class(self, aws_credentials, setup_environment):
        """Set up class with Minio client mocks."""
        with patch(
            "pygarden.env.check_environment",
            side_effect=lambda key: "localhost:9000" if key == "MINIO_ENDPOINT" else "minio",
        ):
            with patch("pygarden.mixins.minio_mixin.MinioMixin.get_minio_client") as mock_get_minio_client:
                mock_client = MagicMock()
                mock_client.create_bucket = MagicMock(return_value=None)
                mock_client.list_objects = MagicMock(return_value=[MagicMock(object_name="test.txt")])
                mock_client.get_object = MagicMock(return_value=MagicMock(read=MagicMock(return_value=b"content")))
                mock_client.fput_object = MagicMock(return_value=None)
                mock_client.fget_object = MagicMock(return_value=None)

                # Simulate file retrieval by actually creating the file
                def mock_fget_object(bucket_name, object_name, file_path):
                    with open(file_path, "w") as f:
                        f.write("content")

                mock_client.fget_object.side_effect = mock_fget_object
                mock_client._http = MagicMock()

                mock_get_minio_client.return_value = mock_client
                self.mixin = MinioMixin()

    def test_upload_file(self):
        """Test the upload_file method."""
        test_file_path = os.getenv("TEST_FILE_PATH")
        self.mixin.upload_file(test_file_path, "test.txt")
        objects = list(self.mixin.minio.list_objects(self.mixin.bucket_name))
        assert len(objects) == 1 and objects[0].object_name == "test.txt"
        body = self.mixin.minio.get_object(self.mixin.bucket_name, "test.txt").read().decode()
        assert body == "content"

    def test_retrieve_file(self):
        """Test the retrieve_file method."""
        retrieved_file_path = os.getenv("RETRIEVED_FILE_PATH")
        self.mixin.retrieve_file("test.txt", retrieved_file_path)
        with open(retrieved_file_path, "r") as file:
            assert file.read() == "content"
