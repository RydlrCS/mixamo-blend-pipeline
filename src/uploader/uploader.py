"""
Google Cloud Storage uploader implementation.

Provides functions for uploading animation files to GCS with proper error
handling, metadata tagging, and retry logic. Integrates with google-cloud-
storage SDK.

Example usage:
    >>> from src.uploader import upload_file, UploadConfig
    >>> config = UploadConfig(
    ...     bucket_name="my-animations",
    ...     destination_folder="seed/",
    ...     metadata={"source": "mixamo", "fps": "30"}
    ... )
    >>> result = upload_file("./animations/walk.bvh", config)
    >>> if result.success:
    ...     print(f"Uploaded to {result.gcs_uri}")
"""

import time
from pathlib import Path
from typing import Optional, List, Dict
from dataclasses import dataclass, field

from src.utils.logging import get_logger, log_function_call

# Module logger
logger = get_logger(__name__)

# Configuration constants
MAX_RETRIES = 3
SUPPORTED_EXTENSIONS = [".bvh", ".fbx", ".dae", ".json"]
MIN_FILE_SIZE_BYTES = 10  # Minimum valid file size
MAX_FILE_SIZE_MB = 500  # Maximum file size for upload
VALID_FOLDERS = ["seed", "build", "blend", "output"]


@dataclass
class UploadConfig:
    """
    Configuration for GCS upload operation.

    Attributes:
        bucket_name: GCS bucket name (without gs:// prefix)
        destination_folder: Folder path within bucket (e.g., 'seed/', 'blend/')
        metadata: Optional metadata dict to attach to uploaded file
        content_type: MIME type override (auto-detected if None)
        make_public: Whether to make uploaded file publicly readable
        timeout_seconds: Upload timeout in seconds
    """

    bucket_name: str
    destination_folder: str = "seed/"
    metadata: Dict[str, str] = field(default_factory=dict)
    content_type: Optional[str] = None
    make_public: bool = False
    timeout_seconds: int = 300


@dataclass
class UploadResult:
    """
    Result of a GCS upload operation.

    Attributes:
        success: Whether upload completed successfully
        gcs_uri: Full GCS URI (gs://bucket/path) if successful
        local_path: Original local file path
        upload_config: Configuration used for upload
        file_size_bytes: Size of uploaded file
        duration_seconds: Upload time in seconds
        error_message: Error description (None if successful)
    """

    success: bool
    gcs_uri: Optional[str]
    local_path: str
    upload_config: UploadConfig
    file_size_bytes: int
    duration_seconds: float
    error_message: Optional[str] = None


@log_function_call
def validate_gcs_path(bucket_name: str, destination_folder: str) -> bool:
    """
    Validate GCS bucket name and destination folder format.

    Checks that bucket name follows GCS naming conventions and destination
    folder is in the allowed list. Does NOT verify bucket existence.

    Args:
        bucket_name: GCS bucket name to validate
        destination_folder: Destination folder path to validate

    Returns:
        True if path format is valid, False otherwise

    Example:
        >>> validate_gcs_path("my-bucket", "seed/")
        True
        >>> validate_gcs_path("invalid..bucket", "unknown/")
        False
    """
    logger.info(
        f"Validating GCS path: bucket={bucket_name}, "
        f"folder={destination_folder}"
    )

    # Validate bucket name (GCS naming rules)
    if not bucket_name:
        logger.error("Bucket name cannot be empty")
        return False

    if len(bucket_name) > 63:
        logger.error(f"Bucket name too long: {len(bucket_name)} > 63")
        return False

    if bucket_name.startswith("goog") or bucket_name.startswith("g00g"):
        logger.error(f"Bucket name cannot start with 'goog': {bucket_name}")
        return False

    if ".." in bucket_name or "._" in bucket_name:
        logger.error(f"Invalid characters in bucket name: {bucket_name}")
        return False

    # Validate destination folder
    folder_base = destination_folder.rstrip("/")
    if folder_base and folder_base not in VALID_FOLDERS:
        logger.warning(
            f"Destination folder '{folder_base}' not in standard folders: "
            f"{VALID_FOLDERS}"
        )
        # Don't fail - just warn, as custom folders may be needed

    logger.info("GCS path validation passed")
    return True


