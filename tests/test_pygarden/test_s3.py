"""
Pytest tests for pygarden/s3.py using moto for realistic AWS mocking.

pygarden is a real package so we must NOT stub it wholesale. We only stub the
one submodule whose side-effects we cannot allow in tests:
  - pygarden.logz (create_logger called in __init__ – avoids real log setup)

pygarden.env is left real. check_environment() simply reads os.environ, so
tests that care about env-var resolution set values via monkeypatch.setenv and
let the real ce() run.
"""

import sys
import os
import math
from textwrap import dedent
from unittest.mock import MagicMock, patch, call

import pytest
from moto import mock_aws
from botocore.exceptions import ClientError

# ---------------------------------------------------------------------------
# Stub only pygarden.logz – create_logger has real side-effects we don't want.
# pygarden.env is intentionally left real so ce() reads os.environ normally.
# ---------------------------------------------------------------------------
sys.modules["pygarden.logz"] = MagicMock(create_logger=MagicMock(return_value=MagicMock()))

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REGION = "us-east-1"
SRC_BUCKET = "src-bucket"
DST_BUCKET = "dst-bucket"
SMALL_THRESHOLD = 5 * 1024**2      # 5 MiB – just at the multipart threshold
SMALL_PART_SIZE = 5 * 1024**2      # 5 MiB – AWS/moto minimum part size
DEFAULT_ENDPOINT = "http://testing:1000"
os.environ.setdefault("S3_ENDPOINT", DEFAULT_ENDPOINT)
os.environ.setdefault("S3_ACCESS_KEY", "testing")
os.environ.setdefault("S3_SECRET_KEY", "testing")
os.environ.setdefault("S3_REGION", REGION)

from pygarden.s3 import S3  # noqa: E402  (must follow sys.modules patching)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _client_error(code: str) -> ClientError:
    return ClientError({"Error": {"Code": code, "Message": "test"}}, "op")


def _make_s3_instance(**kwargs) -> S3:
    """
    Build an S3 instance using the real get_client() path.

    Must be called inside an active mock_aws() context so that the boto3 client
    created by get_client() is backed by moto. create_logger is already stubbed
    via the sys.modules patch at module level, so no additional patching is needed.
    """
    return S3(**kwargs)


def _put_object(client, bucket: str, key: str, body: bytes = b"hello",
                metadata: dict | None = None, tags: str = "") -> None:
    kwargs: dict = dict(Bucket=bucket, Key=key, Body=body)
    if metadata:
        kwargs["Metadata"] = metadata
    if tags:
        kwargs["Tagging"] = tags
    client.put_object(**kwargs)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def aws_env(monkeypatch):
    monkeypatch.setattr(S3, "DEFAULT_ENDPOINT", None)

@pytest.fixture
def s3(aws_env):
    """S3 instance with both test buckets created, inside a moto context."""
    with mock_aws():
        inst = _make_s3_instance()
        inst.client.create_bucket(Bucket=SRC_BUCKET)
        inst.client.create_bucket(Bucket=DST_BUCKET)
        yield inst


@pytest.fixture
def s3_small_threshold(aws_env):
    """S3 instance with a tiny multipart threshold for easier large-copy testing."""
    with mock_aws():
        inst = _make_s3_instance(
            multipart_threshold=SMALL_THRESHOLD,
            multipart_chunksize=SMALL_PART_SIZE,
        )
        inst.client.create_bucket(Bucket=SRC_BUCKET)
        inst.client.create_bucket(Bucket=DST_BUCKET)
        yield inst

# ===========================================================================
# __init__ – configuration / clamping
# ===========================================================================

class TestInit:
    def test_multipart_threshold_over_max_is_clamped(self):
        over = S3.DEFAULT_MULTIPART_THRESHOLD + 1
        with mock_aws():
            inst = _make_s3_instance(multipart_threshold=over)
        assert inst.multipart_threshold == S3.DEFAULT_MULTIPART_THRESHOLD

    def test_multipart_threshold_over_max_logs_warning(self):
        mock_logger = MagicMock()
        over = S3.DEFAULT_MULTIPART_THRESHOLD + 1
        with mock_aws(), patch("pygarden.s3.create_logger", return_value=mock_logger):
            _make_s3_instance(multipart_threshold=over)
        mock_logger.warning.assert_called_once()

    def test_multipart_chunksize_under_min_is_clamped(self):
        under = S3.MINIMUM_MULTIPART_CHUNKSIZE - 1
        with mock_aws():
            inst = _make_s3_instance(multipart_chunksize=under)
        assert inst.multipart_chunksize == S3.MINIMUM_MULTIPART_CHUNKSIZE

    def test_multipart_chunksize_under_min_logs_warning(self):
        mock_logger = MagicMock()
        under = S3.MINIMUM_MULTIPART_CHUNKSIZE - 1
        with mock_aws(), patch("pygarden.s3.create_logger", return_value=mock_logger):
            _make_s3_instance(multipart_chunksize=under)
        mock_logger.warning.assert_called_once()

    def test_valid_custom_values_stored(self):
        threshold = 2 * 1024 ** 3
        part_size = 64 * 1024 ** 2
        with mock_aws():
            inst = _make_s3_instance(multipart_threshold=threshold, multipart_chunksize=part_size)
        assert inst.multipart_threshold == threshold
        assert inst.multipart_chunksize == part_size

    def test_defaults_applied_when_no_args_given(self):
        with mock_aws():
            inst = _make_s3_instance()
        assert inst.multipart_threshold == S3.DEFAULT_MULTIPART_THRESHOLD
        assert inst.multipart_chunksize == S3.DEFAULT_MULTIPART_CHUNKSIZE

    def test_get_client_uses_correct_credential_kwarg_names(self):
        """get_client() must pass the correct boto3 kwarg names so credentials are honoured."""
        with patch("pygarden.s3.boto3.client", return_value=MagicMock()) as mock_boto:
            S3(endpoint="http://localhost:9000", access_key="mykey",
               secret_key="mysecret", region="us-west-2")
        _, kwargs = mock_boto.call_args
        assert kwargs["aws_access_key_id"] == "mykey"
        assert kwargs["aws_secret_access_key"] == "mysecret"
        assert kwargs["endpoint_url"] == "http://localhost:9000"
        assert kwargs["region_name"] == "us-west-2"

    def test_profile_loads_credentials_and_region_from_aws_files(self, monkeypatch, tmp_path):
        credentials_file = tmp_path / "credentials"
        credentials_file.write_text(
            dedent(
                """
                [default]
                aws_access_key_id = default-key
                aws_secret_access_key = default-secret

                [test-profile]
                aws_access_key_id = profile-key
                aws_secret_access_key = profile-secret
                aws_session_token = profile-token
                """
            ).strip()
        )

        config_file = tmp_path / "config"
        config_file.write_text(
            dedent(
                """
                [default]
                region = us-west-1

                [profile test-profile]
                region = eu-central-1
                """
            ).strip()
        )

        monkeypatch.setenv("AWS_SHARED_CREDENTIALS_FILE", str(credentials_file))
        monkeypatch.setenv("AWS_CONFIG_FILE", str(config_file))
        monkeypatch.setenv("AWS_EC2_METADATA_DISABLED", "true")
        monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
        monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)
        monkeypatch.delenv("AWS_SESSION_TOKEN", raising=False)
        monkeypatch.delenv("AWS_PROFILE", raising=False)
        monkeypatch.delenv("AWS_DEFAULT_PROFILE", raising=False)

        inst = S3(profile="test-profile")

        frozen_creds = inst.client._request_signer._credentials.get_frozen_credentials()
        assert frozen_creds.access_key == "profile-key"
        assert frozen_creds.secret_key == "profile-secret"
        assert frozen_creds.token == "profile-token"
        assert inst.client.meta.region_name == "eu-central-1"


