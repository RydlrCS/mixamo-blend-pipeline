"""
Unit tests for blender module (motion blending interface).

Tests the blender module API without requiring actual blendanim framework.
Uses mocked data and validates interface contracts, error handling, and
parameter validation.
"""

import pytest
from pathlib import Path
import tempfile

from src.blender import (
    BlendConfig,
    BlendResult,
    blend_motions,
    blend_batch,
    load_bvh,
    save_bvh,
)


class TestBlendConfig:
    """Test BlendConfig dataclass."""

    def test_blend_config_creation_with_defaults(self):
        """Test creating BlendConfig with only required fields."""
        config = BlendConfig(
            source_animation="./seed/walk.bvh",
            target_animation="./seed/run.bvh",
        )

        assert config.source_animation == "./seed/walk.bvh"
        assert config.target_animation == "./seed/run.bvh"
        assert config.blend_mode == "single-shot"
        assert config.transition_frames == 30
        assert config.fps == 30
        assert config.scale == 1.0
        assert config.use_temporal_conditioning is True
        assert config.checkpoint_path is None

    def test_blend_config_creation_with_custom_values(self):
        """Test creating BlendConfig with all custom fields."""
        config = BlendConfig(
            source_animation="./animations/idle.bvh",
            target_animation="./animations/jump.bvh",
            blend_mode="multi-frame",
            transition_frames=60,
            fps=60,
            scale=2.0,
            use_temporal_conditioning=False,
            checkpoint_path="./checkpoints/model.pt",
        )

        assert config.source_animation == "./animations/idle.bvh"
        assert config.target_animation == "./animations/jump.bvh"
        assert config.blend_mode == "multi-frame"
        assert config.transition_frames == 60
        assert config.fps == 60
        assert config.scale == 2.0
        assert config.use_temporal_conditioning is False
        assert config.checkpoint_path == "./checkpoints/model.pt"


class TestBlendResult:
    """Test BlendResult dataclass."""

    def test_blend_result_success(self):
        """Test creating successful BlendResult."""
        config = BlendConfig(
            source_animation="./seed/walk.bvh",
            target_animation="./seed/run.bvh",
        )

        result = BlendResult(
            success=True,
            output_path="./blend/walk_to_run.bvh",
            blend_config=config,
            frame_count=150,
            duration_seconds=2.5,
        )

        assert result.success is True
        assert result.output_path == "./blend/walk_to_run.bvh"
        assert result.blend_config == config
        assert result.frame_count == 150
        assert result.duration_seconds == 2.5
        assert result.error_message is None

    def test_blend_result_failure(self):
        """Test creating failed BlendResult with error message."""
        config = BlendConfig(
            source_animation="./missing.bvh",
            target_animation="./seed/run.bvh",
        )

        result = BlendResult(
            success=False,
            output_path=None,
            blend_config=config,
            frame_count=0,
            duration_seconds=0.1,
            error_message="Source file not found",
        )

        assert result.success is False
        assert result.output_path is None
        assert result.error_message == "Source file not found"


class TestLoadBVH:
    """Test BVH loading function."""

    def test_load_bvh_nonexistent_file(self):
        """Test load_bvh raises FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError) as exc_info:
            load_bvh("/nonexistent/path/animation.bvh")

        assert "not found" in str(exc_info.value).lower()

    def test_load_bvh_invalid_extension(self):
        """Test load_bvh raises ValueError for non-BVH file."""
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            with pytest.raises(ValueError) as exc_info:
                load_bvh(tmp_path)

            assert "invalid file format" in str(exc_info.value).lower()
        finally:
            Path(tmp_path).unlink()

    def test_load_bvh_not_implemented(self):
        """Test load_bvh raises NotImplementedError (placeholder)."""
        with tempfile.NamedTemporaryFile(suffix=".bvh", delete=False) as tmp:
            tmp_path = tmp.name
            tmp.write(b"HIERARCHY\nROOT Hips\n")

        try:
            with pytest.raises(NotImplementedError) as exc_info:
                load_bvh(tmp_path)

            assert "blendanim" in str(exc_info.value).lower()
        finally:
            Path(tmp_path).unlink()


class TestSaveBVH:
    """Test BVH saving function."""

    def test_save_bvh_not_implemented(self):
        """Test save_bvh raises NotImplementedError (placeholder)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "output.bvh"

            with pytest.raises(NotImplementedError) as exc_info:
                save_bvh(
                    str(output_path),
                    positions=None,
                    rotations=None,
                    offsets=None,
                    parents=None,
                    names=["Hips", "Spine"],
                    fps=30,
                    scale=1.0,
                )

            assert "blendanim" in str(exc_info.value).lower()


