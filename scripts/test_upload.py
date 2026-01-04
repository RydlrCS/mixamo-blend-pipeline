#!/usr/bin/env python3
"""
Quick test script to verify GCS upload configuration.

Usage:
    python scripts/test_upload.py <file_path>
"""

import sys
from pathlib import Path

# Add src to path before imports
_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from src.utils.config import get_config  # noqa: E402
from src.uploader import upload_file, UploadConfig  # noqa: E402


def main():
    """Test GCS upload with environment configuration."""
    if len(sys.argv) < 2:
        print("Usage: python scripts/test_upload.py <file_path>")
        print("\nExample:")
        print("  python scripts/test_upload.py data/sample.bvh")
        sys.exit(1)

    file_path = sys.argv[1]

    # Load environment configuration
    try:
        config = get_config()
        print(f"✓ Configuration loaded:")
        print(f"  GCS Bucket: {config.gcs_bucket}")
        print(f"  BQ Project: {config.bq_project}")
        print(f"  BQ Dataset: {config.bq_dataset}")
        if config.elasticsearch_url:
            print(f"  Elasticsearch: {config.elasticsearch_url}")
        print()
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        print("\nMake sure .env file exists with required variables:")
        print("  - GCS_BUCKET")
        print("  - BQ_PROJECT")
        print("  - BQ_DATASET")
        sys.exit(1)

    # Create upload config
    upload_config = UploadConfig(
        bucket_name=config.gcs_bucket,
        destination_folder="seed/",
        metadata={
            "source": "test-script",
            "project": config.bq_project,
        },
        timeout_seconds=config.upload_timeout_seconds,
    )

    # Upload file
    print(f"Uploading: {file_path}")
    print(f"Destination: gs://{config.gcs_bucket}/seed/")
    print()

    result = upload_file(file_path, upload_config)

    if result.success:
        print(f"✅ Upload successful!")
        print(f"  GCS URI: {result.gcs_uri}")
        print(f"  File size: {result.file_size_bytes:,} bytes")
        print(f"  Duration: {result.duration_seconds:.2f}s")
    else:
        print(f"❌ Upload failed:")
        print(f"  Error: {result.error_message}")
        sys.exit(1)


if __name__ == "__main__":
    main()
