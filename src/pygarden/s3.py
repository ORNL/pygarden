"""Provides a S3 Client built on top of boto3."""

import fnmatch
import io
from datetime import datetime
from typing import Optional, TypedDict
from urllib.parse import urlencode

import boto3
from boto3.s3.transfer import TransferConfig
from botocore.exceptions import ClientError
from botocore.response import StreamingBody
from humanize import naturalsize

from pygarden.env import boolify
from pygarden.env import check_environment as ce
from pygarden.logz import create_logger


class S3Object(TypedDict):
    """
    Represents a single S3 object as returned by list_objects_v2.

    Attributes
    ----------
    Key : str
        The full object key (path) within the bucket.
    LastModified : datetime
        The date and time the object was last modified.
    ETag : str
        The entity tag, an MD5 hash of the object used for integrity checking.
    Size : int
        The size of the object in bytes.
    StorageClass : str
        The storage class of the object (e.g. STANDARD, GLACIER).

    """

    Key: str
    LastModified: datetime
    ETag: str
    Size: int
    StorageClass: str


class S3:
    """
    Provides a wrapper around the boto3 client for uploading and moving files.

    Attributes
    ----------
    client : boto3.client
        A boto3 S3 client instance.
    logger : logging.Logger
        A logger instance, used for logging messages and is defined in the `pygarden.logz` module.


    """

    DEFAULT_ENDPOINT = ce("S3_ENDPOINT", ce("MINIO_ENDPOINT"))
    DEFAULT_ACCESS_KEY = ce("S3_ACCESS_KEY", ce("MINIO_ACCESS_KEY"))
    DEFAULT_SECRET_KEY = ce("S3_SECRET_KEY", ce("MINIO_SECRET_KEY"))
    DEFAULT_USE_SSL = ce("S3_USE_SSL", ce("MINIO_USE_SSL"))
    DEFAULT_REGION = ce("S3_REGION")

    # AWS hard limit for a single copy_object call; anything at or above requires multipart
    MAXIMUM_MULTIPART_THRESHOLD = 5 * 1024**3  # 5 GiB
    DEFAULT_MULTIPART_THRESHOLD = ce("S3_MULTIPART_THRESHOLD", MAXIMUM_MULTIPART_THRESHOLD)

    DEFAULT_MULTIPART_CHUNKSIZE = ce(
        "S3_MULTIPART_CHUNKSIZE", 256 * 1024**2
    )  # 256 MiB per part (tune to taste, min is 5 MiB)
    MINIMUM_MULTIPART_CHUNKSIZE = 5 * 1024**2  # 5 MiB per part minimum size per AWS

    DEFAULT_USE_THREADS = ce("S3_USE_THREADS", True)  # True is boto3 default
    DEFAULT_MAX_CONCURRENCY = ce("S3_MAX_CONCURRENCY", 10)  # 10 is boto3 default

    def __init__(
        self,
        *,
        env_prefix: str | None = None,
        profile: str | None = None,
        endpoint: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        use_ssl: bool | None = None,
        region: str | None = None,
        multipart_threshold: int | None = None,
        multipart_chunksize: int | None = None,
        use_threads: bool | None = None,
        max_concurrency: int | None = None,
    ):
        """
        Initialize S3 Client object.

        Credentials and connection settings are resolved in the following priority order:
        explicit argument > prefixed env var (if env_prefix provided) > default env var.

        :param env_prefix: Optional prefix for environment variable lookups. When provided,
            variables like ``{env_prefix}_ENDPOINT`` are checked before the default S3_* vars.
        :param profile: AWS profile name. Defaults to None
        :param endpoint: The endpoint URL of the S3-compatible service. Defaults to
            ``{env_prefix}_ENDPOINT`` > ``S3_ENDPOINT`` env variable.
        :param access_key: Access key credential. Defaults to
            ``{env_prefix}_ACCESS_KEY`` > ``S3_ACCESS_KEY`` env variable.
        :param secret_key: Secret key credential. Defaults to
            ``{env_prefix}_SECRET_KEY`` > ``S3_SECRET_KEY`` env variable.
        :param use_ssl: Whether to use SSL for the connection. Defaults to
            ``{env_prefix}_USE_SSL`` > ``S3_USE_SSL`` env variable. Ignored by boto3
            if the endpoint URL already contains an http/https scheme.
        :param region: AWS region name. Defaults to
            ``{env_prefix}_REGION`` > ``S3_REGION`` env variable.
        :param multipart_threshold: Object size in bytes above which a multipart copy is
            used instead of a single ``copy_object`` call. Must not exceed the AWS hard
            limit of 5 GiB; if a larger value is supplied it is clamped to that limit and
            a warning is logged. Defaults to ``5 GiB``.
        :param multipart_chunksize: Size in bytes of each part when performing a multipart
            copy. Must be at least 5 MiB (AWS minimum). Larger values reduce the number of
            API calls at the cost of higher per-request memory usage. Defaults to ``256 MiB``.
        """
        self.logger = create_logger()

        self.env_prefix = env_prefix
        self.profile = profile or ce("AWS_PROFILE", None)

        self._access_key = access_key or (
            (ce(f"{env_prefix}_ACCESS_KEY", S3.DEFAULT_ACCESS_KEY) if env_prefix else S3.DEFAULT_ACCESS_KEY)
            if not self.profile
            else None
        )
        self._secret_key = secret_key or (
            (ce(f"{env_prefix}_SECRET_KEY", S3.DEFAULT_SECRET_KEY) if env_prefix else S3.DEFAULT_SECRET_KEY)
            if not self.profile
            else None
        )
        _default_ssl = boolify(S3.DEFAULT_USE_SSL) if (S3.DEFAULT_USE_SSL is not None) else None

        self.use_ssl = (
            use_ssl
            if use_ssl is not None
            else (
                (ce(f"{env_prefix}_USE_SSL", _default_ssl) if env_prefix else _default_ssl)
                if not self.profile
                else None
            )
        )
        if self.use_ssl is not None:
            self.use_ssl = boolify(self.use_ssl)

        self.endpoint = endpoint or (
            (ce(f"{env_prefix}_ENDPOINT", S3.DEFAULT_ENDPOINT) if env_prefix else S3.DEFAULT_ENDPOINT)
            if not self.profile
            else None
        )
        if self.endpoint is not None:
            if self.endpoint.startswith("s3://"):
                self.endpoint = self.endpoint[len("s3://") :]

            if not any(self.endpoint.startswith(x) for x in ["https://", "http://"]):
                scheme = "https://"
                if self.use_ssl is not None:
                    scheme = "https://" if self.use_ssl else "http://"
                self.endpoint = scheme + self.endpoint

        self.region = region or (
            (ce(f"{env_prefix}_REGION", S3.DEFAULT_REGION) if env_prefix else S3.DEFAULT_REGION)
            if not self.profile
            else None
        )
        multipart_threshold = multipart_threshold or (
            ce(f"{env_prefix}_MULTIPART_THRESHOLD", S3.DEFAULT_MULTIPART_THRESHOLD)
            if env_prefix
            else S3.DEFAULT_MULTIPART_THRESHOLD
        )
        if multipart_threshold and multipart_threshold > S3.MAXIMUM_MULTIPART_THRESHOLD:
            self.logger.warning(
                (
                    f"Provided multipart_threshold {naturalsize(multipart_threshold)} over maximum threshold "
                    f"enforced by S3 protocol {naturalsize(S3.MAXIMUM_MULTIPART_THRESHOLD)}"
                )
            )
            multipart_threshold = None
        self.multipart_threshold = multipart_threshold or S3.MAXIMUM_MULTIPART_THRESHOLD

        multipart_chunksize = multipart_chunksize or (
            ce(f"{env_prefix}_MULTIPART_CHUNKSIZE", S3.DEFAULT_MULTIPART_CHUNKSIZE)
            if env_prefix
            else S3.DEFAULT_MULTIPART_CHUNKSIZE
        )
        if multipart_chunksize and multipart_chunksize < S3.MINIMUM_MULTIPART_CHUNKSIZE:
            self.logger.warning(
                (
                    f"Provided multipart_chunksize {naturalsize(multipart_chunksize)} "
                    f"under maximum size of {naturalsize(S3.MINIMUM_MULTIPART_CHUNKSIZE)}"
                )
            )
            multipart_chunksize = None
        self.multipart_chunksize = multipart_chunksize or S3.MINIMUM_MULTIPART_CHUNKSIZE

        _default_use_threads = boolify(S3.DEFAULT_USE_THREADS) if (S3.DEFAULT_USE_THREADS is not None) else None
        self.use_threads = (
            use_threads
            if use_threads is not None
            else (ce(f"{env_prefix}_USE_THREADS", _default_use_threads) if env_prefix else _default_use_threads)
        )
        if self.use_threads is not None:
            self.use_threads = boolify(self.use_threads)

        self.max_concurrency = max_concurrency or (
            ce(f"{env_prefix}_MAX_CONCURRENCY", S3.DEFAULT_MAX_CONCURRENCY)
            if env_prefix
            else S3.DEFAULT_MAX_CONCURRENCY
        )

        self.transfer_config = TransferConfig(
            multipart_threshold=self.multipart_threshold,
            multipart_chunksize=self.multipart_chunksize,
            use_threads=self.use_threads,
            max_concurrency=self.max_concurrency,
        )

        self.client = self.get_client()

        self.logger.debug("--- S3 Configuration ---")
        self.logger.debug(f"Endpoint:   {self.endpoint}")
        self.logger.debug(f"Access Key: {self._access_key}")
        self.logger.debug(f"Secret Key: {('*' * len(self._secret_key)) if self._secret_key else None}")
        self.logger.debug(f"Use SSL:    {self.use_ssl}")
        self.logger.debug(f"Region:     {self.region}")
        self.logger.debug(f"Multipart threshold: {naturalsize(self.multipart_threshold)}")
        self.logger.debug(f"Multipart chunksize: {naturalsize(self.multipart_chunksize)}")
        self.logger.debug(f"Use threads: {self.use_threads}")
        self.logger.debug(f"Max concurrency: {self.max_concurrency}")
        self.logger.debug("-------------------------")

    def get_client(self):
        """
        Create and return a boto3 S3 client instance.

        Builds the client using the endpoint, credentials, SSL preference, and region
        set during initialisation.

        :returns: A configured boto3 S3 client.
        :rtype: botocore.client.S3
        """
        if self.profile:
            session = boto3.Session(profile_name=self.profile)
            # only pull in the non-null values to pass up to the boto3 client
            params = {
                k: v
                for k, v in dict(
                    endpoint_url=self.endpoint,
                    aws_access_key_id=self._access_key,
                    aws_secret_access_key=self._secret_key,
                    use_ssl=self.use_ssl,
                    region_name=self.region,
                ).items()
                if v is not None
            }

            return session.client("s3", **params)
        else:
            return boto3.client(
                "s3",
                endpoint_url=self.endpoint,
                aws_access_key_id=self._access_key,
                aws_secret_access_key=self._secret_key,
                use_ssl=self.use_ssl,
                region_name=self.region,
            )

    def confirm_client(self):
        """
        Confirm S3 Client can connect

        Attempts to list buckets, fails if any error.
        """
        try:
            self.client.list_buckets()
            return True
        except Exception as e:
            self.logger.warning(f"List buckets failed with {e}")
            return False

    def object_exists(self, bucket_name: str, object_name: str, *, check_dir: bool = False) -> bool:
        """
        Check whether an object exists in a bucket.

        Performs a HEAD request against the given key. If the key is not found and
        ``check_dir`` is ``True``, falls back to :meth:`directory_exists` to handle
        the case where the key represents a virtual directory prefix.

        :param bucket_name: Name of the S3 bucket to check.
        :param object_name: Key of the object to look up.
        :param check_dir: When ``True`` and the object is not found, also checks
            whether the key exists as a directory prefix. Defaults to ``False``.
        :returns: ``True`` if the object (or directory, when ``check_dir=True``) exists,
            ``False`` otherwise.
        :rtype: bool
        :raises botocore.exceptions.ClientError: Re-raised for any error other than a 404.
        """
        try:
            response = self.client.head_object(Bucket=bucket_name, Key=object_name)
            # Return False if object is a directory marker, unless check_dir = True
            if not check_dir and response.get("ContentType") == "application/x-directory":
                return False
            return True
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "404":
                if check_dir:
                    return self.directory_exists(bucket_name, object_name)
                else:
                    return False
            raise

    def directory_exists(self, bucket_name: str, prefix: str) -> bool:
        """
        Check whether a virtual directory (prefix) exists in a bucket.

        Issues a ``list_objects_v2`` call limited to one key under the given prefix.
        A trailing slash is appended to the prefix if not already present, matching
        the S3 convention for directory-like prefixes.

        :param bucket_name: Name of the S3 bucket to check.
        :param prefix: The directory prefix to check for. A trailing ``/`` is added
            automatically if absent.
        :returns: ``True`` if at least one object exists under the prefix,
            ``False`` otherwise.
        :rtype: bool
        """
        if not prefix.endswith("/"):
            prefix += "/"
        resp = self.client.list_objects_v2(Bucket=bucket_name, Prefix=prefix, MaxKeys=1)
        return "Contents" in resp

    def copy_with_tags(self, *, src_bucket: str, src_key: str, dst_bucket: str, dst_key: str):
        """
        Copy an S3 object to a new location, preserving its metadata and tags.

        Delegates multipart/single-part decisions to boto3's managed transfer via
        :attr:`transfer_config`. Tags are fetched before the copy and re-applied
        afterwards via ``put_object_tagging``, since the managed transfer has no
        ``TaggingDirective`` equivalent.

        :param src_bucket: Name of the source bucket.
        :param src_key: Key of the source object.
        :param dst_bucket: Name of the destination bucket.
        :param dst_key: Key for the destination object.
        :raises botocore.exceptions.ClientError: On any underlying S3 API error.
        """
        # Fetch tags before the copy so we can re-apply them afterwards.
        tag_resp = self.client.get_object_tagging(Bucket=src_bucket, Key=src_key)
        tag_set = tag_resp.get("TagSet", [])

        self.client.copy(
            CopySource={"Bucket": src_bucket, "Key": src_key},
            Bucket=dst_bucket,
            Key=dst_key,
            Config=self.transfer_config,
        )

        if tag_set:
            self.client.put_object_tagging(
                Bucket=dst_bucket,
                Key=dst_key,
                Tagging={"TagSet": tag_set},
            )

    def move_object(self, src_bucket: str, src_key: str, dst_bucket: str, dst_key: str):
        """
        Move an object from one location to another by copying then deleting the source.

        Delegates the copy to :meth:`copy_with_tags`, which handles both small and large
        objects and validates integrity before returning. The source object is only deleted
        if the copy completes without raising an exception.

        :param src_bucket: Name of the source bucket.
        :param src_key: Key of the object to move.
        :param dst_bucket: Name of the destination bucket.
        :param dst_key: Key for the object at the destination.
        :raises ValueError: If integrity validation fails during the copy step.
        :raises botocore.exceptions.ClientError: On any underlying S3 API error.
        """
        self.copy_with_tags(
            src_bucket=src_bucket,
            src_key=src_key,
            dst_bucket=dst_bucket,
            dst_key=dst_key,
        )
        # copy_with_tags will raise error if copy is not validated.
        # Safe to proceed with delete if we make it here.
        self.client.delete_object(Bucket=src_bucket, Key=src_key)

    def get_matching_objects(
        self,
        bucket: str,
        prefix: Optional[str] = None,
        pattern: Optional[str] = None,
    ) -> list[S3Object]:
        """
        List all objects under a prefix whose filenames match a glob pattern.

        Pages through the entire bucket prefix using ``list_objects_v2`` and filters
        results client-side with :func:`fnmatch.fnmatch`. Only the filename portion of
        each key (i.e. the last path segment) is tested against the pattern.

        :param bucket: Name of the S3 bucket to query.
        :param prefix: Optional key prefix to restrict the listing. A trailing ``/`` is
            appended automatically. If ``None``, the entire bucket is listed.
        :param pattern: Optional glob pattern (e.g. ``"*.parquet"``) applied to the
            filename (last segment) of each key. If ``None``, all objects under the prefix
            are returned.
        :returns: A list of :class:`S3Object` dicts for every matching object.
        :rtype: list[S3Object]

        Example:
        -------
        .. code-block:: python

            objects = s3.get_matching_objects(
                bucket="my-bucket",
                prefix="data/2024/",
                pattern="*.csv",
            )

        """
        _prefix = f"{prefix.rstrip('/')}/" if prefix else ""
        _pattern = pattern or "*"
        full_pattern = f"{_prefix}{_pattern}"
        paginator = self.client.get_paginator("list_objects_v2")
        obj_ls = []
        for page in paginator.paginate(Bucket=bucket, **({"Prefix": _prefix} if prefix else {})):
            for obj in page.get("Contents", []):
                filename = obj["Key"]
                if fnmatch.fnmatch(filename, full_pattern):
                    obj_ls.append(obj)
        return obj_ls

    def get_object_stream(self, bucket: str, key: str) -> StreamingBody:
        """
        Return the raw :class:`~botocore.response.StreamingBody` for an object.

        The response body is **not** buffered into memory; the caller is responsible
        for reading and closing the stream. Prefer this method over
        :meth:`get_object_bytes` when dealing with large objects where loading the
        entire payload at once is undesirable.

        :param bucket: Name of the S3 bucket containing the object.
        :param key: Key of the object to stream.
        :returns: An open :class:`~botocore.response.StreamingBody` that the caller
            must close (or use as a context manager) after reading.
        :rtype: botocore.response.StreamingBody
        :raises botocore.exceptions.ClientError: On any underlying S3 API error.
        """
        response = self.client.get_object(Bucket=bucket, Key=key)
        return response["Body"]

    def get_object_range(self, bucket: str, key: str, start: int, end: int | None = None) -> bytes:
        """
        Read a byte range from an object and return it as :class:`bytes`.

        Uses the HTTP ``Range`` header supported by the S3 protocol. The range is
        **inclusive** on both ends, matching the HTTP Range specification
        (``bytes=start-end``). This is useful for partial reads of large objects
        such as columnar file formats (Parquet, ORC) that embed footer metadata at
        a known offset.

        :param bucket: Name of the S3 bucket containing the object.
        :param key: Key of the object to read.
        :param start: Zero-based byte offset at which to begin reading.
        :param end: Inclusive byte offset at which to stop reading. If ``None``,
            reads from ``start`` through the end of the object.
        :returns: The raw bytes for the requested range.
        :rtype: bytes
        :raises botocore.exceptions.ClientError: On any underlying S3 API error.
        """
        range_header = f"bytes={start}-" if end is None else f"bytes={start}-{end}"
        response = self.client.get_object(Bucket=bucket, Key=key, Range=range_header)
        return response["Body"].read()

    def get_object_bytes(self, bucket: str, key: str, **kwargs) -> bytes:
        """
        Download an object and return its contents as :class:`bytes`.

        Uses boto3's ``download_fileobj`` under the hood with :attr:`transfer_config`
        applied by default, enabling multipart downloads and concurrency for large
        objects. Any additional keyword arguments are forwarded directly to
        ``download_fileobj`` and can be used to pass extra parameters such as
        ``ExtraArgs`` or a custom ``Callback``.

        See the boto3 docs for the full list of accepted parameters:
        https://docs.aws.amazon.com/boto3/latest/reference/services/s3/client/download_fileobj.html

        :param bucket: Name of the S3 bucket containing the object.
        :param key: Key of the object to download.
        :param kwargs: Additional keyword arguments forwarded to ``download_fileobj``.
            A caller-supplied ``Config`` will override the default
            :attr:`transfer_config`.
        :returns: The complete object content as a :class:`bytes` object.
        :rtype: bytes
        :raises botocore.exceptions.ClientError: On any underlying S3 API error.
        """
        buffer = io.BytesIO()
        kwargs = {"Config": self.transfer_config} | kwargs
        self.client.download_fileobj(Bucket=bucket, Key=key, Fileobj=buffer, **kwargs)
        buffer.seek(0)
        return buffer.read()

    def get_object_text(self, bucket: str, key: str, encoding: str = "utf-8", **kwargs) -> str:
        """
        Download an object and return its contents as a decoded :class:`str`.

        Delegates the download to :meth:`get_object_bytes` and decodes the resulting
        bytes using the specified character encoding. Any additional keyword arguments
        are forwarded to :meth:`get_object_bytes` (and ultimately to boto3's
        ``download_fileobj``).

        See the boto3 docs for the full list of accepted parameters:
        https://docs.aws.amazon.com/boto3/latest/reference/services/s3/client/download_fileobj.html

        :param bucket: Name of the S3 bucket containing the object.
        :param key: Key of the object to download.
        :param encoding: Character encoding used to decode the raw bytes.
            Defaults to ``'utf-8'``.
        :param kwargs: Additional keyword arguments forwarded to
            :meth:`get_object_bytes`.
        :returns: The object content decoded as a :class:`str`.
        :rtype: str
        :raises UnicodeDecodeError: If the object bytes cannot be decoded with
            the given encoding.
        :raises botocore.exceptions.ClientError: On any underlying S3 API error.
        """
        content = self.get_object_bytes(bucket=bucket, key=key, **kwargs)
        return content.decode(encoding)

    def put_object_bytes(
        self, bucket: str, key: str, data: bytes, tagging: None | dict[str, str] | str = None, **kwargs
    ) -> None:
        """
        Upload raw :class:`bytes` to an S3 object.

        Uses boto3's ``upload_fileobj`` under the hood with :attr:`transfer_config`
        applied by default, enabling multipart uploads and concurrency for large
        payloads. Object tags can be supplied either as a pre-encoded query string or
        as a plain :class:`dict`; the dict form is URL-encoded automatically. Also checks for
        an ``ExtraArgs`` key inside ``kwargs`` and will apply the same process to a ``Tagging``
        key inside that ``ExtraArgs``.

        See the boto3 docs for the full list of accepted parameters:
        https://docs.aws.amazon.com/boto3/latest/reference/services/s3/client/upload_fileobj.html

        :param bucket: Name of the destination S3 bucket.
        :param key: Key under which the object will be stored.
        :param data: Raw bytes to upload.
        :param tagging: Optional object tags. Accepts a URL-encoded tag string
            (e.g. ``"key1=val1&key2=val2"``), a :class:`dict` of tag key/value pairs
            that will be encoded automatically, or ``None`` for no tags.
            If ``None`` and a ``Tagging`` key is present in ``kwargs``, that value is
            used instead.
        :param kwargs: Additional keyword arguments forwarded to ``upload_fileobj``.
            A caller-supplied ``Config`` will override the default
            :attr:`transfer_config`.
        :raises botocore.exceptions.ClientError: On any underlying S3 API error.
        """
        buffer = io.BytesIO(data)

        kwargs = {"Config": self.transfer_config} | kwargs
        if "ExtraArgs" in kwargs:
            extra_args = kwargs.pop("ExtraArgs")
        else:
            extra_args = {}

        if tagging is None and "Tagging" in extra_args:
            tagging = extra_args.pop("Tagging")

        if isinstance(tagging, dict):
            tagging = urlencode(tagging)
        if tagging:
            extra_args.update({"Tagging": tagging})
        kwargs["ExtraArgs"] = extra_args
        self.client.upload_fileobj(Fileobj=buffer, Bucket=bucket, Key=key, **kwargs)

    def put_object_text(
        self,
        bucket: str,
        key: str,
        text: str,
        encoding: str = "utf-8",
        tagging: None | dict[str, str] | str = None,
        **kwargs,
    ) -> None:
        """
        Encode a :class:`str` and upload it to an S3 object.

        Encodes ``text`` using the specified character encoding and delegates the
        upload to :meth:`put_object_bytes`. Tag handling and additional keyword
        arguments behave identically to that method.

        See the boto3 docs for the full list of accepted parameters:
        https://docs.aws.amazon.com/boto3/latest/reference/services/s3/client/upload_fileobj.html

        :param bucket: Name of the destination S3 bucket.
        :param key: Key under which the object will be stored.
        :param text: String content to encode and upload.
        :param encoding: Character encoding used to convert ``text`` to bytes.
            Defaults to ``'utf-8'``.
        :param tagging: Optional object tags. Accepts a URL-encoded tag string,
            a :class:`dict` of tag key/value pairs, or ``None``. See
            :meth:`put_object_bytes` for full details.
        :param kwargs: Additional keyword arguments forwarded to
            :meth:`put_object_bytes`.
        :raises UnicodeEncodeError: If ``text`` cannot be encoded with the given
            encoding.
        :raises botocore.exceptions.ClientError: On any underlying S3 API error.
        """
        self.put_object_bytes(bucket=bucket, key=key, data=text.encode(encoding), tagging=tagging, **kwargs)