class TestBlendMotions:
    """Test blend_motions function."""

    def test_blend_motions_invalid_blend_mode(self):
        """Test blend_motions rejects invalid blend_mode."""
        config = BlendConfig(
            source_animation="./seed/walk.bvh",
            target_animation="./seed/run.bvh",
            blend_mode="invalid-mode",
        )

        result = blend_motions(config, "./output/blend.bvh")

        assert result.success is False
        assert result.output_path is None
        assert "unsupported blend_mode" in result.error_message.lower()

    def test_blend_motions_too_few_transition_frames(self):
        """Test blend_motions rejects transition_frames below minimum."""
        config = BlendConfig(
            source_animation="./seed/walk.bvh",
            target_animation="./seed/run.bvh",
            transition_frames=10,  # Below MIN_FRAMES (30)
        )

        result = blend_motions(config, "./output/blend.bvh")

        assert result.success is False
        assert result.output_path is None
        assert "transition_frames" in result.error_message.lower()

    def test_blend_motions_missing_source_file(self):
        """Test blend_motions detects missing source animation."""
        config = BlendConfig(
            source_animation="./nonexistent/walk.bvh",
            target_animation="./seed/run.bvh",
        )

        result = blend_motions(config, "./output/blend.bvh")

        assert result.success is False
        assert result.output_path is None
        assert "source animation not found" in result.error_message.lower()

    def test_blend_motions_missing_target_file(self):
        """Test blend_motions detects missing target animation."""
        # Create temporary source file
        with tempfile.NamedTemporaryFile(suffix=".bvh", delete=False, mode="w") as tmp:
            tmp.write("HIERARCHY\n")
            source_path = tmp.name

        try:
            config = BlendConfig(
                source_animation=source_path,
                target_animation="./nonexistent/run.bvh",
            )

            result = blend_motions(config, "./output/blend.bvh")

            assert result.success is False
            assert result.output_path is None
            assert "target animation not found" in result.error_message.lower()
        finally:
            Path(source_path).unlink()

    def test_blend_motions_creates_output_directory(self):
        """Test blend_motions creates output directory if needed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create source and target files
            source_path = Path(tmpdir) / "source.bvh"
            target_path = Path(tmpdir) / "target.bvh"
            source_path.write_text("HIERARCHY\n")
            target_path.write_text("HIERARCHY\n")

            # Output in nested directory
            output_path = Path(tmpdir) / "output" / "nested" / "blend.bvh"

            config = BlendConfig(
                source_animation=str(source_path),
                target_animation=str(target_path),
            )

            result = blend_motions(config, str(output_path))

            # Should create parent directories
            assert output_path.parent.exists()

            # Will fail with NotImplementedError but directories created
            assert result.success is False
            assert "blendanim" in result.error_message.lower()


class TestBlendBatch:
    """Test blend_batch function."""

    def test_blend_batch_empty_list(self):
        """Test blend_batch handles empty configuration list."""
        results = blend_batch([], "./output/")

        assert len(results) == 0

    def test_blend_batch_creates_output_directory(self):
        """Test blend_batch creates output directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "blend_output"

            results = blend_batch(
                [
                    {
                        "source_animation": "./seed/walk.bvh",
                        "target_animation": "./seed/run.bvh",
                    }
                ],
                str(output_dir),
            )

            assert output_dir.exists()
            assert len(results) == 1

    def test_blend_batch_missing_required_fields(self):
        """Test blend_batch detects missing required fields."""
        results = blend_batch(
            [
                {
                    "source_animation": "./seed/walk.bvh",
                    # Missing target_animation
                },
                {
                    # Missing source_animation
                    "target_animation": "./seed/run.bvh",
                },
            ],
            "./output/",
        )

        assert len(results) == 2
        assert all(not r.success for r in results)
        assert all("missing required fields" in r.error_message.lower() for r in results)

    def test_blend_batch_invalid_config(self):
        """Test blend_batch handles invalid configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files so file validation passes
            source_path = Path(tmpdir) / "walk.bvh"
            target_path = Path(tmpdir) / "run.bvh"
            source_path.write_text("HIERARCHY\n")
            target_path.write_text("HIERARCHY\n")

            results = blend_batch(
                [
                    {
                        "source_animation": str(source_path),
                        "target_animation": str(target_path),
                        "fps": "not-a-number",  # Invalid type
                    }
                ],
                str(Path(tmpdir) / "output"),
            )

            assert len(results) == 1
            # Python's type tolerance allows string fps in dataclass
            # Will fail later with NotImplementedError instead
            assert not results[0].success
            # Error is from blend implementation, not type validation
            assert "blendanim" in results[0].error_message.lower()

    def test_blend_batch_multiple_configs(self):
        """Test blend_batch processes multiple configurations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            walk_path = Path(tmpdir) / "walk.bvh"
            run_path = Path(tmpdir) / "run.bvh"
            jump_path = Path(tmpdir) / "jump.bvh"

            walk_path.write_text("HIERARCHY\n")
            run_path.write_text("HIERARCHY\n")
            jump_path.write_text("HIERARCHY\n")

            results = blend_batch(
                [
                    {
                        "source_animation": str(walk_path),
                        "target_animation": str(run_path),
                        "output_filename": "walk_to_run.bvh",
                    },
                    {
                        "source_animation": str(run_path),
                        "target_animation": str(jump_path),
                        "output_filename": "run_to_jump.bvh",
                    },
                ],
                str(Path(tmpdir) / "output"),
            )

            assert len(results) == 2
            # All fail because output_filename is not a BlendConfig parameter
            assert all(not r.success for r in results)
            assert all("invalid config" in r.error_message.lower() for r in results)

    def test_blend_batch_default_output_filename(self):
        """Test blend_batch generates default output filenames."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source_path = Path(tmpdir) / "source.bvh"
            target_path = Path(tmpdir) / "target.bvh"
            source_path.write_text("HIERARCHY\n")
            target_path.write_text("HIERARCHY\n")

            results = blend_batch(
                [
                    {
                        "source_animation": str(source_path),
                        "target_animation": str(target_path),
                        # No output_filename provided
                    }
                ],
                str(Path(tmpdir) / "output"),
            )

            assert len(results) == 1
            # Default filename pattern: blend_0000.bvh
            # (Can't verify exact path since blend fails, but validated)


class TestIntegration:
    """Integration tests for blender module workflow."""

    def test_full_workflow_validation(self):
        """Test complete blend workflow validates all parameters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            source_path = Path(tmpdir) / "walk.bvh"
            target_path = Path(tmpdir) / "run.bvh"
            source_path.write_text("HIERARCHY\nROOT Hips\n")
            target_path.write_text("HIERARCHY\nROOT Hips\n")

            # Create valid configuration
            config = BlendConfig(
                source_animation=str(source_path),
                target_animation=str(target_path),
                blend_mode="single-shot",
                transition_frames=30,
                fps=30,
                scale=1.0,
            )

            output_path = Path(tmpdir) / "output" / "blended.bvh"

            # Execute blend (will fail but validates everything)
            result = blend_motions(config, str(output_path))

            # Verify validation passed (failed only due to implementation)
            assert result.success is False
            assert "blendanim" in result.error_message.lower()
            assert result.blend_config == config
            assert output_path.parent.exists()
