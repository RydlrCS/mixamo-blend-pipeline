"""Tests for configuration loader and validator."""

from pathlib import Path
from typing import Any, Dict

import pytest

from src.utils.config_loader import (
    ConfigError,
    get_config_examples,
    load_config,
    validate_config,
)

# Test data directory
TEST_DATA_DIR = Path(__file__).parent / "test_data"


class TestConfigLoader:
    """Tests for load_config function."""

    def test_load_valid_yaml(self, tmp_path: Path):
        """Test loading valid YAML configuration."""
        config_file = tmp_path / "test.yaml"
        config_file.write_text(
            """
version: "1.0"
workflow: blend_batch
blends:
  - input1: a.bvh
    input2: b.bvh
    output: c.bvh
"""
        )

        config = load_config(config_file)
        assert config["version"] == "1.0"
        assert config["workflow"] == "blend_batch"
        assert len(config["blends"]) == 1

    def test_load_nonexistent_file(self):
        """Test loading non-existent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_config("nonexistent.yaml")

    def test_load_empty_file(self, tmp_path: Path):
        """Test loading empty file raises ValueError."""
        config_file = tmp_path / "empty.yaml"
        config_file.write_text("")

        with pytest.raises(ValueError, match="empty"):
            load_config(config_file)

    def test_load_invalid_yaml(self, tmp_path: Path):
        """Test loading malformed YAML raises YAMLError."""
        config_file = tmp_path / "invalid.yaml"
        config_file.write_text(
            """
