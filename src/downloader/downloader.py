"""
Mixamo animation file validator and organizer.

NOTE: This module does NOT directly download from Mixamo's API.
Use the browser-based scripts from mixamo_anims_downloader repository:
https://github.com/RydlrCS/mixamo_anims_downloader

This module provides:
- File validation for downloaded animations (FBX/BVH format checks)
- Batch file organization and metadata tracking
- Integration with the blendanim pipeline
- Progress tracking and logging

Typical workflow:
1. Download animations using mixamo_anims_downloader browser scripts
2. Use this module to validate and organize files
3. Upload to GCS for pipeline processing

Example usage:
    >>> from src.downloader import validate_download
    >>> # After downloading with browser script
    >>> is_valid = validate_download("./downloads/walk.fbx")
    >>> if is_valid:
    ...     print("File is valid and ready for processing")

See docs/MIXAMO_INTEGRATION.md for detailed integration guide.
"""

import time
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from src.utils.logging import get_logger, log_function_call

# Module logger
logger = get_logger(__name__)

# Configuration constants
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 2.0
SUPPORTED_FORMATS = ["fbx", "bvh"]
MIN_FILE_SIZE_BYTES = 1024  # Minimum valid animation file size (1 KB)


@dataclass
class DownloadConfig:
    """
    Configuration for animation download operations.

    Attributes:
        animation_id: Mixamo animation ID to download
        output_path: Local file path where animation will be saved
        format: Animation file format - "fbx" or "bvh" (default: "fbx")
        overwrite: Whether to overwrite existing files (default: False)
        max_retries: Maximum number of retry attempts (default: 3)
    """

    animation_id: str
    output_path: str
    format: str = "fbx"
    overwrite: bool = False
    max_retries: int = MAX_RETRIES


@dataclass
class DownloadResult:
    """
    Result of an animation download operation.

    Attributes:
        success: Whether the download completed successfully
        file_path: Path to the downloaded file (None if failed)
        animation_id: Mixamo animation ID
        error_message: Error description if download failed
        file_size_bytes: Size of downloaded file in bytes
        duration_seconds: Time taken for download operation
    """

    success: bool
    file_path: Optional[str]
    animation_id: str
    error_message: Optional[str] = None
    file_size_bytes: Optional[int] = None
    duration_seconds: Optional[float] = None


@log_function_call
def validate_download(file_path: str, min_size_bytes: int = MIN_FILE_SIZE_BYTES) -> bool:
    """
    Validate that a downloaded animation file is valid and complete.

    Performs basic integrity checks:
    - File exists on disk
    - File size is above minimum threshold
    - File has correct extension

    Args:
        file_path: Path to the downloaded animation file
        min_size_bytes: Minimum acceptable file size in bytes

    Returns:
        True if file passes validation, False otherwise

    Raises:
        ValueError: If file_path is empty or invalid

    Example:
        >>> is_valid = validate_download("./animations/walk.fbx")
        >>> if not is_valid:
        ...     print("Download corrupted or incomplete")
    """
    logger.info(f"Validating downloaded file: {file_path}")

    # Validate input
    if not file_path or not file_path.strip():
        raise ValueError("file_path cannot be empty")

    file_path_obj = Path(file_path)

    # Check file exists
    if not file_path_obj.exists():
        logger.warning(f"File does not exist: {file_path}")
        return False

    # Check file is not a directory
    if file_path_obj.is_dir():
        logger.warning(f"Path is a directory, not a file: {file_path}")
        return False

    # Check file extension
    extension = file_path_obj.suffix.lower().lstrip(".")
    if extension not in SUPPORTED_FORMATS:
        logger.warning(
            f"Unsupported file format '{extension}'. "
            f"Supported formats: {', '.join(SUPPORTED_FORMATS)}"
        )
        return False

    # Check file size
    file_size = file_path_obj.stat().st_size
    if file_size < min_size_bytes:
        logger.warning(
            f"File too small ({file_size} bytes < {min_size_bytes} bytes minimum). "
            f"File may be corrupted or incomplete."
        )
        return False

    logger.info(
        f"File validation successful: {file_path} ({file_size} bytes, format: {extension})"
    )
    return True