# ===========================================================================
# __init__ – environment variable resolution
# ===========================================================================

class TestEnvVarResolution:
    """
    Verify the three-tier priority chain for every config field:
        explicit argument  >  {env_prefix}_* env var  >  DEFAULT_* class attribute

    pygarden.env is the real module, so monkeypatch.setenv is all that's needed —
    ce() reads os.environ directly. Tests run inside mock_aws() so get_client()
    produces a real (moto-backed) client without any boto3 patching.

    The kwarg-name plumbing (that stored values actually reach boto3.client()) is
    covered once by test_get_client_uses_correct_credential_kwarg_names above;
    these tests only need to assert the stored instance attributes.
    """

    # --- env_prefix storage -------------------------------------------------

    def test_env_prefix_stored_on_instance(self):
        with mock_aws():
            inst = _make_s3_instance(env_prefix="MYSTORE")
        assert inst.env_prefix == "MYSTORE"

    def test_no_env_prefix_stored_as_none(self):
        with mock_aws():
            inst = _make_s3_instance()
        assert inst.env_prefix is None

    # --- endpoint -----------------------------------------------------------

    def test_explicit_endpoint_wins_over_env_prefix(self, monkeypatch):
        monkeypatch.setenv("MYNS_ENDPOINT", "http://from-env")
        with mock_aws():
            inst = _make_s3_instance(env_prefix="MYNS", endpoint="http://explicit")
        assert inst.endpoint == "http://explicit"

    def test_env_prefix_endpoint_used_when_no_explicit(self, monkeypatch):
        monkeypatch.setenv("MYNS_ENDPOINT", "http://prefixed-endpoint")
        with mock_aws():
            inst = _make_s3_instance(env_prefix="MYNS")
        assert inst.endpoint == "http://prefixed-endpoint"

    def test_endpoint_falls_back_to_class_default_when_prefix_var_absent(self):
        with mock_aws():
            inst = _make_s3_instance(env_prefix="MYNS")
        assert inst.endpoint == DEFAULT_ENDPOINT

    def test_no_env_prefix_and_no_explicit_uses_class_default(self):
        with mock_aws():
            inst = _make_s3_instance()
        assert inst.endpoint == DEFAULT_ENDPOINT

    # --- access_key ---------------------------------------------------------

    def test_explicit_access_key_wins_over_env_prefix(self, monkeypatch):
        monkeypatch.setenv("MYNS_ACCESS_KEY", "env-access-key")
        with mock_aws():
            inst = _make_s3_instance(env_prefix="MYNS", access_key="explicit-key")
        assert inst._access_key == "explicit-key"

    def test_env_prefix_access_key_used_when_no_explicit(self, monkeypatch):
        monkeypatch.setenv("MYNS_ACCESS_KEY", "prefixed-access-key")
        with mock_aws():
            inst = _make_s3_instance(env_prefix="MYNS", access_key=None)
        assert inst._access_key == "prefixed-access-key"

    def test_access_key_falls_back_to_class_default_when_prefix_var_absent(self):
        with mock_aws():
            inst = _make_s3_instance(env_prefix="MYNS", access_key=None)
        assert inst._access_key == S3.DEFAULT_ACCESS_KEY

    # --- secret_key ---------------------------------------------------------

    def test_explicit_secret_key_wins_over_env_prefix(self, monkeypatch):
        monkeypatch.setenv("MYNS_SECRET_KEY", "env-secret")
        with mock_aws():
            inst = _make_s3_instance(env_prefix="MYNS", secret_key="explicit-secret")
        assert inst._secret_key == "explicit-secret"

    def test_env_prefix_secret_key_used_when_no_explicit(self, monkeypatch):
        monkeypatch.setenv("MYNS_SECRET_KEY", "prefixed-secret")
        with mock_aws():
            inst = _make_s3_instance(env_prefix="MYNS", secret_key=None)
        assert inst._secret_key == "prefixed-secret"

    # --- region -------------------------------------------------------------

    def test_explicit_region_wins_over_env_prefix(self, monkeypatch):
        monkeypatch.setenv("MYNS_REGION", "eu-west-1")
        with mock_aws():
            inst = _make_s3_instance(env_prefix="MYNS", region="ap-southeast-1")
        assert inst.region == "ap-southeast-1"

    def test_env_prefix_region_used_when_no_explicit(self, monkeypatch):
        monkeypatch.setenv("MYNS_REGION", "eu-west-1")
        with mock_aws():
            inst = _make_s3_instance(env_prefix="MYNS", region=None)
        assert inst.region == "eu-west-1"

    def test_region_falls_back_to_class_default_when_prefix_var_absent(self):
        with mock_aws():
            inst = _make_s3_instance(env_prefix="MYNS", region=None)
        assert inst.region == S3.DEFAULT_REGION

    # --- use_ssl ------------------------------------------------------------

    def test_explicit_use_ssl_wins_over_env_prefix(self, monkeypatch):
        monkeypatch.setenv("MYNS_USE_SSL", "false")
        with mock_aws():
            inst = _make_s3_instance(env_prefix="MYNS", use_ssl=True)
        assert inst.use_ssl is True

    def test_env_prefix_use_ssl_used_when_no_explicit(self, monkeypatch):
        monkeypatch.setenv("MYNS_USE_SSL", "true")
        with mock_aws():
            inst = _make_s3_instance(env_prefix="MYNS", use_ssl=None)
        assert inst.use_ssl is True

    # --- partial prefix (some vars set, others absent) ----------------------

    def test_partial_prefix_mixes_prefixed_and_default_per_field(self, monkeypatch):
        """When only some prefixed vars exist, each field falls back independently."""
        monkeypatch.setenv("MYNS_ENDPOINT", "http://partial-endpoint")
        monkeypatch.setenv("MYNS_REGION", "ca-central-1")
        with mock_aws():
            inst = _make_s3_instance(env_prefix="MYNS")
        assert inst.endpoint == "http://partial-endpoint"
        assert inst.region == "ca-central-1"
        assert inst._access_key == "testing"  # _make_s3_instance default, no prefixed var set

    # --- ce() call verification ---------------------------------------------

    def test_ce_called_with_prefixed_keys_for_all_fields(self):
        """When env_prefix is set, ce() must be called with every prefixed key name."""
        with mock_aws(), patch("pygarden.s3.ce", return_value=None) as mock_ce:
            _make_s3_instance(env_prefix="NS")

        called_keys = [c.args[0] for c in mock_ce.call_args_list]
        assert "NS_ENDPOINT" in called_keys
        assert "NS_ACCESS_KEY" in called_keys
        assert "NS_SECRET_KEY" in called_keys
        assert "NS_USE_SSL" in called_keys
        assert "NS_REGION" in called_keys

    def test_ce_not_called_for_env_fields_when_all_explicit(self):
        """When every field is supplied explicitly, ce() must not be consulted for those fields."""
        with mock_aws(), patch("pygarden.s3.ce", return_value=None) as mock_ce:
            _make_s3_instance(endpoint="http://e", access_key="ak", secret_key="sk",
                              use_ssl=False, region="us-east-1")

        called_keys = [c.args[0] for c in mock_ce.call_args_list]
        for field in ("_ENDPOINT", "_ACCESS_KEY", "_SECRET_KEY", "_USE_SSL", "_REGION"):
            assert not any(k.endswith(field) for k in called_keys), (
                f"ce() was unexpectedly called for {field}"
            )


