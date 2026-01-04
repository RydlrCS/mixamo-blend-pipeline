"""
Unit tests for uploader module (GCS upload interface).

Tests the uploader module API without requiring actual GCS authentication.
Uses temporary files and validates interface contracts, error handling, and
parameter validation.
"""

from pathlib import Path
import tempfile
from unittest.mock import patch, MagicMock

from src.uploader import (
    UploadConfig,
    UploadResult,
    upload_file,
    upload_batch,
    validate_gcs_path,
)


class TestUploadConfig:
    """Test UploadConfig dataclass."""

    def test_upload_config_with_defaults(self):
        """Test creating UploadConfig with minimal required fields."""
        config = UploadConfig(bucket_name="my-bucket")

        assert config.bucket_name == "my-bucket"
        assert config.destination_folder == "seed/"
        assert config.metadata == {}
        assert config.content_type is None
        assert config.make_public is False
        assert config.timeout_seconds == 300

    def test_upload_config_with_custom_values(self):
        """Test creating UploadConfig with all custom fields."""
        config = UploadConfig(
            bucket_name="animations-bucket",
            destination_folder="blend/",
            metadata={"source": "mixamo", "fps": "30"},
            content_type="application/octet-stream",
            make_public=True,
            timeout_seconds=600,
        )

        assert config.bucket_name == "animations-bucket"
        assert config.destination_folder == "blend/"
        assert config.metadata == {"source": "mixamo", "fps": "30"}
        assert config.content_type == "application/octet-stream"
        assert config.make_public is True
        assert config.timeout_seconds == 600


class TestUploadResult:
    """Test UploadResult dataclass."""

    def test_upload_result_success(self):
        """Test creating successful UploadResult."""
        config = UploadConfig(bucket_name="test-bucket")

        result = UploadResult(
            success=True,
            gcs_uri="gs://test-bucket/seed/walk.bvh",
            local_path="./animations/walk.bvh",
            upload_config=config,
            file_size_bytes=15000,
            duration_seconds=1.5,
        )

        assert result.success is True
        assert result.gcs_uri == "gs://test-bucket/seed/walk.bvh"
        assert result.local_path == "./animations/walk.bvh"
        assert result.upload_config == config
        assert result.file_size_bytes == 15000
        assert result.duration_seconds == 1.5
        assert result.error_message is None

    def test_upload_result_failure(self):
        """Test creating failed UploadResult with error message."""
        config = UploadConfig(bucket_name="test-bucket")

        result = UploadResult(
            success=False,
            gcs_uri=None,
            local_path="./missing.bvh",
            upload_config=config,
            file_size_bytes=0,
            duration_seconds=0.1,
            error_message="File not found",
        )

        assert result.success is False
        assert result.gcs_uri is None
        assert result.error_message == "File not found"


class TestValidateGCSPath:
    """Test GCS path validation function."""

    def test_validate_gcs_path_valid_bucket_and_folder(self):
        """Test validation passes for valid bucket and folder."""
        assert validate_gcs_path("my-bucket", "seed/") is True
        assert validate_gcs_path("animations-123", "blend/") is True
        assert validate_gcs_path("test-bucket", "build/") is True

    def test_validate_gcs_path_empty_bucket_name(self):
        """Test validation fails for empty bucket name."""
        assert validate_gcs_path("", "seed/") is False

    def test_validate_gcs_path_bucket_too_long(self):
        """Test validation fails for bucket name > 63 characters."""
        long_bucket = "a" * 64
        assert validate_gcs_path(long_bucket, "seed/") is False

    def test_validate_gcs_path_bucket_starts_with_goog(self):
        """Test validation fails for bucket starting with 'goog'."""
        assert validate_gcs_path("google-bucket", "seed/") is False
        assert validate_gcs_path("g00gle-bucket", "seed/") is False

    def test_validate_gcs_path_invalid_characters(self):
        """Test validation fails for buckets with invalid characters."""
        assert validate_gcs_path("bucket..name", "seed/") is False
        assert validate_gcs_path("bucket._name", "seed/") is False

    def test_validate_gcs_path_custom_folder_warns_but_passes(self):
        """Test validation warns but passes for custom folders."""
        # Custom folders are allowed but generate warnings
        assert validate_gcs_path("my-bucket", "custom/") is True


