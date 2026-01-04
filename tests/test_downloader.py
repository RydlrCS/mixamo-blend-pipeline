"""
Unit tests for Mixamo downloader module.

Tests verify:
- Download validation logic
- Error handling for invalid inputs
- File existence and size checks
- Batch download processing
- DownloadResult dataclass behavior
"""

import tempfile
from pathlib import Path
import pytest

from src.downloader import download_animation, download_batch, validate_download
from src.downloader.downloader import DownloadResult


class TestValidateDownload:
    """Test suite for download validation function."""

    def test_validate_nonexistent_file_returns_false(self) -> None:
        """Test that validation fails for non-existent files."""
        result = validate_download("/nonexistent/path/to/file.fbx")
        assert result is False

    def test_validate_empty_path_raises_value_error(self) -> None:
        """Test that empty file path raises ValueError."""
        with pytest.raises(ValueError, match="file_path cannot be empty"):
            validate_download("")

    def test_validate_whitespace_path_raises_value_error(self) -> None:
        """Test that whitespace-only path raises ValueError."""
        with pytest.raises(ValueError, match="file_path cannot be empty"):
            validate_download("   ")

    def test_validate_directory_returns_false(self) -> None:
        """Test that validation fails when path is a directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = validate_download(tmpdir)
            assert result is False

    def test_validate_file_too_small_returns_false(self) -> None:
        """Test that validation fails for files below minimum size."""
        with tempfile.NamedTemporaryFile(suffix=".fbx", delete=False) as tmp:
            tmp.write(b"small")  # Only 5 bytes
            tmp.flush()
            tmp_path = tmp.name

        try:
            result = validate_download(tmp_path, min_size_bytes=1024)
            assert result is False
        finally:
            Path(tmp_path).unlink()

    def test_validate_unsupported_format_returns_false(self) -> None:
        """Test that validation fails for unsupported file formats."""
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            tmp.write(b"x" * 2000)  # Large enough
            tmp.flush()
            tmp_path = tmp.name

        try:
            result = validate_download(tmp_path)
            assert result is False
        finally:
            Path(tmp_path).unlink()

    def test_validate_valid_fbx_file_returns_true(self) -> None:
        """Test that validation succeeds for valid FBX file."""
        with tempfile.NamedTemporaryFile(suffix=".fbx", delete=False) as tmp:
            tmp.write(b"x" * 2000)  # Large enough to pass size check
            tmp.flush()
            tmp_path = tmp.name

        try:
            result = validate_download(tmp_path, min_size_bytes=1024)
            assert result is True
        finally:
            Path(tmp_path).unlink()

    def test_validate_valid_bvh_file_returns_true(self) -> None:
        """Test that validation succeeds for valid BVH file."""
        with tempfile.NamedTemporaryFile(suffix=".bvh", delete=False) as tmp:
            tmp.write(b"x" * 2000)
            tmp.flush()
            tmp_path = tmp.name

        try:
            result = validate_download(tmp_path, min_size_bytes=1024)
            assert result is True
        finally:
            Path(tmp_path).unlink()


class TestDownloadAnimation:
    """Test suite for single animation download function."""

    def test_download_empty_animation_id_raises_value_error(self) -> None:
        """Test that empty animation_id raises ValueError."""
        with pytest.raises(ValueError, match="animation_id cannot be empty"):
            download_animation("", "./output.fbx")

    def test_download_empty_output_path_raises_value_error(self) -> None:
        """Test that empty output_path raises ValueError."""
        with pytest.raises(ValueError, match="output_path cannot be empty"):
            download_animation("123456", "")

    def test_download_unsupported_format_raises_value_error(self) -> None:
        """Test that unsupported format raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported format"):
            download_animation("123456", "./output.mp4", format="mp4")

    def test_download_creates_output_directory(self) -> None:
        """Test that download creates output directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "subdir" / "animation.fbx"
            download_animation("123456", str(output_path))

            # Check that parent directory was created
            assert output_path.parent.exists()
            assert output_path.parent.is_dir()

    def test_download_existing_file_without_overwrite_returns_success(self) -> None:
        """Test that existing file without overwrite flag returns success without downloading."""
        with tempfile.NamedTemporaryFile(suffix=".fbx", delete=False) as tmp:
            tmp.write(b"existing animation data")
            tmp.flush()
            tmp_path = tmp.name

        try:
            result = download_animation("123456", tmp_path, overwrite=False)

            assert result.success is True
            assert result.file_path is not None
            assert result.animation_id == "123456"
        finally:
            Path(tmp_path).unlink()

    def test_download_returns_not_implemented_result(self) -> None:
        """Test that download returns not-implemented result (until API integration)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "animation.fbx"
            result = download_animation("123456", str(output_path))

            # Until Mixamo API is integrated, should return failure
            assert result.success is False
            assert result.error_message is not None
            assert "not yet implemented" in result.error_message.lower()
            assert result.animation_id == "123456"