# ===========================================================================
# object_exists
# ===========================================================================

class TestObjectExists:
    def test_returns_true_for_existing_object(self, s3):
        _put_object(s3.client, SRC_BUCKET, "file.txt")
        assert s3.object_exists(SRC_BUCKET, "file.txt") is True

    def test_returns_false_for_missing_object(self, s3):
        assert s3.object_exists(SRC_BUCKET, "ghost.txt") is False

    def test_check_dir_true_finds_virtual_directory(self, s3):
        _put_object(s3.client, SRC_BUCKET, "data/2024/report.csv")
        # The prefix itself ("data/2024") is not an object, but check_dir falls back
        assert s3.object_exists(SRC_BUCKET, "data/2024", check_dir=True) is True

    def test_check_dir_false_does_not_find_virtual_directory(self, s3):
        _put_object(s3.client, SRC_BUCKET, "data/2024/report.csv")
        assert s3.object_exists(SRC_BUCKET, "data/2024", check_dir=False) is False

    def test_reraises_non_404_errors(self, s3):
        """Querying a non-existent bucket should raise ClientError, not return False."""
        with pytest.raises(ClientError):
            s3.object_exists("bucket-that-does-not-exist", "key.txt")


# ===========================================================================
# directory_exists
# ===========================================================================

class TestDirectoryExists:
    def test_returns_true_when_objects_exist_under_prefix(self, s3):
        _put_object(s3.client, SRC_BUCKET, "logs/2024/app.log")
        assert s3.directory_exists(SRC_BUCKET, "logs/2024") is True

    def test_returns_false_when_prefix_is_empty(self, s3):
        assert s3.directory_exists(SRC_BUCKET, "nonexistent/prefix") is False

    def test_trailing_slash_normalised(self, s3):
        _put_object(s3.client, SRC_BUCKET, "reports/q1.pdf")
        assert s3.directory_exists(SRC_BUCKET, "reports") is True
        assert s3.directory_exists(SRC_BUCKET, "reports/") is True

    def test_partial_prefix_not_matched(self, s3):
        # "rep" should not match objects under "reports/"
        _put_object(s3.client, SRC_BUCKET, "reports/q1.pdf")
        assert s3.directory_exists(SRC_BUCKET, "rep") is False


