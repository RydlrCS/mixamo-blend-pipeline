#!/usr/bin/env python3
"""
Blend two animation files together.

CLI wrapper for the blender module providing command-line access to
animation blending functionality.

Usage:
    python scripts/blend.py input1.bvh input2.bvh -o output.bvh
    python scripts/blend.py walk.bvh run.bvh --ratio 0.3 -o walk_to_run.bvh
    python scripts/blend.py idle.fbx jump.fbx -r 0.5 -o blend.fbx --method snn
"""

import argparse
import sys
from pathlib import Path

# Add src to path for imports (before other imports)
_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from src.blender import blend_animations, BlendConfig  # noqa: E402
from src.utils.logging import get_logger  # noqa: E402

logger = get_logger(__name__)


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Blend two animation files together",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Simple 50/50 blend
  %(prog)s walk.bvh run.bvh -o walk_run_blend.bvh

  # 70%% walk, 30%% run
  %(prog)s walk.bvh run.bvh --ratio 0.3 -o output.bvh

  # Use SNN blending method
  %(prog)s idle.bvh jump.bvh -r 0.5 -o blend.bvh --method snn

  # Verbose output
  %(prog)s walk.bvh run.bvh -o output.bvh -v
        """,
    )

    parser.add_argument(
        "input1",
        type=str,
        help="Path to first animation file",
    )

    parser.add_argument(
        "input2",
        type=str,
        help="Path to second animation file",
    )

    parser.add_argument(
        "-o",
        "--output",
        required=True,
        help="Output file path for blended animation",
    )

    parser.add_argument(
        "-r",
        "--ratio",
        type=float,
        default=0.5,
        help=(
            "Blend ratio (0.0-1.0, default: 0.5). "
            "0.0 = all input1, 1.0 = all input2"
        ),
    )

    parser.add_argument(
        "-m",
        "--method",
        choices=["linear", "snn", "spade"],
        default="linear",
        help="Blending method (default: linear)",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )

    return parser.parse_args()


def validate_args(args):
    """Validate command-line arguments."""
    # Check input files exist
    input1_path = Path(args.input1)
    if not input1_path.exists():
        print(f"❌ Error: Input file not found: {args.input1}")
        return False

    input2_path = Path(args.input2)
    if not input2_path.exists():
        print(f"❌ Error: Input file not found: {args.input2}")
        return False

    # Check input files are readable
    if not input1_path.is_file():
        print(f"❌ Error: Not a file: {args.input1}")
        return False

    if not input2_path.is_file():
        print(f"❌ Error: Not a file: {args.input2}")
        return False

    # Validate blend ratio
    if not 0.0 <= args.ratio <= 1.0:
        print(f"❌ Error: Blend ratio must be between 0.0 and 1.0")
        print(f"   Got: {args.ratio}")
        return False

    # Check output directory exists or can be created
    output_path = Path(args.output)
    output_dir = output_path.parent
    if not output_dir.exists():
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"❌ Error: Cannot create output directory: {e}")
            return False

    return True


def main():
    """Main entry point for blend CLI."""
    args = parse_args()

    # Configure logging verbosity
    if args.verbose:
        import logging

        logging.getLogger("src.blender").setLevel(logging.DEBUG)

    # Validate arguments
    if not validate_args(args):
        return 1

    logger.info(f"Blending animations: {args.input1} + {args.input2} " f"(ratio: {args.ratio})")

    # Create blend configuration
    config = BlendConfig(
        source_animation=args.input1,
        target_animation=args.input2,
        blend_mode="single-shot",
    )

    try:
        # Attempt blend (placeholder implementation)
        result = blend_animations(config, output_path=args.output)

        if result.success:
            print(f"✅ Blend successful!")
            print(f"  Input 1: {args.input1}")
            print(f"  Input 2: {args.input2}")
            print(f"  Ratio: {args.ratio:.1%} of input2")
            print(f"  Method: {args.method}")
            print(f"  Output: {result.output_path}")
            print(f"  Duration: {result.duration_seconds:.2f}s")
            if result.frame_count:
                print(f"  Frames: {result.frame_count}")
            return 0
        else:
            print(f"❌ Blend failed:")
            print(f"  Error: {result.error_message}")
            if args.verbose and hasattr(result, "error_details"):
                print(f"  Details: {result.error_details}")
            return 1

    except KeyboardInterrupt:
        print("\n⚠️  Blend cancelled by user")
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