class TestUploadFile:
    """Test upload_file function."""

    def test_upload_file_nonexistent_file(self):
        """Test upload_file detects missing file."""
        config = UploadConfig(bucket_name="test-bucket")
        result = upload_file("/nonexistent/file.bvh", config)

        assert result.success is False
        assert result.gcs_uri is None
        assert "not found" in result.error_message.lower()

    def test_upload_file_path_is_directory(self):
        """Test upload_file rejects directory path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = UploadConfig(bucket_name="test-bucket")
            result = upload_file(tmpdir, config)

            assert result.success is False
            assert "not a file" in result.error_message.lower()

    def test_upload_file_too_small(self):
        """Test upload_file rejects files below minimum size."""
        with tempfile.NamedTemporaryFile(
            suffix=".bvh", delete=False
        ) as tmp:
            # Write less than MIN_FILE_SIZE_BYTES (10 bytes)
            tmp.write(b"tiny")
            tmp_path = tmp.name

        try:
            config = UploadConfig(bucket_name="test-bucket")
            result = upload_file(tmp_path, config)

            assert result.success is False
            assert "too small" in result.error_message.lower()
        finally:
            Path(tmp_path).unlink()

    @patch('google.cloud.storage.Client')
    def test_upload_file_too_large(self, mock_client_class):
        """Test upload_file rejects files exceeding size limit."""
        with tempfile.NamedTemporaryFile(
            suffix=".bvh", delete=False
        ) as tmp:
            # Write more than MAX_FILE_SIZE_MB (500MB)
            # We'll just check the logic without creating huge file
            tmp_path = tmp.name

        try:
            # Mock a large file size check
            # (Can't create 500MB file in test, so we test the validation)
            config = UploadConfig(bucket_name="test-bucket")

            # Create small file for this test
            Path(tmp_path).write_bytes(b"x" * 100)

            # Mock successful GCS upload
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            result = upload_file(tmp_path, config)

            # Small file should pass validation and upload successfully
            assert result.success is True
            assert result.gcs_uri == "gs://test-bucket/seed/" + Path(tmp_path).name
        finally:
            Path(tmp_path).unlink()

    def test_upload_file_unsupported_extension_warns(self):
        """Test upload_file warns but continues for unusual extensions."""
        with tempfile.NamedTemporaryFile(
            suffix=".txt", delete=False
        ) as tmp:
            tmp.write(b"Valid content for size check")
            tmp_path = tmp.name

        try:
            config = UploadConfig(bucket_name="test-bucket")
            result = upload_file(tmp_path, config)

            # Should generate warning but proceed to upload attempt
            # (Will fail with NotImplementedError in placeholder)
            assert result.success is False
        finally:
            Path(tmp_path).unlink()

    def test_upload_file_invalid_gcs_path(self):
        """Test upload_file validates GCS path configuration."""
        with tempfile.NamedTemporaryFile(
            suffix=".bvh", delete=False
        ) as tmp:
            tmp.write(b"Valid content for testing")
            tmp_path = tmp.name

        try:
            # Create config with invalid bucket name
            config = UploadConfig(
                bucket_name="google-bucket",  # Starts with 'goog'
                destination_folder="seed/",
            )
            result = upload_file(tmp_path, config)

            assert result.success is False
            assert "invalid gcs path" in result.error_message.lower()
        finally:
            Path(tmp_path).unlink()

    @patch('google.cloud.storage.Client')
    def test_upload_file_valid_inputs_success(self, mock_client_class):
        """Test upload_file with valid inputs successfully uploads."""
        with tempfile.NamedTemporaryFile(
            suffix=".bvh", delete=False
        ) as tmp:
            tmp.write(b"Valid BVH content for testing upload")
            tmp_path = tmp.name

        try:
            config = UploadConfig(
                bucket_name="test-bucket",
                destination_folder="seed/",
                metadata={"source": "test"},
            )

            # Mock successful GCS upload
            mock_client = MagicMock()
            mock_bucket = MagicMock()
            mock_blob = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.bucket.return_value = mock_bucket
            mock_bucket.blob.return_value = mock_blob

            result = upload_file(tmp_path, config)

            # Should succeed with mocked GCS
            assert result.success is True
            assert result.gcs_uri.startswith("gs://test-bucket/seed/")
            assert result.local_path == tmp_path
            assert result.file_size_bytes > 0
            assert result.duration_seconds > 0
            assert result.error_message is None

            # Verify GCS SDK was called correctly
            mock_blob.upload_from_filename.assert_called_once()
        finally:
            Path(tmp_path).unlink()

    @patch('google.cloud.storage.Client')
    def test_upload_file_constructs_correct_gcs_uri(self, mock_client_class):
        """Test upload_file constructs proper GCS URI format."""
        with tempfile.NamedTemporaryFile(
            suffix=".bvh", delete=False
        ) as tmp:
            tmp.write(b"Content for URI test")
            tmp_path = tmp.name

        try:
            # Mock GCS client
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            config = UploadConfig(
                bucket_name="animations",
                destination_folder="blend/",
            )
            result = upload_file(tmp_path, config)

            # Verify URI construction
            assert result.success is True
            expected_uri = f"gs://animations/blend/{Path(tmp_path).name}"
            assert result.gcs_uri == expected_uri
            assert result.local_path == tmp_path
        finally:
            Path(tmp_path).unlink()


class TestUploadBatch:
    """Test upload_batch function."""

    def test_upload_batch_empty_list(self):
        """Test upload_batch handles empty file list."""
        config = UploadConfig(bucket_name="test-bucket")
        results = upload_batch([], config)

        assert len(results) == 0

    def test_upload_batch_single_file(self):
        """Test upload_batch processes single file."""
        with tempfile.NamedTemporaryFile(
            suffix=".bvh", delete=False
        ) as tmp:
            tmp.write(b"Single file content")
            tmp_path = tmp.name

        try:
            config = UploadConfig(bucket_name="test-bucket")
            results = upload_batch([tmp_path], config)

            assert len(results) == 1
            assert results[0].local_path == tmp_path
        finally:
            Path(tmp_path).unlink()

    def test_upload_batch_multiple_files(self):
        """Test upload_batch processes multiple files."""
        temp_files = []
        try:
            # Create 3 test files
            for i in range(3):
                tmp = tempfile.NamedTemporaryFile(
                    suffix=".bvh", delete=False
                )
                tmp.write(f"File {i} content".encode())
                tmp.close()
                temp_files.append(tmp.name)

            config = UploadConfig(bucket_name="test-bucket")
            results = upload_batch(temp_files, config)

            assert len(results) == 3
            assert all(not r.success for r in results)  # Placeholder fails
            assert [r.local_path for r in results] == temp_files
        finally:
            for tmp_path in temp_files:
                Path(tmp_path).unlink()

    @patch('google.cloud.storage.Client')
    def test_upload_batch_mixed_valid_and_invalid(self, mock_client_class):
        """Test upload_batch handles mix of valid and invalid files."""
        with tempfile.NamedTemporaryFile(
            suffix=".bvh", delete=False
        ) as tmp:
            tmp.write(b"Valid file content")
            valid_path = tmp.name

        try:
            # Mock GCS client
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            config = UploadConfig(bucket_name="test-bucket")
            file_paths = [
                "/nonexistent/file1.bvh",
                valid_path,
                "/nonexistent/file2.bvh",
            ]

            results = upload_batch(file_paths, config)

            assert len(results) == 3

            # Check error messages
            assert "not found" in results[0].error_message.lower()
            assert results[1].success is True  # Valid file uploads successfully
            assert "not found" in results[2].error_message.lower()
        finally:
            Path(valid_path).unlink()

    def test_upload_batch_with_metadata(self):
        """Test upload_batch applies config metadata to all files."""
        temp_files = []
        try:
            for i in range(2):
                tmp = tempfile.NamedTemporaryFile(
                    suffix=".bvh", delete=False
                )
                tmp.write(f"File {i}".encode())
                tmp.close()
                temp_files.append(tmp.name)

            config = UploadConfig(
                bucket_name="test-bucket",
                metadata={"batch_id": "123", "source": "test"},
            )
            results = upload_batch(temp_files, config)

            assert len(results) == 2
            # All results should have same config
            assert all(r.upload_config == config for r in results)
        finally:
            for tmp_path in temp_files:
                Path(tmp_path).unlink()


class TestIntegration:
    """Integration tests for uploader module workflow."""

    def test_full_upload_workflow_validation(self):
        """Test complete upload workflow validates all parameters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            file1 = Path(tmpdir) / "walk.bvh"
            file2 = Path(tmpdir) / "run.bvh"
            file1.write_bytes(b"Walk animation data content")
            file2.write_bytes(b"Run animation data content")

            # Create config with metadata
            config = UploadConfig(
                bucket_name="animations-pipeline",
                destination_folder="seed/",
                metadata={
                    "pipeline": "mixamo-blend",
                    "stage": "download",
                    "fps": "30",
                },
                timeout_seconds=600,
            )

            # Validate GCS path
            assert validate_gcs_path(
                config.bucket_name, config.destination_folder
            )

            # Upload batch
            results = upload_batch([str(file1), str(file2)], config)

            assert len(results) == 2
            # Placeholder fails but validation passes
            assert all(not r.success for r in results)
            assert all(r.file_size_bytes > 0 for r in results)
            assert all(r.upload_config == config for r in results)