# ===========================================================================
# copy_with_tags
# ===========================================================================

class TestCopyWithTags:
    def test_content_copied_correctly(self, s3):
        body = b"hello copy"
        _put_object(s3.client, SRC_BUCKET, "src.txt", body=body)
        s3.copy_with_tags(
            src_bucket=SRC_BUCKET, src_key="src.txt",
            dst_bucket=DST_BUCKET, dst_key="dst.txt",
        )
        assert s3.client.get_object(Bucket=DST_BUCKET, Key="dst.txt")["Body"].read() == body

    def test_tags_preserved(self, s3):
        _put_object(s3.client, SRC_BUCKET, "tagged.txt", tags="env=prod&team=data")
        s3.copy_with_tags(
            src_bucket=SRC_BUCKET, src_key="tagged.txt",
            dst_bucket=DST_BUCKET, dst_key="tagged-copy.txt",
        )
        tag_resp = s3.client.get_object_tagging(Bucket=DST_BUCKET, Key="tagged-copy.txt")
        tag_dict = {t["Key"]: t["Value"] for t in tag_resp["TagSet"]}
        assert tag_dict == {"env": "prod", "team": "data"}

    def test_no_tags_produces_empty_tag_set(self, s3):
        _put_object(s3.client, SRC_BUCKET, "plain.txt")
        s3.copy_with_tags(
            src_bucket=SRC_BUCKET, src_key="plain.txt",
            dst_bucket=DST_BUCKET, dst_key="plain-copy.txt",
        )
        tags = s3.client.get_object_tagging(Bucket=DST_BUCKET, Key="plain-copy.txt")
        assert tags["TagSet"] == []

    def test_metadata_preserved(self, s3):
        _put_object(s3.client, SRC_BUCKET, "meta.txt", metadata={"author": "tester"})
        s3.copy_with_tags(
            src_bucket=SRC_BUCKET, src_key="meta.txt",
            dst_bucket=DST_BUCKET, dst_key="meta-copy.txt",
        )
        dst_head = s3.client.head_object(Bucket=DST_BUCKET, Key="meta-copy.txt")
        assert dst_head["Metadata"] == {"author": "tester"}

    def test_source_object_unchanged_after_copy(self, s3):
        body = b"do not touch"
        _put_object(s3.client, SRC_BUCKET, "src.txt", body=body)
        s3.copy_with_tags(
            src_bucket=SRC_BUCKET, src_key="src.txt",
            dst_bucket=DST_BUCKET, dst_key="dst.txt",
        )
        assert s3.client.get_object(Bucket=SRC_BUCKET, Key="src.txt")["Body"].read() == body

    def test_cross_bucket_copy(self, s3):
        body = b"cross"
        _put_object(s3.client, SRC_BUCKET, "a.txt", body=body)
        s3.copy_with_tags(
            src_bucket=SRC_BUCKET, src_key="a.txt",
            dst_bucket=DST_BUCKET, dst_key="b.txt",
        )
        assert s3.client.get_object(Bucket=DST_BUCKET, Key="b.txt")["Body"].read() == body
        assert s3.object_exists(SRC_BUCKET, "a.txt") is True

    def test_uses_transfer_config(self, s3):
        _put_object(s3.client, SRC_BUCKET, "cfg.txt", body=b"x")
        with patch.object(s3.client, "copy", wraps=s3.client.copy) as spy:
            s3.copy_with_tags(
                src_bucket=SRC_BUCKET, src_key="cfg.txt",
                dst_bucket=DST_BUCKET, dst_key="cfg-copy.txt",
            )
        _, kwargs = spy.call_args
        assert kwargs.get("Config") is s3.transfer_config

    def test_large_object_copied_correctly(self, s3_small_threshold):
        body = b"L" * (SMALL_THRESHOLD * 3)
        _put_object(s3_small_threshold.client, SRC_BUCKET, "large.bin", body=body)
        s3_small_threshold.copy_with_tags(
            src_bucket=SRC_BUCKET, src_key="large.bin",
            dst_bucket=DST_BUCKET, dst_key="large-copy.bin",
        )
        result = s3_small_threshold.client.get_object(Bucket=DST_BUCKET, Key="large-copy.bin")["Body"].read()
        assert result == body

    def test_large_object_tags_preserved(self, s3_small_threshold):
        body = b"T" * (SMALL_THRESHOLD * 2)
        _put_object(s3_small_threshold.client, SRC_BUCKET, "tagged-large.bin", body=body, tags="stage=prod")
        s3_small_threshold.copy_with_tags(
            src_bucket=SRC_BUCKET, src_key="tagged-large.bin",
            dst_bucket=DST_BUCKET, dst_key="tagged-large-copy.bin",
        )
        tags = s3_small_threshold.client.get_object_tagging(Bucket=DST_BUCKET, Key="tagged-large-copy.bin")
        assert {t["Key"]: t["Value"] for t in tags["TagSet"]} == {"stage": "prod"}

    def test_raises_on_missing_source(self, s3):
        with pytest.raises(ClientError):
            s3.copy_with_tags(
                src_bucket=SRC_BUCKET, src_key="ghost.txt",
                dst_bucket=DST_BUCKET, dst_key="ghost-copy.txt",
            )


# ===========================================================================
# move_object
# ===========================================================================