class TestDownloadBatch:
    """Test suite for batch download function."""

    def test_batch_empty_configs_raises_value_error(self) -> None:
        """Test that empty animation configs raises ValueError."""
        with pytest.raises(ValueError, match="animation_configs cannot be empty"):
            download_batch([], "./output")

    def test_batch_empty_output_dir_raises_value_error(self) -> None:
        """Test that empty output_dir raises ValueError."""
        with pytest.raises(ValueError, match="output_dir cannot be empty"):
            download_batch([{"animation_id": "123", "output_filename": "test.fbx"}], "")

    def test_batch_creates_output_directory(self) -> None:
        """Test that batch download creates output directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "batch_output"
            configs = [{"animation_id": "123", "output_filename": "test.fbx"}]

            download_batch(configs, str(output_dir))

            assert output_dir.exists()
            assert output_dir.is_dir()

    def test_batch_processes_all_configs(self) -> None:
        """Test that batch download processes all animation configs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            configs = [
                {"animation_id": "123", "output_filename": "walk.fbx"},
                {"animation_id": "456", "output_filename": "run.fbx"},
                {"animation_id": "789", "output_filename": "jump.fbx"},
            ]

            results = download_batch(configs, tmpdir)

            assert len(results) == 3
            assert all(isinstance(r, DownloadResult) for r in results)

    def test_batch_handles_missing_animation_id(self) -> None:
        """Test that batch handles configs with missing animation_id."""
        with tempfile.TemporaryDirectory() as tmpdir:
            configs = [
                {"output_filename": "test.fbx"}  # Missing animation_id
            ]

            results = download_batch(configs, tmpdir)

            assert len(results) == 1
            assert results[0].success is False
            assert "Missing animation_id" in results[0].error_message

    def test_batch_handles_missing_output_filename(self) -> None:
        """Test that batch handles configs with missing output_filename."""
        with tempfile.TemporaryDirectory() as tmpdir:
            configs = [
                {"animation_id": "123"}  # Missing output_filename
            ]

            results = download_batch(configs, tmpdir)

            assert len(results) == 1
            assert results[0].success is False
            assert "Missing output_filename" in results[0].error_message


class TestDownloadResult:
    """Test suite for DownloadResult dataclass."""

    def test_download_result_creation(self) -> None:
        """Test that DownloadResult can be created with all fields."""
        result = DownloadResult(
            success=True,
            file_path="/path/to/file.fbx",
            animation_id="123456",
            error_message=None,
            file_size_bytes=5000,
            duration_seconds=1.5,
        )

        assert result.success is True
        assert result.file_path == "/path/to/file.fbx"
        assert result.animation_id == "123456"
        assert result.error_message is None
        assert result.file_size_bytes == 5000
        assert result.duration_seconds == 1.5

    def test_download_result_minimal_fields(self) -> None:
        """Test that DownloadResult can be created with minimal required fields."""
        result = DownloadResult(
            success=False, file_path=None, animation_id="123456", error_message="Download failed"
        )

        assert result.success is False
        assert result.file_path is None
        assert result.animation_id == "123456"
        assert result.error_message == "Download failed"
        assert result.file_size_bytes is None
        assert result.duration_seconds is None
