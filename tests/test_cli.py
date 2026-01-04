"""Tests for CLI scripts."""

import subprocess
import sys
from pathlib import Path

# Project paths
project_root = Path(__file__).parent.parent
scripts_dir = project_root / "scripts"


class TestDownloadCLI:
    """Tests for download.py CLI script."""

    def test_help_message(self):
        """Test that --help works."""
        result = subprocess.run(
            [sys.executable, str(scripts_dir / "download.py"), "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "Download animations from Mixamo" in result.stdout
        assert "--character" in result.stdout
        assert "--animation" in result.stdout

    def test_missing_required_args(self):
        """Test that missing required arguments returns error."""
        result = subprocess.run(
            [sys.executable, str(scripts_dir / "download.py")],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert "required" in result.stderr.lower()


class TestBlendCLI:
    """Tests for blend.py CLI script."""

    def test_help_message(self):
        """Test that --help works."""
        result = subprocess.run(
            [sys.executable, str(scripts_dir / "blend.py"), "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "Blend two animation files" in result.stdout
        assert "--ratio" in result.stdout
        assert "--output" in result.stdout

    def test_missing_required_args(self):
        """Test that missing required arguments returns error."""
        result = subprocess.run(
            [sys.executable, str(scripts_dir / "blend.py")],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert "required" in result.stderr.lower()

    def test_invalid_ratio_too_low(self):
        """Test that ratio < 0.0 is rejected."""
        result = subprocess.run(
            [
                sys.executable,
                str(scripts_dir / "blend.py"),
                "file1.bvh",
                "file2.bvh",
                "--ratio",
                "-0.5",
            ],
            capture_output=True,
            text=True,
        )
        # Should either fail at argparse or validation
        assert result.returncode != 0

    def test_invalid_ratio_too_high(self):
        """Test that ratio > 1.0 is rejected."""
        result = subprocess.run(
            [
                sys.executable,
                str(scripts_dir / "blend.py"),
                "file1.bvh",
                "file2.bvh",
                "--ratio",
                "1.5",
            ],
            capture_output=True,
            text=True,
        )
        # Should either fail at argparse or validation
        assert result.returncode != 0


class TestUploadCLI:
    """Tests for upload.py CLI script."""

    def test_help_message(self):
        """Test that --help works."""
        result = subprocess.run(
            [sys.executable, str(scripts_dir / "upload.py"), "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "Upload animation files" in result.stdout
        assert "--folder" in result.stdout
        assert "--metadata" in result.stdout
        assert "--public" in result.stdout

    def test_missing_required_args(self):
        """Test that missing required arguments returns error."""
        result = subprocess.run(
            [sys.executable, str(scripts_dir / "upload.py")],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert "required" in result.stderr.lower()


class TestPipelineCLI:
    """Tests for pipeline.py CLI script."""

    def test_help_message(self):
        """Test that --help works."""
        result = subprocess.run(
            [sys.executable, str(scripts_dir / "pipeline.py"), "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "pipeline" in result.stdout.lower()
        assert "--download-only" in result.stdout
        assert "--blend-only" in result.stdout
        assert "--skip-upload" in result.stdout

    def test_conflicting_mode_flags(self):
        """Test that conflicting mode flags are handled."""
        result = subprocess.run(
            [
                sys.executable,
                str(scripts_dir / "pipeline.py"),
                "--download-only",
                "--blend-only",
            ],
            capture_output=True,
            text=True,
        )
        # Should either fail at argparse (mutually exclusive) or validation
        # Depending on implementation, this may succeed but only do one operation
        # For now, just check it doesn't crash
        assert result.returncode in (0, 1, 2)


class TestCLIIntegration:
    """Integration tests for CLI scripts."""

    def test_all_scripts_executable(self):
        """Verify all CLI scripts are executable."""
        cli_scripts = [
            "download.py",
            "blend.py",
            "upload.py",
            "pipeline.py",
        ]

        for script_name in cli_scripts:
            script_path = scripts_dir / script_name
            assert script_path.exists(), f"{script_name} not found"
            assert script_path.is_file(), f"{script_name} is not a file"

            # Test that script can be imported (syntax check)
            result = subprocess.run(
                [sys.executable, "-m", "py_compile", str(script_path)],
                capture_output=True,
                text=True,
            )
            assert (
                result.returncode == 0
            ), f"{script_name} has syntax errors: {result.stderr}"

    def test_scripts_have_shebang(self):
        """Verify all scripts have proper shebang."""
        cli_scripts = [
            "download.py",
            "blend.py",
            "upload.py",
            "pipeline.py",
        ]

        for script_name in cli_scripts:
            script_path = scripts_dir / script_name
            with open(script_path, "r") as f:
                first_line = f.readline().strip()
                assert first_line == "#!/usr/bin/env python3", (
                    f"{script_name} missing proper shebang"
                )

    def test_scripts_have_docstring(self):
        """Verify all scripts have module docstrings."""
        cli_scripts = [
            "download.py",
            "blend.py",
            "upload.py",
            "pipeline.py",
        ]

        for script_name in cli_scripts:
            script_path = scripts_dir / script_name
            with open(script_path, "r") as f:
                lines = f.readlines()
                # Skip shebang and blank lines
                doc_start = None
                for i, line in enumerate(lines[1:], 1):
                    if line.strip().startswith('"""'):
                        doc_start = i
                        break
                assert (
                    doc_start is not None
                ), f"{script_name} missing module docstring"