class TestMoveObject:
    def test_object_present_at_destination(self, s3):
        body = b"move me"
        _put_object(s3.client, SRC_BUCKET, "original.txt", body=body)
        s3.move_object(SRC_BUCKET, "original.txt", DST_BUCKET, "moved.txt")

        assert s3.client.get_object(Bucket=DST_BUCKET, Key="moved.txt")["Body"].read() == body

    def test_source_deleted_after_move(self, s3):
        _put_object(s3.client, SRC_BUCKET, "original.txt")
        s3.move_object(SRC_BUCKET, "original.txt", DST_BUCKET, "moved.txt")
        assert s3.object_exists(SRC_BUCKET, "original.txt") is False

    def test_source_not_deleted_when_copy_fails(self, s3):
        _put_object(s3.client, SRC_BUCKET, "safe.txt")
        with patch.object(s3, "copy_with_tags", side_effect=ValueError("copy failed")):
            with pytest.raises(ValueError):
                s3.move_object(SRC_BUCKET, "safe.txt", DST_BUCKET, "safe-copy.txt")

        assert s3.object_exists(SRC_BUCKET, "safe.txt") is True

    def test_tags_survive_move(self, s3):
        _put_object(s3.client, SRC_BUCKET, "tagged.txt", tags="owner=alice")
        s3.move_object(SRC_BUCKET, "tagged.txt", DST_BUCKET, "tagged-moved.txt")

        tags = s3.client.get_object_tagging(Bucket=DST_BUCKET, Key="tagged-moved.txt")
        assert {t["Key"]: t["Value"] for t in tags["TagSet"]} == {"owner": "alice"}

    def test_metadata_survives_move(self, s3):
        _put_object(s3.client, SRC_BUCKET, "meta.txt", metadata={"x-custom": "yes"})
        s3.move_object(SRC_BUCKET, "meta.txt", DST_BUCKET, "meta-moved.txt")

        dst_head = s3.client.head_object(Bucket=DST_BUCKET, Key="meta-moved.txt")
        assert dst_head["Metadata"] == {"x-custom": "yes"}

    def test_cross_bucket_move(self, s3):
        body = b"cross bucket"
        _put_object(s3.client, SRC_BUCKET, "a.txt", body=body)
        s3.move_object(SRC_BUCKET, "a.txt", DST_BUCKET, "b.txt")

        assert s3.object_exists(SRC_BUCKET, "a.txt") is False
        assert s3.client.get_object(Bucket=DST_BUCKET, Key="b.txt")["Body"].read() == body


# ===========================================================================
# get_matching_objects
# ===========================================================================

class TestGetMatchingObjects:
    def _populate(self, client, keys: list[str], bucket: str = SRC_BUCKET) -> None:
        for key in keys:
            _put_object(client, bucket, key)

    def test_returns_matching_objects_with_glob_pattern(self, s3):
        self._populate(s3.client, ["data/a.csv", "data/b.parquet", "data/c.csv"])
        result = s3.get_matching_objects(SRC_BUCKET, pattern="*.csv")
        assert sorted(obj["Key"] for obj in result) == ["data/a.csv", "data/c.csv"]

    def test_returns_all_objects_when_pattern_matches_all(self, s3):
        keys = ["x.txt", "y.txt", "z.txt"]
        self._populate(s3.client, keys)
        result = s3.get_matching_objects(SRC_BUCKET, pattern="*.txt")
        assert sorted(obj["Key"] for obj in result) == sorted(keys)

    def test_returns_empty_list_when_nothing_matches(self, s3):
        self._populate(s3.client, ["file.json", "file.parquet"])
        assert s3.get_matching_objects(SRC_BUCKET, pattern="*.csv") == []

    def test_returns_empty_list_for_empty_bucket(self, s3):
        assert s3.get_matching_objects(SRC_BUCKET, pattern="*.csv") == []

    def test_result_objects_contain_expected_s3object_keys(self, s3):
        self._populate(s3.client, ["info.csv"])
        result = s3.get_matching_objects(SRC_BUCKET, pattern="*.csv")
        assert len(result) == 1
        for field in ("Key", "LastModified", "ETag", "Size", "StorageClass"):
            assert field in result[0]

    def test_aggregates_results_across_multiple_pages(self, s3):
        self._populate(s3.client, [f"file{i}.csv" for i in range(5)] + ["other.json"])
        original_get_paginator = s3.client.get_paginator

        def small_page_paginator(op):
            pager = original_get_paginator(op)
            original_paginate = pager.paginate

            def paginate_small(**kwargs):
                return original_paginate(**{**kwargs, "PaginationConfig": {"PageSize": 2}})

            pager.paginate = paginate_small
            return pager

        with patch.object(s3.client, "get_paginator", side_effect=small_page_paginator):
            result = s3.get_matching_objects(SRC_BUCKET, pattern="*.csv")

        assert len(result) == 5

    def test_pattern_none_returns_all_objects(self, s3):
        keys = ["a.csv", "b.parquet", "c.json"]
        self._populate(s3.client, keys)
        result = s3.get_matching_objects(SRC_BUCKET, pattern=None)
        assert sorted(obj["Key"] for obj in result) == sorted(keys)

    def test_prefix_and_pattern_combined_filters_correctly(self, s3):
        self._populate(s3.client, [
            "data/2024/report.csv",
            "data/2024/summary.parquet",
            "data/2023/report.csv",  # different prefix, should be excluded
        ])
        result = s3.get_matching_objects(SRC_BUCKET, prefix="data/2024", pattern="*.csv")
        assert [obj["Key"] for obj in result] == ["data/2024/report.csv"]

    def test_prefix_none_pattern_matches_across_all_prefixes(self, s3):
        self._populate(s3.client, ["a/x.csv", "b/y.csv", "c/z.json"])
        result = s3.get_matching_objects(SRC_BUCKET, prefix=None, pattern="*.csv")
        assert sorted(obj["Key"] for obj in result) == ["a/x.csv", "b/y.csv"]

    def test_prefix_and_pattern_none_returns_all_objects(self, s3):
        keys = ["a.csv", "b/c.parquet", "d/e/f.json"]
        self._populate(s3.client, keys)
        result = s3.get_matching_objects(SRC_BUCKET, prefix=None, pattern=None)
        assert sorted(obj["Key"] for obj in result) == sorted(keys)

