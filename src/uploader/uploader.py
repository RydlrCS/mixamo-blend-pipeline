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
from src.utils.retry import retry_with_backoff, CircuitBreaker
from src.utils.metrics import get_metrics

# Module logger
logger = get_logger(__name__)

# Module metrics
metrics = get_metrics()

# Circuit breaker for GCS operations (fail fast if GCS is down)
gcs_circuit_breaker = CircuitBreaker(
    failure_threshold=5,
    timeout=60.0,
    expected_exception=Exception,
)

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

    # Perform GCS upload with error handling, retry, and metrics
    try:
        # Track upload with metrics
        with metrics.track_upload():
            # Use retry decorator for resilient uploads
            _perform_gcs_upload(
                local_path_obj=local_path_obj,
                config=config,
                destination_blob=destination_blob,
                file_size=file_size,
            )

        duration = time.time() - start_time
        logger.info(
            f"Upload successful: {gcs_uri} "
            f"({file_size} bytes in {duration:.2f}s)"
        )

        # Record success metrics
        folder = config.destination_folder.rstrip('/').split('/')[-1] or 'root'
        metrics.record_upload_success(
            bytes_uploaded=file_size,
            destination=folder
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

        # Record failure metrics
        folder = config.destination_folder.rstrip('/').split('/')[-1] or 'root'
        metrics.record_upload_failure(destination=folder)
        
        # Record GCS error metrics
        error_type = type(e).__name__
        metrics.record_gcs_error(operation="upload", error_type=error_type)

        return UploadResult(
            success=False,
            gcs_uri=None,
            local_path=local_path,
            upload_config=config,
            file_size_bytes=file_size,
            duration_seconds=duration,
            error_message=error_msg
        )


@retry_with_backoff(
    max_attempts=MAX_RETRIES,
    base_delay=2.0,
    max_delay=30.0,
    backoff_multiplier=2.0,
    jitter=True,
    exceptions=(Exception,),
)
@gcs_circuit_breaker
def _perform_gcs_upload(
    local_path_obj: Path,
    config: UploadConfig,
    destination_blob: str,
    file_size: int,
) -> None:
    """
    Internal function to perform GCS upload with retry logic.
    
    This function is decorated with retry_with_backoff and circuit_breaker
    to provide resilient uploads with exponential backoff.
    
    Args:
        local_path_obj: Path object for local file
        config: Upload configuration
        destination_blob: GCS blob destination path
        file_size: File size in bytes
    
    Raises:
        Exception: If upload fails after all retries
    
    Note:
        This function is internal and should not be called directly.
        Use upload_file() instead.
    """
    from google.cloud import storage
    
    logger.debug(
        f"Executing GCS upload: {local_path_obj.name} -> {destination_blob}"
    )
    
    # Initialize GCS client and perform upload
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
    
    # Track GCS API duration
    with metrics.gcs_api_duration.labels(operation="upload").time():
        blob.upload_from_filename(
            str(local_path_obj),
            timeout=config.timeout_seconds
        )

    # Make public if requested
    if config.make_public:
        blob.make_public()
        logger.info(f"Made blob public: {destination_blob}")


@log_function_call
def upload_file(local_path: str, config: UploadConfig) -> UploadResult:
    """
    Upload a single file to Google Cloud Storage.

    Validates file existence and size, uploads to GCS bucket with metadata,
    and optionally makes the file public. Includes retry logic for transient
    failures with exponential backoff and circuit breaker protection.

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
    
    Note:
        - Automatically retries on transient failures (up to MAX_RETRIES times)
        - Uses exponential backoff with jitter to prevent thundering herd
        - Circuit breaker protects against cascading failures when GCS is down
        - Comprehensive metrics tracking for monitoring and alerting
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

    # Log summary
    successful = sum(1 for r in results if r.success)
    total_bytes = sum(r.file_size_bytes for r in results if r.success)
    total_mb = total_bytes / (1024 * 1024)

    logger.info(
        f"Batch upload complete: {successful}/{len(results)} successful, "
        f"{total_mb:.2f}MB uploaded"
    )

    return results
