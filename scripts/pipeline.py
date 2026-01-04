#!/usr/bin/env python3
"""
End-to-end animation pipeline orchestrator.

Combines download → blend → upload workflow into a single automated pipeline
with configuration-driven execution and comprehensive error handling.

Usage:
    python scripts/pipeline.py --config pipeline.yaml
    python scripts/pipeline.py --download-only --character ybot --animation idle
    python scripts/pipeline.py --blend-only walk.bvh run.bvh
"""

import argparse
import sys
import time
from pathlib import Path
from typing import Optional

# Add src to path for imports (before other imports)
_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from src.downloader import download_animation, DownloadConfig  # noqa: E402
from src.blender import blend_animations, BlendConfig  # noqa: E402
from src.uploader import upload_file, UploadConfig  # noqa: E402
from src.utils.config import get_config  # noqa: E402
from src.utils.config_loader import load_config, validate_config  # noqa: E402
from src.utils.logging import get_logger  # noqa: E402

logger = get_logger(__name__)


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Mixamo animation pipeline orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full pipeline: download → blend → upload
  %(prog)s -c ybot -a1 idle -a2 walk -r 0.5

  # Download only
  %(prog)s --download-only -c ybot -a idle

  # Blend existing files
  %(prog)s --blend-only walk.bvh run.bvh -o blend.bvh

  # Download and blend (skip upload)
  %(prog)s -c ybot -a1 walk -a2 run --skip-upload

  # Use configuration file for batch processing
  %(prog)s --config config/examples/blend_batch.yaml

  # Full pipeline with custom output
  %(prog)s -c maximo -a1 idle -a2 jump -r 0.3 -o custom_blend.bvh
        """,
    )

    # Configuration file
    parser.add_argument(
        "--config",
        type=str,
        help="Path to YAML configuration file for batch processing",
    )

    # Pipeline control
    parser.add_argument(
        "--download-only",
        action="store_true",
        help="Only download animations (skip blend and upload)",
    )

    parser.add_argument(
        "--blend-only",
        action="store_true",
        help="Only blend animations (skip download and upload)",
    )

    parser.add_argument(
        "--skip-upload",
        action="store_true",
        help="Skip upload step (download and blend only)",
    )

    # Download arguments
    parser.add_argument(
        "-c",
        "--character",
        help="Character name for download",
    )

    parser.add_argument(
        "-a1",
        "--animation1",
        help="First animation name for download",
    )

    parser.add_argument(
        "-a2",
        "--animation2",
        help="Second animation name for download",
    )

    # Blend arguments
    parser.add_argument(
        "input_files",
        nargs="*",
        help="Input files for blend-only mode",
    )

    parser.add_argument(
        "-r",
        "--ratio",
        type=float,
        default=0.5,
        help="Blend ratio (0.0-1.0, default: 0.5)",
    )

    parser.add_argument(
        "-m",
        "--method",
        choices=["linear", "snn", "spade"],
        default="linear",
        help="Blending method (default: linear)",
    )

    # Output arguments
    parser.add_argument(
        "-o",
        "--output",
        help="Output file path (default: auto-generated)",
    )

    parser.add_argument(
        "--work-dir",
        default="./pipeline_work",
        help="Working directory for intermediate files",
    )

    # Upload arguments
    parser.add_argument(
        "--upload-folder",
        default="blend/",
        help="GCS upload destination folder (default: blend/)",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )

    return parser.parse_args()


def run_download_step(args, work_dir: Path) -> Optional[tuple]:
    """
    Execute download step of pipeline.

    Returns:
        Tuple of (file1_path, file2_path) if successful, None on error
    """
    if not args.character or not args.animation1:
        print("❌ Error: --character and --animation1 required for download")
        return None

    print("\n" + "=" * 60)
    print("STEP 1: DOWNLOAD ANIMATIONS")
    print("=" * 60)

    # Download first animation
    config1 = DownloadConfig(
        character_name=args.character,
        animation_name=args.animation1,
        output_dir=str(work_dir / "downloads"),
        file_format="bvh",
    )

    print(f"\nDownloading: {args.animation1}")
    result1 = download_animation(config1)

    if not result1.success:
        print(f"❌ Failed to download {args.animation1}")
        print(f"   Error: {result1.error_message}")
        return None

    print(f"✅ Downloaded: {result1.output_path}")
    file1_path = result1.output_path

    # Download second animation if specified
    file2_path = None
    if args.animation2:
        config2 = DownloadConfig(
            character_name=args.character,
            animation_name=args.animation2,
            output_dir=str(work_dir / "downloads"),
            file_format="bvh",
        )

        print(f"\nDownloading: {args.animation2}")
        result2 = download_animation(config2)

        if not result2.success:
            print(f"❌ Failed to download {args.animation2}")
            print(f"   Error: {result2.error_message}")
            return None

        print(f"✅ Downloaded: {result2.output_path}")
        file2_path = result2.output_path

    return (file1_path, file2_path)


def run_blend_step(args, work_dir: Path, input1: str, input2: str) -> Optional[str]:
    """
    Execute blend step of pipeline.

    Returns:
        Path to blended output file if successful, None on error
    """
    print("\n" + "=" * 60)
    print("STEP 2: BLEND ANIMATIONS")
    print("=" * 60)

    # Determine output path
    if args.output:
        output_path = args.output
    else:
        # Auto-generate output filename
        name1 = Path(input1).stem
        name2 = Path(input2).stem
        output_path = str(work_dir / "blends" / f"{name1}_{name2}_blend.bvh")

    # Create output directory
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # Blend animations
    config = BlendConfig(
        source_animation=input1,
        target_animation=input2,
        blend_mode="single-shot",
    )

    print(f"\nBlending:")
    print(f"  Input 1: {input1}")
    print(f"  Input 2: {input2}")
    print(f"  Ratio: {args.ratio:.1%}")
    print(f"  Method: {args.method}")

    result = blend_animations(config)

    if not result.success:
        print(f"❌ Blend failed")
        print(f"   Error: {result.error_message_message}")
        return None

    print(f"✅ Blended: {result.output_path}")
    return result.output_path


def run_upload_step(args, file_path: str) -> bool:
    """
    Execute upload step of pipeline.

    Returns:
        True if successful, False on error
    """
    print("\n" + "=" * 60)
    print("STEP 3: UPLOAD TO GCS")
    print("=" * 60)

    # Load GCS configuration
    try:
        env_config = get_config()
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        return False

    # Create upload configuration
    config = UploadConfig(
        bucket_name=env_config.gcs_bucket,
        destination_folder=args.upload_folder,
        metadata={
            "pipeline": "mixamo-blend-pipeline",
            "blend_ratio": str(args.ratio),
            "blend_method": args.method,
        },
    )

    print(f"\nUploading:")
    print(f"  File: {file_path}")
    print(f"  Bucket: {env_config.gcs_bucket}")
    print(f"  Folder: {args.upload_folder}")

    result = upload_file(file_path, config)

    if not result.success:
        print(f"❌ Upload failed")
        print(f"   Error: {result.error_message_message}")
        return False

    print(f"✅ Uploaded: {result.gcs_uri}")
    print(f"   Size: {result.file_size_bytes:,} bytes")
    print(f"   Duration: {result.duration_seconds:.2f}s")
    return True


def run_from_config(config_path: str, verbose: bool = False) -> int:
    """
    Run batch workflow from configuration file.

    Args:
        config_path: Path to YAML configuration file
        verbose: Enable verbose logging

    Returns:
        Exit code (0 for success, 1 for error)
    """
    if verbose:
        import logging

        logging.getLogger("src").setLevel(logging.DEBUG)

    try:
        # Load and validate configuration
        logger.info(f"Loading configuration from: {config_path}")
        config = load_config(config_path)

        errors = validate_config(config)
        if errors:
            print("❌ Configuration validation failed:")
            for error in errors:
                print(f"   • {error}")
            return 1

        print("=" * 60)
        print("MIXAMO BLEND PIPELINE (CONFIG MODE)")
        print(f"Workflow: {config['workflow']}")
        print("=" * 60)

        # Execute workflow based on type
        workflow = config["workflow"]

        if workflow == "blend_batch":
            return run_blend_batch_workflow(config)
        elif workflow == "download_batch":
            logger.warning("download_batch workflow not yet implemented")
            print("❌ download_batch workflow not yet implemented")
            return 1
        elif workflow == "upload_batch":
            logger.warning("upload_batch workflow not yet implemented")
            print("❌ upload_batch workflow not yet implemented")
            return 1
        elif workflow == "full_pipeline":
            logger.warning("full_pipeline workflow not yet implemented")
            print("❌ full_pipeline workflow not yet implemented")
            return 1
        else:
            print(f"❌ Unknown workflow type: {workflow}")
            return 1

    except FileNotFoundError as e:
        print(f"❌ Configuration file not found: {e}")
        return 1
    except Exception as e:
        logger.error(f"Configuration error: {e}", exc_info=True)
        print(f"❌ Failed to load configuration: {e}")
        return 1


def run_blend_batch_workflow(config: dict) -> int:
    """
    Execute blend_batch workflow from configuration.

    Args:
        config: Validated configuration dictionary

    Returns:
        Exit code (0 for success, 1 for error)
    """
    blends = config.get("blends", [])
    if not blends:
        print("❌ No blends defined in configuration")
        return 1

    print(f"\n📋 Processing {len(blends)} blends...")

    successful = 0
    failed = 0

    for i, blend in enumerate(blends, 1):
        name = blend.get("name", f"blend_{i}")
        input1 = blend["input1"]
        input2 = blend["input2"]
        output = blend["output"]
        ratio = blend.get("ratio", 0.5)
        method = blend.get("method", "linear")

        print(f"\n[{i}/{len(blends)}] {name}")
        print(f"   Input1: {input1}")
        print(f"   Input2: {input2}")
        print(f"   Output: {output}")
        print(f"   Ratio: {ratio} ({ratio*100:.0f}% / {(1-ratio)*100:.0f}%)")
        print(f"   Method: {method}")

        try:
            # Create blend config
            blend_config = BlendConfig(
                source_animation=input1,
                target_animation=input2,
                blend_mode="single-shot",
            )

            # Execute blend
            result = blend_animations(blend_config, output)

            if result.success:
                print(f"   ✅ Success")
                successful += 1
            else:
                print(f"   ❌ Failed: {result.error_message}")
                failed += 1

        except Exception as e:
            logger.error(f"Blend failed for {name}: {e}", exc_info=True)
            print(f"   ❌ Error: {e}")
            failed += 1

    # Summary
    print("\n" + "=" * 60)
    print("BATCH BLEND SUMMARY")
    print("=" * 60)
    print(f"Total: {len(blends)}")
    print(f"✅ Successful: {successful}")
    if failed > 0:
        print(f"❌ Failed: {failed}")
    print("=" * 60)

    return 0 if failed == 0 else 1


def main():
    """Main entry point for pipeline orchestrator."""
    args = parse_args()

    # If config file provided, run batch workflow
    if args.config:
        return run_from_config(args.config, args.verbose)

    # Configure logging
    if args.verbose:
        import logging

        logging.getLogger("src").setLevel(logging.DEBUG)

    # Create working directory
    work_dir = Path(args.work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    start_time = time.time()

    print("=" * 60)
    print("MIXAMO BLEND PIPELINE")
    print("=" * 60)

    try:
        # Execute pipeline based on mode
        if args.download_only:
            # Download only mode
            result = run_download_step(args, work_dir)
            if result is None:
                return 1

            print("\n" + "=" * 60)
            print("✅ DOWNLOAD COMPLETE")
            print("=" * 60)
            return 0

        elif args.blend_only:
            # Blend only mode
            if len(args.input_files) < 2:
                print("❌ Error: Need 2 input files for blend-only mode")
                return 1

            output_path = run_blend_step(args, work_dir, args.input_files[0], args.input_files[1])
            if output_path is None:
                return 1

            print("\n" + "=" * 60)
            print("✅ BLEND COMPLETE")
            print("=" * 60)
            return 0

        else:
            # Full pipeline or partial pipeline
            # Step 1: Download
            download_result = run_download_step(args, work_dir)
            if download_result is None:
                return 1

            file1, file2 = download_result

            if file2 is None:
                # Only one animation downloaded
                if args.skip_upload:
                    print("\n" + "=" * 60)
                    print("✅ DOWNLOAD COMPLETE (upload skipped)")
                    print("=" * 60)
                    return 0

                # Upload single file
                if run_upload_step(args, file1):
                    print("\n" + "=" * 60)
                    print("✅ PIPELINE COMPLETE")
                    print("=" * 60)
                    return 0
                else:
                    return 1

            # Step 2: Blend
            blended_path = run_blend_step(args, work_dir, file1, file2)
            if blended_path is None:
                return 1

            if args.skip_upload:
                print("\n" + "=" * 60)
                print("✅ DOWNLOAD + BLEND COMPLETE (upload skipped)")
                print("=" * 60)
                return 0

            # Step 3: Upload
            if run_upload_step(args, blended_path):
                duration = time.time() - start_time
                print("\n" + "=" * 60)
                print("✅ PIPELINE COMPLETE")
                print(f"   Total time: {duration:.2f}s")
                print("=" * 60)
                return 0
            else:
                return 1

    except KeyboardInterrupt:
        print("\n⚠️  Pipeline cancelled by user")
        return 130

    except Exception as e:
        logger.error(f"Pipeline error: {e}", exc_info=True)
        print(f"\n❌ Pipeline failed: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