# ===========================================================================
# confirm_client
# ===========================================================================

class TestConfirmClient:
    @pytest.fixture(autouse=True)
    def reset_mock(self, s3):
        s3.logger.warning.reset_mock()

    def test_returns_true_when_client_can_list_buckets(self, s3):
        assert s3.confirm_client() is True

    def test_returns_false_when_list_buckets_raises(self, s3):
        with patch.object(s3.client, "list_buckets", side_effect=Exception("connection refused")):
            assert s3.confirm_client() is False

    def test_returns_false_on_client_error(self, s3):
        with patch.object(s3.client, "list_buckets", side_effect=_client_error("AccessDenied")):
            assert s3.confirm_client() is False

    def test_logs_warning_on_failure(self, s3):
        with patch.object(s3.client, "list_buckets", side_effect=Exception("timeout")):
            s3.confirm_client()
        s3.logger.warning.assert_called_once()

    def test_warning_message_contains_exception(self, s3):
        with patch.object(s3.client, "list_buckets", side_effect=Exception("timeout")):
            s3.confirm_client()
        warning_msg = s3.logger.warning.call_args[0][0]
        assert "timeout" in warning_msg

    def test_no_warning_logged_on_success(self, s3):
        s3.confirm_client()
        s3.logger.warning.assert_not_called()

# ===========================================================================
# __init__ – endpoint normalisation
# ===========================================================================

class TestEndpointNormalisation:
    """Tests for the s3:// stripping and scheme-injection logic."""

    def test_s3_scheme_replaced_with_https_when_use_ssl_none(self):
        with mock_aws():
            inst = _make_s3_instance(endpoint="s3://myhost:9000", use_ssl=None)
        assert inst.endpoint == "https://myhost:9000"

    def test_s3_scheme_replaced_with_https_when_use_ssl_true(self):
        with mock_aws():
            inst = _make_s3_instance(endpoint="s3://myhost:9000", use_ssl=True)
        assert inst.endpoint == "https://myhost:9000"

    def test_s3_scheme_replaced_with_http_when_use_ssl_false(self):
        with mock_aws():
            inst = _make_s3_instance(endpoint="s3://myhost:9000", use_ssl=False)
        assert inst.endpoint == "http://myhost:9000"

    def test_bare_host_gets_https_when_use_ssl_none(self):
        with mock_aws():
            inst = _make_s3_instance(endpoint="myhost:9000", use_ssl=None)
        assert inst.endpoint == "https://myhost:9000"

    def test_bare_host_gets_https_when_use_ssl_true(self):
        with mock_aws():
            inst = _make_s3_instance(endpoint="myhost:9000", use_ssl=True)
        assert inst.endpoint == "https://myhost:9000"

    def test_bare_host_gets_http_when_use_ssl_false(self):
        with mock_aws():
            inst = _make_s3_instance(endpoint="myhost:9000", use_ssl=False)
        assert inst.endpoint == "http://myhost:9000"

    def test_https_endpoint_unchanged(self):
        with mock_aws():
            inst = _make_s3_instance(endpoint="https://myhost:9000")
        assert inst.endpoint == "https://myhost:9000"

    def test_http_endpoint_unchanged(self):
        with mock_aws():
            inst = _make_s3_instance(endpoint="http://myhost:9000")
        assert inst.endpoint == "http://myhost:9000"

    def test_none_endpoint_not_modified(self):
        with mock_aws():
            inst = _make_s3_instance(endpoint=None)
        # Should remain whatever the env default resolved to, not crash
        assert inst.endpoint == DEFAULT_ENDPOINT

# ===========================================================================
# get_object_stream
# ===========================================================================

class TestGetObjectStream:
    def test_returns_readable_stream_with_correct_content(self, s3):
        body = b"stream me"
        _put_object(s3.client, SRC_BUCKET, "stream.bin", body=body)
        stream = s3.get_object_stream(SRC_BUCKET, "stream.bin")
        assert stream.read() == body

    def test_raises_on_missing_object(self, s3):
        with pytest.raises(ClientError):
            s3.get_object_stream(SRC_BUCKET, "ghost.bin")

    def test_raises_on_missing_bucket(self, s3):
        with pytest.raises(ClientError):
            s3.get_object_stream("no-such-bucket", "key.bin")

    def test_returns_streaming_body_type(self, s3):
        from botocore.response import StreamingBody
        _put_object(s3.client, SRC_BUCKET, "typed.bin", body=b"x")
        stream = s3.get_object_stream(SRC_BUCKET, "typed.bin")
        assert isinstance(stream, StreamingBody)

    def test_large_object_content_intact(self, s3):
        body = b"Z" * (1024 * 1024)  # 1 MiB
        _put_object(s3.client, SRC_BUCKET, "big.bin", body=body)
        assert s3.get_object_stream(SRC_BUCKET, "big.bin").read() == body


# ===========================================================================
# get_object_range
# ===========================================================================

