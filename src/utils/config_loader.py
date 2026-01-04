"""
Configuration loader and validator for pipeline workflows.

Loads YAML configuration files for batch processing, pipeline orchestration,
and workflow automation. Provides validation against expected schema.

Example config file (config/blend_batch.yaml):
    ```yaml
    version: "1.0"
    workflow: blend_batch

    blends:
      - name: walk_to_run
        input1: seed/walk.bvh
        input2: seed/run.bvh
        ratio: 0.5
        method: linear
        output: blend/walk_run.bvh

      - name: idle_to_jump
        input1: seed/idle.bvh
        input2: seed/jump.bvh
        ratio: 0.3
        method: snn
        output: blend/idle_jump.bvh

    upload:
      folder: blend/
      metadata:
        source: mixamo
        pipeline: batch
    ```

Usage:
    >>> from src.utils.config_loader import load_config, validate_config
    >>> config = load_config("config/blend_batch.yaml")
    >>> errors = validate_config(config)
    >>> if not errors:
    ...     print(f"Processing {len(config['blends'])} blends")
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore

from src.utils.logging import get_logger

logger = get_logger(__name__)


# Supported config versions
SUPPORTED_VERSIONS = ["1.0"]

# Valid workflow types
VALID_WORKFLOWS = [
    "blend_batch",
    "download_batch",
    "upload_batch",
    "full_pipeline",
]

# Valid blend methods
VALID_BLEND_METHODS = ["linear", "snn", "spade"]


@dataclass
class ConfigError:
    """Validation error in configuration file."""

    field: str
    message: str
    value: Optional[Any] = None

    def __str__(self) -> str:
        """Format error message."""
        if self.value is not None:
            return f"{self.field}: {self.message} (got: {self.value})"
        return f"{self.field}: {self.message}"


def load_config(config_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Load configuration from YAML file.

    Args:
        config_path: Path to YAML configuration file

    Returns:
        Dictionary containing parsed configuration

    Raises:
        ImportError: If PyYAML is not installed
        FileNotFoundError: If config file doesn't exist
        yaml.YAMLError: If YAML is malformed

    Example:
        >>> config = load_config("config/blend_batch.yaml")
        >>> print(config["workflow"])
        blend_batch
    """
    if yaml is None:
        raise ImportError(
            "PyYAML is required for config loading. Install with: pip install pyyaml"
        )

    path = Path(config_path)
    logger.info(f"Loading configuration from: {path}")

    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")

    if not path.is_file():
        raise ValueError(f"Configuration path is not a file: {path}")

    try:
        with open(path, "r") as f:
            config = yaml.safe_load(f)

        if config is None:
            raise ValueError("Configuration file is empty")

        logger.info(f"✓ Configuration loaded: {config.get('workflow', 'unknown')}")
        return dict(config)  # Ensure we return a dict, not Any

    except yaml.YAMLError as e:
        logger.error(f"Failed to parse YAML: {e}")
        raise


def validate_config(config: Dict[str, Any]) -> List[ConfigError]:
    """
    Validate configuration against expected schema.

    Args:
        config: Configuration dictionary to validate

    Returns:
        List of validation errors (empty if valid)

    Example:
        >>> config = {"version": "1.0", "workflow": "blend_batch"}
        >>> errors = validate_config(config)
        >>> if errors:
        ...     for error in errors:
        ...         print(f"❌ {error}")
    """
    errors: List[ConfigError] = []

    # Check required top-level fields
    if "version" not in config:
        errors.append(ConfigError("version", "Missing required field"))
    elif config["version"] not in SUPPORTED_VERSIONS:
        errors.append(
            ConfigError(
                "version",
                f"Unsupported version (supported: {SUPPORTED_VERSIONS})",
                config["version"],
            )
        )

    if "workflow" not in config:
        errors.append(ConfigError("workflow", "Missing required field"))
    elif config["workflow"] not in VALID_WORKFLOWS:
        errors.append(
            ConfigError(
                "workflow",
                f"Invalid workflow type (valid: {VALID_WORKFLOWS})",
                config["workflow"],
            )
        )

    # Workflow-specific validation
    workflow = config.get("workflow")

    if workflow == "blend_batch":
        errors.extend(_validate_blend_batch(config))
    elif workflow == "download_batch":
        errors.extend(_validate_download_batch(config))
    elif workflow == "upload_batch":
        errors.extend(_validate_upload_batch(config))
    elif workflow == "full_pipeline":
        errors.extend(_validate_full_pipeline(config))

    if errors:
        logger.warning(f"Configuration validation failed with {len(errors)} errors")
    else:
        logger.info("✓ Configuration validation passed")

    return errors


