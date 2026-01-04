#!/usr/bin/env python3
"""
Download animations from Mixamo.

CLI wrapper for the downloader module providing easy command-line access
to Mixamo animation downloads.

Usage:
    python scripts/download.py --character ybot --animation idle
    python scripts/download.py -c ybot -a "walking forward" -o ./downloads/
    python scripts/download.py --character maximo --animation run --format bvh
"""

import argparse
import sys
from pathlib import Path

# Add src to path for imports (before other imports)
_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from src.downloader import download_animation, DownloadConfig  # noqa: E402
from src.utils.logging import get_logger  # noqa: E402

logger = get_logger(__name__)


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Download animations from Mixamo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download idle animation for Y Bot character
  %(prog)s --character ybot --animation idle

  # Download with custom output directory
  %(prog)s -c ybot -a "walking forward" -o ./my_animations/

  # Download in FBX format
  %(prog)s -c maximo -a run --format fbx

  # Verbose output
  %(prog)s -c ybot -a jump -v
        """,
    )

    parser.add_argument(
        "-c",
        "--character",
        required=True,
        help="Character name (e.g., 'ybot', 'maximo')",
    )

    parser.add_argument(
        "-a",
        "--animation",
        required=True,
        help="Animation name (e.g., 'idle', 'walking forward')",
    )

    parser.add_argument(
        "-o",
        "--output",
        default="./downloads",
        help="Output directory (default: ./downloads)",
    )

    parser.add_argument(
        "-f",
        "--format",
        choices=["bvh", "fbx", "dae"],
        default="bvh",
        help="Animation format (default: bvh)",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )

    return parser.parse_args()


def main():
    """Main entry point for download CLI."""
    args = parse_args()

    # Configure logging verbosity
    if args.verbose:
        import logging

        logging.getLogger("src.downloader").setLevel(logging.DEBUG)

    # Create output directory
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Downloading animation: {args.animation} " f"for character: {args.character}")

    # Create download configuration
    config = DownloadConfig(
        character_name=args.character,
        animation_name=args.animation,
        output_dir=str(output_dir),
        file_format=args.format,
    )

    try:
        # Attempt download (placeholder implementation)
        result = download_animation(config)

        if result.success:
            print(f"✅ Download successful!")
            print(f"  Character: {args.character}")
            print(f"  Animation: {args.animation}")
            print(f"  Format: {args.format}")
            print(f"  Output: {result.output_path}")
            print(f"  Duration: {result.duration_seconds:.2f}s")
            return 0
        else:
            print(f"❌ Download failed:")
            print(f"  Error: {result.error_message}")
            if args.verbose and result.error_details:
                print(f"  Details: {result.error_details}")
            return 1

    except KeyboardInterrupt:
        print("\n⚠️  Download cancelled by user")
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