class TestGetObjectRange:
    def test_returns_correct_bytes_for_range(self, s3):
        _put_object(s3.client, SRC_BUCKET, "range.bin", body=b"0123456789")
        assert s3.get_object_range(SRC_BUCKET, "range.bin", 2, 5) == b"2345"

    def test_end_none_reads_to_eof(self, s3):
        _put_object(s3.client, SRC_BUCKET, "range.bin", body=b"0123456789")
        assert s3.get_object_range(SRC_BUCKET, "range.bin", 7) == b"789"

    def test_start_zero_reads_from_beginning(self, s3):
        _put_object(s3.client, SRC_BUCKET, "range.bin", body=b"abcdef")
        assert s3.get_object_range(SRC_BUCKET, "range.bin", 0, 2) == b"abc"

    def test_raises_on_missing_object(self, s3):
        with pytest.raises(ClientError):
            s3.get_object_range(SRC_BUCKET, "ghost.bin", 0, 10)

    def test_single_byte_range(self, s3):
        _put_object(s3.client, SRC_BUCKET, "range.bin", body=b"abcdef")
        assert s3.get_object_range(SRC_BUCKET, "range.bin", 3, 3) == b"d"


# ===========================================================================
# get_object_bytes
# ===========================================================================

class TestGetObjectBytes:
    def test_returns_correct_bytes(self, s3):
        body = b"hello bytes"
        _put_object(s3.client, SRC_BUCKET, "obj.bin", body=body)
        assert s3.get_object_bytes(SRC_BUCKET, "obj.bin") == body

    def test_raises_on_missing_object(self, s3):
        with pytest.raises(ClientError):
            s3.get_object_bytes(SRC_BUCKET, "ghost.bin")

    def test_uses_transfer_config_by_default(self, s3):
        _put_object(s3.client, SRC_BUCKET, "cfg.bin", body=b"x")
        with patch.object(s3.client, "download_fileobj",
                          wraps=s3.client.download_fileobj) as spy:
            s3.get_object_bytes(SRC_BUCKET, "cfg.bin")
        _, kwargs = spy.call_args
        assert kwargs.get("Config") is s3.transfer_config

    def test_caller_config_overrides_default(self, s3):
        from boto3.s3.transfer import TransferConfig
        _put_object(s3.client, SRC_BUCKET, "cfg.bin", body=b"x")
        custom_cfg = TransferConfig()
        with patch.object(s3.client, "download_fileobj",
                          wraps=s3.client.download_fileobj) as spy:
            s3.get_object_bytes(SRC_BUCKET, "cfg.bin", Config=custom_cfg)
        _, kwargs = spy.call_args
        assert kwargs.get("Config") is custom_cfg

    def test_large_object_content_intact(self, s3):
        body = b"Q" * (2 * 1024 * 1024)
        _put_object(s3.client, SRC_BUCKET, "large.bin", body=body)
        assert s3.get_object_bytes(SRC_BUCKET, "large.bin") == body

    def test_empty_object_returns_empty_bytes(self, s3):
        _put_object(s3.client, SRC_BUCKET, "empty.bin", body=b"")
        assert s3.get_object_bytes(SRC_BUCKET, "empty.bin") == b""


# ===========================================================================
# get_object_text
# ===========================================================================

class TestGetObjectText:
    def test_returns_decoded_utf8_string(self, s3):
        _put_object(s3.client, SRC_BUCKET, "text.txt", body="hello world".encode())
        assert s3.get_object_text(SRC_BUCKET, "text.txt") == "hello world"

    def test_custom_encoding_respected(self, s3):
        text = "café"
        _put_object(s3.client, SRC_BUCKET, "latin.txt", body=text.encode("latin-1"))
        assert s3.get_object_text(SRC_BUCKET, "latin.txt", encoding="latin-1") == text

    def test_raises_unicode_decode_error_on_wrong_encoding(self, s3):
        _put_object(s3.client, SRC_BUCKET, "latin.txt", body="café".encode("latin-1"))
        with pytest.raises(UnicodeDecodeError):
            s3.get_object_text(SRC_BUCKET, "latin.txt", encoding="ascii")

    def test_raises_on_missing_object(self, s3):
        with pytest.raises(ClientError):
            s3.get_object_text(SRC_BUCKET, "ghost.txt")

    def test_delegates_to_get_object_bytes(self, s3):
        _put_object(s3.client, SRC_BUCKET, "delegate.txt", body=b"hi")
        with patch.object(s3, "get_object_bytes",
                          wraps=s3.get_object_bytes) as spy:
            s3.get_object_text(SRC_BUCKET, "delegate.txt")
        spy.assert_called_once_with(bucket=SRC_BUCKET, key="delegate.txt")

    def test_kwargs_forwarded_to_get_object_bytes(self, s3):
        from boto3.s3.transfer import TransferConfig
        _put_object(s3.client, SRC_BUCKET, "fwd.txt", body=b"x")
        custom_cfg = TransferConfig()
        with patch.object(s3, "get_object_bytes",
                          wraps=s3.get_object_bytes) as spy:
            s3.get_object_text(SRC_BUCKET, "fwd.txt", Config=custom_cfg)
        _, kwargs = spy.call_args
        assert kwargs.get("Config") is custom_cfg


# ===========================================================================
# put_object_bytes
# ===========================================================================

