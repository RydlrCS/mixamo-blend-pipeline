"""
Google Cloud Storage uploader module.

Provides functions for uploading animation files to GCS buckets with proper
metadata, error handling, and progress tracking. Organizes files into
structured folders (seed/, build/, blend/) for pipeline processing.
"""

from .uploader import (
    UploadConfig,
    UploadResult,
    upload_file,
    upload_batch,
    validate_gcs_path,
)

__all__ = [
    "UploadConfig",
    "UploadResult",
    "upload_file",
    "upload_batch",
    "validate_gcs_path",
]
