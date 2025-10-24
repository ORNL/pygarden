"""Provides a Minio Mixin"""

from minio import Minio
from minio.error import S3Error

from pygarden.env import check_environment as ce
from pygarden.logz import create_logger


class MinioMixin:
    """
    Provides a wrapper around the Minio client for uploading and retrieving files.

    Attributes
    ----------
        minio: A Minio client instance.
        bucket_name: The name of the Minio bucket, defaults to the os environment variable "MINIO_BUCKET_NAME".
        logger: A logger instance, used for logging messages and is defined in the `pygarden.logz` module.
    """

    def __init__(self, bucket_name: str = None):
        """
        Initialize the MinioMixin.

        :param bucket_name: The name of the Minio bucket. If not provided,
                            it defaults to the environment variable "MINIO_BUCKET_NAME".
        """
        self.minio: Minio = self.get_minio_client()
        self.bucket_name = bucket_name or ce("MINIO_BUCKET_NAME")
        self.logger = create_logger()

    @staticmethod
    def get_minio_client():
        """
        Create a Minio client instance.

        Uses the os environment variables of MINIO_ENDPOINT, MINIO_ACCESS_KEY, and MINIO_SECRET_KEY
        to create the client.
        :returns: A Minio client instance.
        :rtype: Minio
        """
        return Minio(
            endpoint=ce("MINIO_ENDPOINT"),
            access_key=ce("MINIO_ACCESS_KEY"),
            secret_key=ce("MINIO_SECRET_KEY"),
        )

    def upload_file(self, file_path: str, object_name: str):
        """
        Upload a file to Minio.

        :param file_path: The path to the file to be uploaded.
        :param object_name: The name of the object to be created in Minio.
        """
        try:
            self.minio.fput_object(self.bucket_name, object_name, file_path)
        except S3Error as exc:
            self.logger.info(f"Error uploading file to Minio: {exc}")

    def retrieve_file(self, object_name: str, file_path: str):
        """
        Retrieve a file from Minio.

        :param object_name: The name of the object to be retrieved from Minio.
        :param file_path: The path to save the retrieved file.
        """
        try:
            self.minio.fget_object(self.bucket_name, object_name, file_path)
        except S3Error as exc:
            self.logger.info(f"Error retrieving file from Minio: {exc}")