class TestPutObjectBytes:
    def test_uploaded_content_retrievable(self, s3):
        body = b"put me"
        s3.put_object_bytes(SRC_BUCKET, "put.bin", body)
        assert s3.client.get_object(Bucket=SRC_BUCKET, Key="put.bin")["Body"].read() == body

    def test_tagging_as_dict_applied_correctly(self, s3):
        s3.put_object_bytes(SRC_BUCKET, "tagged.bin", b"x", tagging={"env": "test", "team": "data"})
        tags = s3.client.get_object_tagging(Bucket=SRC_BUCKET, Key="tagged.bin")
        tag_dict = {t["Key"]: t["Value"] for t in tags["TagSet"]}
        assert tag_dict == {"env": "test", "team": "data"}

    def test_tagging_as_url_encoded_string_applied_correctly(self, s3):
        s3.put_object_bytes(SRC_BUCKET, "tagged.bin", b"x", tagging="stage=prod&owner=alice")
        tags = s3.client.get_object_tagging(Bucket=SRC_BUCKET, Key="tagged.bin")
        tag_dict = {t["Key"]: t["Value"] for t in tags["TagSet"]}
        assert tag_dict == {"stage": "prod", "owner": "alice"}

    def test_tagging_in_kwargs_accepted(self, s3):
        s3.put_object_bytes(SRC_BUCKET, "tagged.bin", b"x", ExtraArgs=dict(Tagging="env=staging"))
        tags = s3.client.get_object_tagging(Bucket=SRC_BUCKET, Key="tagged.bin")
        tag_dict = {t["Key"]: t["Value"] for t in tags["TagSet"]}
        assert tag_dict == {"env": "staging"}

    def test_tagging_param_wins_over_kwargs_tagging(self, s3):
        """Explicit tagging= takes precedence over Tagging= in kwargs."""
        s3.put_object_bytes(SRC_BUCKET, "tagged.bin", b"x",
                            tagging="winner=yes", ExtraArgs=dict(Tagging="winner=no"))
        tags = s3.client.get_object_tagging(Bucket=SRC_BUCKET, Key="tagged.bin")
        tag_dict = {t["Key"]: t["Value"] for t in tags["TagSet"]}
        assert tag_dict == {"winner": "yes"}

    def test_no_tagging_produces_empty_tag_set(self, s3):
        s3.put_object_bytes(SRC_BUCKET, "untagged.bin", b"x")
        tags = s3.client.get_object_tagging(Bucket=SRC_BUCKET, Key="untagged.bin")
        assert tags["TagSet"] == []

    def test_uses_transfer_config_by_default(self, s3):
        with patch.object(s3.client, "upload_fileobj",
                          wraps=s3.client.upload_fileobj) as spy:
            s3.put_object_bytes(SRC_BUCKET, "cfg.bin", b"x")
        _, kwargs = spy.call_args
        assert kwargs.get("Config") is s3.transfer_config

    def test_caller_config_overrides_default(self, s3):
        from boto3.s3.transfer import TransferConfig
        custom_cfg = TransferConfig()
        with patch.object(s3.client, "upload_fileobj",
                          wraps=s3.client.upload_fileobj) as spy:
            s3.put_object_bytes(SRC_BUCKET, "cfg.bin", b"x", Config=custom_cfg)
        _, kwargs = spy.call_args
        assert kwargs.get("Config") is custom_cfg

    def test_empty_bytes_uploaded_successfully(self, s3):
        s3.put_object_bytes(SRC_BUCKET, "empty.bin", b"")
        assert s3.client.get_object(Bucket=SRC_BUCKET, Key="empty.bin")["Body"].read() == b""

    def test_overwrite_existing_object(self, s3):
        _put_object(s3.client, SRC_BUCKET, "overwrite.bin", body=b"old")
        s3.put_object_bytes(SRC_BUCKET, "overwrite.bin", b"new")
        assert s3.client.get_object(Bucket=SRC_BUCKET, Key="overwrite.bin")["Body"].read() == b"new"


# ===========================================================================
# put_object_text
# ===========================================================================

class TestPutObjectText:
    def test_text_uploaded_and_retrievable_as_utf8(self, s3):
        s3.put_object_text(SRC_BUCKET, "hello.txt", "hello world")
        body = s3.client.get_object(Bucket=SRC_BUCKET, Key="hello.txt")["Body"].read()
        assert body == b"hello world"

    def test_custom_encoding_used_for_upload(self, s3):
        text = "café"
        s3.put_object_text(SRC_BUCKET, "latin.txt", text, encoding="latin-1")
        body = s3.client.get_object(Bucket=SRC_BUCKET, Key="latin.txt")["Body"].read()
        assert body == text.encode("latin-1")

    def test_raises_unicode_encode_error_on_bad_encoding(self, s3):
        with pytest.raises((UnicodeEncodeError, LookupError)):
            s3.put_object_text(SRC_BUCKET, "bad.txt", "hello", encoding="ascii_bad_codec")

    def test_tagging_forwarded_to_put_object_bytes(self, s3):
        with patch.object(s3, "put_object_bytes",
                          wraps=s3.put_object_bytes) as spy:
            s3.put_object_text(SRC_BUCKET, "tagged.txt", "x", tagging={"k": "v"})
        _, kwargs = spy.call_args
        assert kwargs.get("tagging") == {"k": "v"}

    def test_kwargs_forwarded_to_put_object_bytes(self, s3):
        from boto3.s3.transfer import TransferConfig
        custom_cfg = TransferConfig()
        with patch.object(s3, "put_object_bytes",
                          wraps=s3.put_object_bytes) as spy:
            s3.put_object_text(SRC_BUCKET, "fwd.txt", "x", Config=custom_cfg)
        _, kwargs = spy.call_args
        assert kwargs.get("Config") is custom_cfg

    def test_delegates_encoding_to_put_object_bytes(self, s3):
        """put_object_text must pass the encoded bytes, not the raw string."""
        text = "こんにちは"
        with patch.object(s3, "put_object_bytes",
                          wraps=s3.put_object_bytes) as spy:
            s3.put_object_text(SRC_BUCKET, "unicode.txt", text, encoding="utf-8")
        _, kwargs = spy.call_args
        assert kwargs.get('data') == text.encode("utf-8")

    def test_round_trip_via_get_object_text(self, s3):
        text = "round-trip ✓"
        s3.put_object_text(SRC_BUCKET, "rt.txt", text)
        assert s3.get_object_text(SRC_BUCKET, "rt.txt") == text