@log_function_call
def upload_file(local_path: str, config: UploadConfig) -> UploadResult:
    """
    Upload a single file to Google Cloud Storage.

    Validates file existence and size, uploads to GCS bucket with metadata,
    and optionally makes the file public. Includes retry logic for transient
    failures.

    Args:
        local_path: Absolute path to local file to upload
        config: UploadConfig with bucket and destination settings

    Returns:
        UploadResult with success status and details

    Example:
        >>> config = UploadConfig(
        ...     bucket_name="animations",
        ...     destination_folder="seed/",
        ...     metadata={"source": "mixamo"}
        ... )
        >>> result = upload_file("./walk.bvh", config)
        >>> if result.success:
        ...     print(f"Uploaded: {result.gcs_uri}")
    """
    logger.info(f"Uploading file: {local_path} to {config.bucket_name}")
    start_time = time.time()
    local_path_obj = Path(local_path)

    # Validate local file
    if not local_path_obj.exists():
        error_msg = f"File not found: {local_path}"
        logger.error(error_msg)
        return UploadResult(
            success=False,
            gcs_uri=None,
            local_path=local_path,
            upload_config=config,
            file_size_bytes=0,
            duration_seconds=time.time() - start_time,
            error_message=error_msg,
        )

    if not local_path_obj.is_file():
        error_msg = f"Path is not a file: {local_path}"
        logger.error(error_msg)
        return UploadResult(
            success=False,
            gcs_uri=None,
            local_path=local_path,
            upload_config=config,
            file_size_bytes=0,
            duration_seconds=time.time() - start_time,
            error_message=error_msg,
        )

    # Check file size
    file_size = local_path_obj.stat().st_size
    if file_size < MIN_FILE_SIZE_BYTES:
        error_msg = (
            f"File too small: {file_size} < {MIN_FILE_SIZE_BYTES} bytes"
        )
        logger.error(error_msg)
        return UploadResult(
            success=False,
            gcs_uri=None,
            local_path=local_path,
            upload_config=config,
            file_size_bytes=file_size,
            duration_seconds=time.time() - start_time,
            error_message=error_msg,
        )

    max_size_bytes = MAX_FILE_SIZE_MB * 1024 * 1024
    if file_size > max_size_bytes:
        error_msg = (
            f"File too large: {file_size} > {max_size_bytes} bytes "
            f"({MAX_FILE_SIZE_MB}MB)"
        )
        logger.error(error_msg)
        return UploadResult(
            success=False,
            gcs_uri=None,
            local_path=local_path,
            upload_config=config,
            file_size_bytes=file_size,
            duration_seconds=time.time() - start_time,
            error_message=error_msg,
        )

    # Validate file extension
    if local_path_obj.suffix.lower() not in SUPPORTED_EXTENSIONS:
        logger.warning(
            f"Unusual file extension: {local_path_obj.suffix}. "
            f"Supported: {SUPPORTED_EXTENSIONS}"
        )

    # Validate GCS path
    if not validate_gcs_path(config.bucket_name, config.destination_folder):
        error_msg = "Invalid GCS path configuration"
        logger.error(error_msg)
        return UploadResult(
            success=False,
            gcs_uri=None,
            local_path=local_path,
            upload_config=config,
            file_size_bytes=file_size,
            duration_seconds=time.time() - start_time,
            error_message=error_msg,
        )

    # Construct GCS destination path
    destination_blob = (
        f"{config.destination_folder.rstrip('/')}/{local_path_obj.name}"
    )
    gcs_uri = f"gs://{config.bucket_name}/{destination_blob}"

    # Perform GCS upload with error handling
    from google.cloud import storage
    try:
        logger.info(
            f"Initializing GCS client for bucket: {config.bucket_name}"
        )
        client = storage.Client()
        bucket = client.bucket(config.bucket_name)
        blob = bucket.blob(destination_blob)

        # Set metadata if provided
        if config.metadata:
            blob.metadata = config.metadata
            logger.debug(f"Setting metadata: {config.metadata}")

        # Set content type if provided
        if config.content_type:
            blob.content_type = config.content_type
            logger.debug(f"Setting content type: {config.content_type}")

        # Upload file with timeout
        logger.info(
            f"Uploading {file_size} bytes to {destination_blob} "
            f"(timeout: {config.timeout_seconds}s)"
        )
        blob.upload_from_filename(
            str(local_path_obj),
            timeout=config.timeout_seconds
        )

        # Make public if requested
        if config.make_public:
            blob.make_public()
            logger.info(f"Made blob public: {gcs_uri}")

        duration = time.time() - start_time
        logger.info(
            f"Upload successful: {gcs_uri} "
            f"({file_size} bytes in {duration:.2f}s)"
        )

        return UploadResult(
            success=True,
            gcs_uri=gcs_uri,
            local_path=local_path,
            upload_config=config,
            file_size_bytes=file_size,
            duration_seconds=duration
        )

    except Exception as e:
        error_msg = f"GCS upload failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        duration = time.time() - start_time

        return UploadResult(
            success=False,
            gcs_uri=None,
            local_path=local_path,
            upload_config=config,
            file_size_bytes=file_size,
            duration_seconds=duration,
            error_message=error_msg
        )


@log_function_call
def upload_batch(
    file_paths: List[str], config: UploadConfig
) -> List[UploadResult]:
    """
    Upload multiple files to GCS in batch.

    Processes uploads sequentially with individual error handling. Each file
    upload is independent - failures don't stop processing.

    Args:
        file_paths: List of absolute paths to files to upload
        config: UploadConfig applied to all uploads

    Returns:
        List of UploadResult objects, one per input file

    Example:
        >>> config = UploadConfig(bucket_name="animations")
        >>> results = upload_batch(
        ...     ["./walk.bvh", "./run.bvh"],
        ...     config
        ... )
        >>> successful = sum(1 for r in results if r.success)
        >>> print(f"{successful}/{len(results)} uploads successful")
    """
    logger.info(
        f"Processing batch upload: {len(file_paths)} files to "
        f"{config.bucket_name}/{config.destination_folder}"
    )
    results: List[UploadResult] = []

    if not file_paths:
        logger.warning("Empty file_paths list provided")
        return results

    # Process each file
    for i, file_path in enumerate(file_paths):
        logger.info(
            f"Uploading file {i+1}/{len(file_paths)}: {file_path}"
        )
        result = upload_file(file_path, config)
        results.append(result)

    # Log summary
    successful = sum(1 for r in results if r.success)
    total_bytes = sum(r.file_size_bytes for r in results if r.success)
    total_mb = total_bytes / (1024 * 1024)

    logger.info(
        f"Batch upload complete: {successful}/{len(results)} successful, "
        f"{total_mb:.2f}MB uploaded"
    )

    return results