def _validate_blend_batch(config: Dict[str, Any]) -> List[ConfigError]:
    """Validate blend_batch workflow configuration."""
    errors: List[ConfigError] = []

    if "blends" not in config:
        errors.append(ConfigError("blends", "Missing required field for blend_batch"))
        return errors

    blends = config["blends"]
    if not isinstance(blends, list):
        errors.append(ConfigError("blends", "Must be a list", type(blends).__name__))
        return errors

    if len(blends) == 0:
        errors.append(ConfigError("blends", "Must contain at least one blend"))

    # Validate each blend
    for i, blend in enumerate(blends):
        prefix = f"blends[{i}]"

        # Required fields
        for field in ["input1", "input2", "output"]:
            if field not in blend:
                errors.append(ConfigError(f"{prefix}.{field}", "Missing required field"))

        # Optional ratio validation
        if "ratio" in blend:
            ratio = blend["ratio"]
            if not isinstance(ratio, (int, float)):
                errors.append(
                    ConfigError(f"{prefix}.ratio", "Must be a number", type(ratio).__name__)
                )
            elif not 0.0 <= ratio <= 1.0:
                errors.append(ConfigError(f"{prefix}.ratio", "Must be between 0.0 and 1.0", ratio))

        # Optional method validation
        if "method" in blend:
            method = blend["method"]
            if method not in VALID_BLEND_METHODS:
                errors.append(
                    ConfigError(
                        f"{prefix}.method",
                        f"Invalid method (valid: {VALID_BLEND_METHODS})",
                        method,
                    )
                )

    return errors


def _validate_download_batch(config: Dict[str, Any]) -> List[ConfigError]:
    """Validate download_batch workflow configuration."""
    errors: List[ConfigError] = []

    if "downloads" not in config:
        errors.append(ConfigError("downloads", "Missing required field for download_batch"))
        return errors

    downloads = config["downloads"]
    if not isinstance(downloads, list):
        errors.append(ConfigError("downloads", "Must be a list", type(downloads).__name__))
        return errors

    if len(downloads) == 0:
        errors.append(ConfigError("downloads", "Must contain at least one download"))

    # Validate each download
    for i, download in enumerate(downloads):
        prefix = f"downloads[{i}]"

        for field in ["animation_id", "output"]:
            if field not in download:
                errors.append(ConfigError(f"{prefix}.{field}", "Missing required field"))

        # Optional format validation
        if "format" in download:
            fmt = download["format"]
            if fmt not in ["fbx", "bvh"]:
                errors.append(
                    ConfigError(f"{prefix}.format", "Invalid format (valid: fbx, bvh)", fmt)
                )

    return errors


def _validate_upload_batch(config: Dict[str, Any]) -> List[ConfigError]:
    """Validate upload_batch workflow configuration."""
    errors: List[ConfigError] = []

    if "uploads" not in config:
        errors.append(ConfigError("uploads", "Missing required field for upload_batch"))
        return errors

    uploads = config["uploads"]
    if not isinstance(uploads, list):
        errors.append(ConfigError("uploads", "Must be a list", type(uploads).__name__))
        return errors

    if len(uploads) == 0:
        errors.append(ConfigError("uploads", "Must contain at least one upload"))

    # Validate each upload
    for i, upload in enumerate(uploads):
        prefix = f"uploads[{i}]"

        if "file" not in upload:
            errors.append(ConfigError(f"{prefix}.file", "Missing required field"))

        # Optional folder validation
        if "folder" in upload and not isinstance(upload["folder"], str):
            errors.append(
                ConfigError(
                    f"{prefix}.folder", "Must be a string", type(upload["folder"]).__name__
                )
            )

    return errors


def _validate_full_pipeline(config: Dict[str, Any]) -> List[ConfigError]:
    """Validate full_pipeline workflow configuration."""
    errors: List[ConfigError] = []

    # Full pipeline requires download, blend, and upload sections
    if "download" not in config:
        errors.append(ConfigError("download", "Missing required field for full_pipeline"))

    if "blend" not in config:
        errors.append(ConfigError("blend", "Missing required field for full_pipeline"))

    if "upload" not in config:
        errors.append(ConfigError("upload", "Missing required field for full_pipeline"))

    return errors


def get_config_examples() -> Dict[str, str]:
    """
    Get example configuration templates.

    Returns:
        Dictionary mapping example names to YAML templates

    Example:
        >>> examples = get_config_examples()
        >>> print(examples["blend_batch"])
    """
    examples = {
        "blend_batch": """version: "1.0"
workflow: blend_batch

blends:
  - name: walk_to_run
    input1: seed/walk.bvh
    input2: seed/run.bvh
    ratio: 0.5
    method: linear
    output: blend/walk_run.bvh

  - name: idle_to_jump
    input1: seed/idle.bvh
    input2: seed/jump.bvh
    ratio: 0.3
    method: snn
    output: blend/idle_jump.bvh

upload:
  folder: blend/
  metadata:
    source: mixamo
    pipeline: batch
""",
        "download_batch": """version: "1.0"
workflow: download_batch

downloads:
  - animation_id: "123456"
    output: seed/walk.fbx
    format: fbx

  - animation_id: "123457"
    output: seed/run.fbx
    format: fbx

  - animation_id: "123458"
    output: seed/jump.bvh
    format: bvh
""",
        "upload_batch": """version: "1.0"
workflow: upload_batch

uploads:
  - file: blend/walk_run.bvh
    folder: blend/
    metadata:
      source: mixamo
      method: linear

  - file: blend/idle_jump.bvh
    folder: blend/
    metadata:
      source: mixamo
      method: snn
""",
    }

    return examples