version: "1.0"
workflow: [unclosed bracket
"""
        )

        # Import here to handle optional yaml dependency
        try:
            import yaml

            with pytest.raises(yaml.YAMLError):
                load_config(config_file)
        except ImportError:
            pytest.skip("PyYAML not installed")

    def test_load_directory_raises_error(self, tmp_path: Path):
        """Test loading directory path raises ValueError."""
        with pytest.raises(ValueError, match="not a file"):
            load_config(tmp_path)


class TestConfigValidation:
    """Tests for validate_config function."""

    def test_validate_missing_version(self):
        """Test validation fails when version is missing."""
        config: Dict[str, Any] = {"workflow": "blend_batch"}
        errors = validate_config(config)

        assert len(errors) > 0
        assert any("version" in e.field for e in errors)

    def test_validate_unsupported_version(self):
        """Test validation fails for unsupported version."""
        config: Dict[str, Any] = {"version": "99.0", "workflow": "blend_batch"}
        errors = validate_config(config)

        assert len(errors) > 0
        version_errors = [e for e in errors if "version" in e.field]
        assert len(version_errors) > 0
        assert "unsupported" in str(version_errors[0]).lower()

    def test_validate_missing_workflow(self):
        """Test validation fails when workflow is missing."""
        config: Dict[str, Any] = {"version": "1.0"}
        errors = validate_config(config)

        assert len(errors) > 0
        assert any("workflow" in e.field for e in errors)

    def test_validate_invalid_workflow(self):
        """Test validation fails for invalid workflow type."""
        config: Dict[str, Any] = {"version": "1.0", "workflow": "invalid_workflow"}
        errors = validate_config(config)

        assert len(errors) > 0
        workflow_errors = [e for e in errors if "workflow" in e.field]
        assert len(workflow_errors) > 0

    def test_validate_valid_blend_batch(self):
        """Test validation passes for valid blend_batch config."""
        config: Dict[str, Any] = {
            "version": "1.0",
            "workflow": "blend_batch",
            "blends": [
                {
                    "input1": "a.bvh",
                    "input2": "b.bvh",
                    "output": "c.bvh",
                    "ratio": 0.5,
                    "method": "linear",
                }
            ],
        }
        errors = validate_config(config)
        assert len(errors) == 0

    def test_validate_blend_batch_missing_blends(self):
        """Test validation fails when blends field is missing."""
        config: Dict[str, Any] = {"version": "1.0", "workflow": "blend_batch"}
        errors = validate_config(config)

        assert len(errors) > 0
        assert any("blends" in e.field for e in errors)

    def test_validate_blend_batch_empty_blends(self):
        """Test validation fails when blends list is empty."""
        config: Dict[str, Any] = {
            "version": "1.0",
            "workflow": "blend_batch",
            "blends": [],
        }
        errors = validate_config(config)

        assert len(errors) > 0
        assert any("blends" in e.field and "at least one" in e.message for e in errors)

    def test_validate_blend_batch_invalid_blends_type(self):
        """Test validation fails when blends is not a list."""
        config: Dict[str, Any] = {
            "version": "1.0",
            "workflow": "blend_batch",
            "blends": "not a list",
        }
        errors = validate_config(config)

        assert len(errors) > 0
        assert any("blends" in e.field and "list" in e.message for e in errors)

    def test_validate_blend_missing_required_fields(self):
        """Test validation fails when blend missing required fields."""
        config: Dict[str, Any] = {
            "version": "1.0",
            "workflow": "blend_batch",
            "blends": [{"input1": "a.bvh"}],  # Missing input2 and output
        }
        errors = validate_config(config)

        assert len(errors) >= 2
        assert any("input2" in e.field for e in errors)
        assert any("output" in e.field for e in errors)

    def test_validate_blend_invalid_ratio(self):
        """Test validation fails for invalid ratio values."""
        # Test ratio > 1.0
        config: Dict[str, Any] = {
            "version": "1.0",
            "workflow": "blend_batch",
            "blends": [
                {
                    "input1": "a.bvh",
                    "input2": "b.bvh",
                    "output": "c.bvh",
                    "ratio": 1.5,
                }
            ],
        }
        errors = validate_config(config)
        assert any("ratio" in e.field and "between 0.0 and 1.0" in e.message for e in errors)

        # Test ratio < 0.0
        config["blends"][0]["ratio"] = -0.5
        errors = validate_config(config)
        assert any("ratio" in e.field for e in errors)

    def test_validate_blend_invalid_method(self):
        """Test validation fails for invalid blend method."""
        config: Dict[str, Any] = {
            "version": "1.0",
            "workflow": "blend_batch",
            "blends": [
                {
                    "input1": "a.bvh",
                    "input2": "b.bvh",
                    "output": "c.bvh",
                    "method": "invalid_method",
                }
            ],
        }
        errors = validate_config(config)

        assert any("method" in e.field for e in errors)

    def test_validate_download_batch_valid(self):
        """Test validation passes for valid download_batch config."""
        config: Dict[str, Any] = {
            "version": "1.0",
            "workflow": "download_batch",
            "downloads": [{"animation_id": "123456", "output": "walk.fbx", "format": "fbx"}],
        }
        errors = validate_config(config)
        assert len(errors) == 0

    def test_validate_download_batch_missing_downloads(self):
        """Test validation fails when downloads field is missing."""
        config: Dict[str, Any] = {"version": "1.0", "workflow": "download_batch"}
        errors = validate_config(config)

        assert len(errors) > 0
        assert any("downloads" in e.field for e in errors)

    def test_validate_download_invalid_format(self):
        """Test validation fails for invalid download format."""
        config: Dict[str, Any] = {
            "version": "1.0",
            "workflow": "download_batch",
            "downloads": [{"animation_id": "123", "output": "test.xyz", "format": "xyz"}],
        }
        errors = validate_config(config)

        assert any("format" in e.field for e in errors)

    def test_validate_upload_batch_valid(self):
        """Test validation passes for valid upload_batch config."""
        config: Dict[str, Any] = {
            "version": "1.0",
            "workflow": "upload_batch",
            "uploads": [{"file": "test.bvh", "folder": "blend/"}],
        }
        errors = validate_config(config)
        assert len(errors) == 0

    def test_validate_upload_batch_missing_uploads(self):
        """Test validation fails when uploads field is missing."""
        config: Dict[str, Any] = {"version": "1.0", "workflow": "upload_batch"}
        errors = validate_config(config)

        assert len(errors) > 0
        assert any("uploads" in e.field for e in errors)

    def test_validate_full_pipeline_valid(self):
        """Test validation passes for valid full_pipeline config."""
        config: Dict[str, Any] = {
            "version": "1.0",
            "workflow": "full_pipeline",
            "download": {"animations": []},
            "blend": {"pairs": []},
            "upload": {"files": []},
        }
        errors = validate_config(config)
        assert len(errors) == 0

    def test_validate_full_pipeline_missing_sections(self):
        """Test validation fails when pipeline sections are missing."""
        config: Dict[str, Any] = {"version": "1.0", "workflow": "full_pipeline"}
        errors = validate_config(config)

        assert len(errors) >= 3
        assert any("download" in e.field for e in errors)
        assert any("blend" in e.field for e in errors)
        assert any("upload" in e.field for e in errors)


class TestConfigError:
    """Tests for ConfigError class."""

    def test_config_error_string_without_value(self):
        """Test ConfigError string representation without value."""
        error = ConfigError("field_name", "error message")
        assert "field_name" in str(error)
        assert "error message" in str(error)

    def test_config_error_string_with_value(self):
        """Test ConfigError string representation with value."""
        error = ConfigError("field_name", "error message", "bad_value")
        error_str = str(error)
        assert "field_name" in error_str
        assert "error message" in error_str
        assert "bad_value" in error_str
        assert "got:" in error_str


class TestConfigExamples:
    """Tests for example config templates."""

    def test_get_config_examples_returns_dict(self):
        """Test get_config_examples returns dictionary."""
        examples = get_config_examples()
        assert isinstance(examples, dict)
        assert len(examples) > 0

    def test_config_examples_have_expected_keys(self):
        """Test config examples contain expected workflow types."""
        examples = get_config_examples()
        assert "blend_batch" in examples
        assert "download_batch" in examples
        assert "upload_batch" in examples

    def test_config_examples_are_valid_yaml(self):
        """Test that example templates are valid YAML."""
        try:
            import yaml
        except ImportError:
            pytest.skip("PyYAML not installed")

        examples = get_config_examples()
        for name, template in examples.items():
            try:
                parsed = yaml.safe_load(template)
                assert parsed is not None, f"Example {name} parsed to None"
                assert "version" in parsed, f"Example {name} missing version"
                assert "workflow" in parsed, f"Example {name} missing workflow"
            except yaml.YAMLError as e:
                pytest.fail(f"Example {name} has invalid YAML: {e}")

    def test_example_configs_pass_validation(self):
        """Test that example templates pass validation."""
        try:
            import yaml
        except ImportError:
            pytest.skip("PyYAML not installed")

        examples = get_config_examples()
        for name, template in examples.items():
            config = yaml.safe_load(template)
            errors = validate_config(config)
            assert (
                len(errors) == 0
            ), f"Example {name} failed validation: {[str(e) for e in errors]}"