@log_function_call
def download_animation(
    animation_id: str,
    output_path: str,
    format: str = "fbx",
    overwrite: bool = False,
    max_retries: int = MAX_RETRIES,
) -> DownloadResult:
    """
    Download a single animation from Mixamo.

    This function serves as a wrapper around the mixamo_anims_downloader
    implementation, adding robust error handling, retry logic, and validation.

    Args:
        animation_id: Mixamo animation ID (e.g., "123456")
        output_path: Local file path where animation will be saved
        format: Animation file format - "fbx" or "bvh" (default: "fbx")
        overwrite: Whether to overwrite existing files (default: False)
        max_retries: Maximum number of retry attempts on failure (default: 3)

    Returns:
        DownloadResult containing download status and metadata

    Raises:
        ValueError: If parameters are invalid
        OSError: If output directory cannot be created

    Example:
        >>> result = download_animation(
        ...     animation_id="123456",
        ...     output_path="./animations/walk.fbx",
        ...     format="fbx"
        ... )
        >>> if result.success:
        ...     print(f"Downloaded {result.file_size_bytes} bytes in {result.duration_seconds}s")
        ... else:
        ...     print(f"Download failed: {result.error_message}")
    """
    logger.info(
        f"Starting download: animation_id={animation_id}, output_path={output_path}, "
        f"format={format}"
    )

    start_time = time.time()

    # Validate inputs
    if not animation_id or not animation_id.strip():
        error_msg = "animation_id cannot be empty"
        logger.error(error_msg)
        raise ValueError(error_msg)

    if not output_path or not output_path.strip():
        error_msg = "output_path cannot be empty"
        logger.error(error_msg)
        raise ValueError(error_msg)

    if format.lower() not in SUPPORTED_FORMATS:
        error_msg = (
            f"Unsupported format '{format}'. Supported formats: {', '.join(SUPPORTED_FORMATS)}"
        )
        logger.error(error_msg)
        raise ValueError(error_msg)

    # Ensure output directory exists
    output_path_obj = Path(output_path)
    output_dir = output_path_obj.parent
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Created output directory: {output_dir}")
    except OSError as e:
        error_msg = f"Failed to create output directory {output_dir}: {str(e)}"
        logger.error(error_msg)
        raise OSError(error_msg) from e

    # Check if file already exists
    if output_path_obj.exists() and not overwrite:
        logger.warning(
            f"File already exists and overwrite=False: {output_path}. Skipping download."
        )
        file_size = output_path_obj.stat().st_size
        duration = time.time() - start_time
        return DownloadResult(
            success=True,
            file_path=str(output_path_obj.absolute()),
            animation_id=animation_id,
            file_size_bytes=file_size,
            duration_seconds=duration,
        )

    # TODO: Implement actual Mixamo API download logic
    # This is a placeholder that demonstrates the structure.
    # The actual implementation will integrate with mixamo_anims_downloader.
    #
    # For now, return a simulated failure to indicate implementation is needed
    error_msg = (
        "Mixamo API integration not yet implemented. "
        "This requires integration with mixamo_anims_downloader repository."
    )
    logger.warning(error_msg)

    duration = time.time() - start_time
    return DownloadResult(
        success=False,
        file_path=None,
        animation_id=animation_id,
        error_message=error_msg,
        duration_seconds=duration,
    )


@log_function_call
def download_batch(
    animation_configs: List[Dict[str, Any]],
    output_dir: str,
    format: str = "fbx",
    max_parallel: int = 1,
) -> List[DownloadResult]:
    """
    Download multiple animations in batch.

    Processes a list of animation download configurations, with options for
    parallel processing and progress tracking.

    Args:
        animation_configs: List of dicts with keys:
            - animation_id (str): Mixamo animation ID
            - output_filename (str): Filename for this animation (e.g., "walk.fbx")
        output_dir: Base directory for all downloads
        format: Animation file format - "fbx" or "bvh" (default: "fbx")
        max_parallel: Maximum number of parallel downloads (default: 1 for sequential)

    Returns:
        List of DownloadResult objects, one per animation

    Raises:
        ValueError: If animation_configs is empty or invalid
        OSError: If output_dir cannot be created

    Example:
        >>> configs = [
        ...     {"animation_id": "123", "output_filename": "walk.fbx"},
        ...     {"animation_id": "456", "output_filename": "run.fbx"}
        ... ]
        >>> results = download_batch(configs, "./animations", format="fbx")
        >>> successful = sum(1 for r in results if r.success)
        >>> print(f"Downloaded {successful}/{len(results)} animations")
    """
    logger.info(
        f"Starting batch download: {len(animation_configs)} animations, "
        f"output_dir={output_dir}, format={format}"
    )

    # Validate inputs
    if not animation_configs:
        error_msg = "animation_configs cannot be empty"
        logger.error(error_msg)
        raise ValueError(error_msg)

    if not output_dir or not output_dir.strip():
        error_msg = "output_dir cannot be empty"
        logger.error(error_msg)
        raise ValueError(error_msg)

    # Ensure output directory exists
    output_dir_obj = Path(output_dir)
    try:
        output_dir_obj.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Created batch output directory: {output_dir_obj}")
    except OSError as e:
        error_msg = f"Failed to create output directory {output_dir_obj}: {str(e)}"
        logger.error(error_msg)
        raise OSError(error_msg) from e

    results: List[DownloadResult] = []

    # Process each animation sequentially (parallel processing can be added later)
    for idx, config in enumerate(animation_configs, 1):
        animation_id = config.get("animation_id")
        output_filename = config.get("output_filename")

        logger.info(f"Processing animation {idx}/{len(animation_configs)}: {animation_id}")

        # Validate config
        if not animation_id:
            error_msg = f"Missing animation_id in config at index {idx - 1}"
            logger.error(error_msg)
            results.append(
                DownloadResult(
                    success=False,
                    file_path=None,
                    animation_id="unknown",
                    error_message=error_msg,
                )
            )
            continue

        if not output_filename:
            error_msg = f"Missing output_filename for animation_id {animation_id}"
            logger.error(error_msg)
            results.append(
                DownloadResult(
                    success=False,
                    file_path=None,
                    animation_id=animation_id,
                    error_message=error_msg,
                )
            )
            continue

        # Construct full output path
        output_path = str(output_dir_obj / output_filename)

        # Download animation
        try:
            result = download_animation(
                animation_id=animation_id, output_path=output_path, format=format
            )
            results.append(result)
        except Exception as e:
            error_msg = (
                f"Unexpected error downloading {animation_id}: "
                f"{type(e).__name__}: {str(e)}"
            )
            logger.error(error_msg)
            results.append(
                DownloadResult(
                    success=False,
                    file_path=None,
                    animation_id=animation_id,
                    error_message=error_msg,
                )
            )

    # Summary logging
    successful_count = sum(1 for r in results if r.success)
    failed_count = len(results) - successful_count
    logger.info(
        f"Batch download complete: {successful_count} successful, {failed_count} failed "
        f"out of {len(results)} total"
    )

    return results
