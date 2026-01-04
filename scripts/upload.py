#!/usr/bin/env python3
"""
Upload animation files to Google Cloud Storage.

CLI wrapper for the uploader module providing command-line access to
GCS upload functionality with environment-based configuration.

Usage:
    python scripts/upload.py file.bvh
    python scripts/upload.py animation.bvh --folder seed/
    python scripts/upload.py *.bvh --folder blend/ --metadata source=mixamo
    python scripts/upload.py walk.fbx --public
"""

import argparse
import sys
from pathlib import Path
from typing import List

# Add src to path for imports (before other imports)
_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from src.uploader import upload_file, upload_batch, UploadConfig  # noqa: E402
from src.utils.config import get_config  # noqa: E402
from src.utils.logging import get_logger  # noqa: E402

logger = get_logger(__name__)


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Upload animation files to Google Cloud Storage",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Upload single file to seed/ folder
  %(prog)s animation.bvh

  # Upload to specific GCS folder
  %(prog)s blended.bvh --folder blend/

  # Upload multiple files
  %(prog)s walk.bvh run.bvh jump.bvh

  # Upload with metadata
  %(prog)s file.bvh --metadata source=mixamo fps=30

  # Make uploaded file publicly accessible
  %(prog)s public_anim.bvh --public

  # Batch upload all BVH files
  %(prog)s *.bvh --folder output/
        """,
    )

    parser.add_argument(
        "files",
        nargs="+",
        help="File(s) to upload (supports glob patterns)",
    )

    parser.add_argument(
        "-f",
        "--folder",
        default="seed/",
        help="GCS destination folder (default: seed/)",
    )

    parser.add_argument(
        "-m",
        "--metadata",
        action="append",
        help="Metadata key=value pairs (can specify multiple times)",
    )

    parser.add_argument(
        "-p",
        "--public",
        action="store_true",
        help="Make uploaded files publicly accessible",
    )

    parser.add_argument(
        "-t",
        "--timeout",
        type=int,
        help="Upload timeout in seconds (default: from config)",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )

    return parser.parse_args()


def parse_metadata(metadata_args: List[str]) -> dict:
    """Parse metadata arguments into dictionary."""
    if not metadata_args:
        return {}

    metadata = {}
    for item in metadata_args:
        if "=" not in item:
            logger.warning(f"Invalid metadata format (use key=value): {item}")
            continue

        key, value = item.split("=", 1)
        metadata[key.strip()] = value.strip()

    return metadata


def main():
    """Main entry point for upload CLI."""
    args = parse_args()

    # Configure logging verbosity
    if args.verbose:
        import logging

        logging.getLogger("src.uploader").setLevel(logging.DEBUG)

    # Load environment configuration
    try:
        env_config = get_config()
        logger.info(f"Using GCS bucket: {env_config.gcs_bucket}")
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        print("\nMake sure .env file exists with required variables:")
        print("  - GCS_BUCKET")
        print("  - BQ_PROJECT")
        print("  - BQ_DATASET")
        return 1

    # Parse metadata
    metadata = parse_metadata(args.metadata or [])

    # Create upload configuration
    upload_config = UploadConfig(
        bucket_name=env_config.gcs_bucket,
        destination_folder=args.folder,
        metadata=metadata,
        make_public=args.public,
        timeout_seconds=(args.timeout if args.timeout else env_config.upload_timeout_seconds),
    )

    # Expand file patterns and validate
    files_to_upload = []
    for file_pattern in args.files:
        file_path = Path(file_pattern)

        # If path exists and is a file, add it
        if file_path.exists() and file_path.is_file():
            files_to_upload.append(str(file_path))
        else:
            print(f"⚠️  Skipping (not found or not a file): {file_pattern}")

    if not files_to_upload:
        print("❌ No valid files to upload")
        return 1

    print(f"📤 Uploading {len(files_to_upload)} file(s) to GCS")
    print(f"   Bucket: {env_config.gcs_bucket}")
    print(f"   Folder: {args.folder}")
    if metadata:
        print(f"   Metadata: {metadata}")
    print()

    try:
        # Upload files
        if len(files_to_upload) == 1:
            # Single file upload
            result = upload_file(files_to_upload[0], upload_config)

            if result.success:
                print(f"✅ Upload successful!")
                print(f"  GCS URI: {result.gcs_uri}")
                print(f"  File size: {result.file_size_bytes:,} bytes")
                print(f"  Duration: {result.duration_seconds:.2f}s")
                return 0
            else:
                print(f"❌ Upload failed:")
                print(f"  Error: {result.error_message}")
                return 1
        else:
            # Batch upload
            results = upload_batch(files_to_upload, upload_config)

            # Count successes/failures
            successful = sum(1 for r in results if r.success)
            failed = len(results) - successful

            # Display results
            print(f"\n📊 Batch Upload Summary:")
            print(f"  Total: {len(results)}")
            print(f"  ✅ Successful: {successful}")
            print(f"  ❌ Failed: {failed}")

            if successful > 0:
                total_bytes = sum(r.file_size_bytes for r in results if r.success)
                print(f"  📦 Total size: {total_bytes:,} bytes")

            # Show failed uploads
            if failed > 0:
                print(f"\n❌ Failed uploads:")
                for result in results:
                    if not result.success:
                        print(f"  • {Path(result.local_path).name}: " f"{result.error_message}")

            return 0 if failed == 0 else 1

    except KeyboardInterrupt:
        print("\n⚠️  Upload cancelled by user")
        return 130

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        print(f"❌ Unexpected error: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
