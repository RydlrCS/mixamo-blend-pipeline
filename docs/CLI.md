# CLI Reference

Command-line interfaces for the Mixamo Blend Pipeline.

## Overview

The pipeline provides four CLI scripts for different workflow stages:

- **download.py** - Download animations from Mixamo
- **blend.py** - Blend two animations together  
- **upload.py** - Upload animations to Google Cloud Storage
- **pipeline.py** - Full end-to-end orchestration

All scripts support `--help` for detailed usage information.

## Quick Start

```bash
# Make scripts executable (one-time setup)
chmod +x scripts/*.py

# Download an animation
python scripts/download.py --character ybot --animation idle

# Blend two animations
python scripts/blend.py walk.bvh run.bvh --ratio 0.7 -o blended.bvh

# Upload to GCS (requires .env configuration)
python scripts/upload.py animation.bvh --folder seed/

# Run full pipeline
python scripts/pipeline.py --character ybot --animation walk,run --blend-ratio 0.5
```

## Environment Configuration

Upload and pipeline scripts require environment variables. Create a `.env` file:

```env
# Required
GCS_BUCKET=your-gcs-bucket-name
BQ_PROJECT=your-bigquery-project
BQ_DATASET=your-dataset-name

# Optional
ELASTICSEARCH_URL=https://your-elasticsearch-endpoint
ES_API_KEY=your-api-key
ES_INDEX=your-index-name
UPLOAD_TIMEOUT_SECONDS=300
```

See `.env.example` for a template.

## download.py

Download animations from Mixamo using browser-based workflow.

```bash
python scripts/download.py [OPTIONS]
```

### Options

- **`--character, -c`** (required): Character name/ID
- **`--animation, -a`** (required): Animation name/ID
- **`--output, -o`**: Output file path (default: auto-generated)
- **`--format, -f`**: File format - `fbx` or `bvh` (default: `fbx`)
- **`--verbose, -v`**: Enable verbose logging

### Examples

```bash
# Download idle animation for ybot character
python scripts/download.py -c ybot -a idle

# Download to specific location as BVH
python scripts/download.py -c maximo -a "walking forward" -o animations/walk.bvh -f bvh

# Verbose output
python scripts/download.py -c ybot -a run -v
```

### Notes

- Uses placeholder implementation (see docs/MIXAMO_INTEGRATION.md)
- In production, integrates with mixamo_anims_downloader browser scripts
- Validates downloaded files for format and size

## blend.py

Blend two animation files with configurable ratios.

```bash
python scripts/blend.py input1 input2 [OPTIONS]
```

### Arguments

- **`input1`** (required): Path to first animation file
- **`input2`** (required): Path to second animation file

### Options

- **`--output, -o`** (required): Output file path
- **`--ratio, -r`**: Blend ratio 0.0-1.0 (default: 0.5)
  - 0.0 = 100% input1, 1.0 = 100% input2
- **`--method, -m`**: Blending method - `linear`, `snn`, `spade` (default: `linear`)
- **`--verbose, -v`**: Enable verbose logging

### Examples

```bash
# Simple 50/50 blend
python scripts/blend.py walk.bvh run.bvh -o walk_run.bvh

# 70% walk, 30% run
python scripts/blend.py walk.bvh run.bvh --ratio 0.3 -o output.bvh

# Use SNN blending method
python scripts/blend.py idle.bvh jump.bvh -r 0.5 -o blend.bvh --method snn

# Verbose output
python scripts/blend.py walk.bvh run.bvh -o output.bvh -v
```

### Notes

- Uses placeholder implementation (see docs/BLENDANIM_INTEGRATION.md)
- In production, integrates with blendanim framework and GANimator
- Validates input files exist and are readable
- Creates output directories if needed

## upload.py

Upload animation files to Google Cloud Storage.

```bash
python scripts/upload.py file [file ...] [OPTIONS]
```

### Arguments

- **`files`** (required): One or more file paths to upload

### Options

- **`--folder, -f`**: GCS destination folder (e.g., `seed/`, `blend/`)
- **`--metadata, -m`**: Key=value metadata pairs (can specify multiple)
- **`--public, -p`**: Make uploaded files publicly accessible
- **`--timeout, -t`**: Upload timeout in seconds (default: from config)
- **`--verbose, -v`**: Enable verbose logging

### Examples

```bash
# Upload single file to seed folder
python scripts/upload.py animation.bvh --folder seed/

# Upload multiple files
python scripts/upload.py walk.bvh run.bvh jump.bvh --folder blend/

# Add metadata and make public
python scripts/upload.py anim.bvh --folder seed/ --metadata source=mixamo version=1.0 --public

# Custom timeout for large files
python scripts/upload.py large_animation.fbx --folder build/ --timeout 600
```

### Notes

- Requires environment configuration (.env file)
- Uses actual Google Cloud Storage SDK (google-cloud-storage)
- Automatically determines GCS bucket from environment
- Supports batch uploads with summary statistics
- Attaches custom metadata to uploaded objects

## pipeline.py

End-to-end pipeline orchestrator combining download → blend → upload.

```bash
python scripts/pipeline.py [OPTIONS]
```

### Workflow Modes

- **Full pipeline** (default): Download → Blend → Upload
- **`--download-only`**: Only download animations
- **`--blend-only`**: Only blend (requires pre-downloaded files)
- **`--skip-upload`**: Download and blend, skip upload

### Options

**Download:**
- **`--character, -c`**: Character name/ID (required for download)
- **`--animation, -a`**: Animation name/ID (required for download)
- **`--format, -f`**: File format - `fbx` or `bvh` (default: `fbx`)

**Blend:**
- **`--blend-ratio, -r`**: Blend ratio 0.0-1.0 (default: 0.5)
- **`--blend-method, -m`**: Method - `linear`, `snn`, `spade` (default: `linear`)

**Upload:**
- **`--upload-folder`**: GCS destination folder (default: `blend/`)
- **`--public, -p`**: Make uploaded files publicly accessible

**General:**
- **`--work-dir, -w`**: Working directory for intermediate files (default: `./work/`)
- **`--verbose, -v`**: Enable verbose logging

### Examples

```bash
# Full pipeline: download two animations, blend them, upload result
python scripts/pipeline.py -c ybot -a "idle,walk" -r 0.5

# Download only (for manual processing)
python scripts/pipeline.py --download-only -c maximo -a run

# Blend pre-downloaded files only
python scripts/pipeline.py --blend-only --input1 walk.bvh --input2 run.bvh

# Download and blend, skip upload
python scripts/pipeline.py -c ybot -a "idle,jump" --skip-upload

# Full pipeline with custom settings
python scripts/pipeline.py \\
  -c ybot -a "walk,run" \\
  -r 0.7 \\
  --blend-method snn \\
  --upload-folder experimental/ \\
  --public \\
  -v
```

### Workflow Details

1. **Download Step**:
   - Downloads specified animations using download.py logic
   - Saves to working directory
   - Validates file integrity

2. **Blend Step**:
   - Blends downloaded (or specified) animations
   - Uses blend.py logic with configuration
   - Auto-generates output filename if not specified

3. **Upload Step**:
   - Uploads blended animation to GCS
   - Attaches metadata (source, method, ratio, timestamps)
   - Generates GCS URI for uploaded file

### Notes

- Uses placeholder implementations for download/blend
- Upload uses actual GCS SDK integration
- Creates working directory automatically
- Cleans up intermediate files on completion (optional)
- Comprehensive error recovery at each step

## Exit Codes

All scripts use standard exit codes:

- **0** - Success
- **1** - Error (invalid arguments, file not found, operation failed)
- **130** - Cancelled by user (Ctrl+C)

## Error Handling

All scripts implement:

- Input validation before execution
- Graceful error messages with actionable guidance
- Proper cleanup on failure
- Exit codes for scripting/automation

Example error output:

```
❌ Error: Input file not found: walk.bvh
   Check that the file exists and path is correct
```

## Logging

Use `--verbose` flag for detailed logging:

```bash
python scripts/blend.py walk.bvh run.bvh -o output.bvh -v
```

Verbose output includes:
- Configuration details
- Progress updates
- Performance metrics (duration, file sizes)
- Debug information

## Integration with Other Tools

### Using in Bash Scripts

```bash
#!/bin/bash
# Batch process multiple animations

for anim in walk run jump; do
  python scripts/download.py -c ybot -a "$anim" || exit 1
done

python scripts/blend.py walk.bvh run.bvh -o walk_run.bvh || exit 1
python scripts/upload.py walk_run.bvh --folder batch/
```

### Python Integration

```python
import subprocess

# Run CLI programmatically
result = subprocess.run(
    ["python", "scripts/download.py", "-c", "ybot", "-a", "idle"],
    capture_output=True,
    text=True,
)

if result.returncode == 0:
    print("Success!")
else:
    print(f"Error: {result.stderr}")
```

## Troubleshooting

### Import Errors

If you see `ModuleNotFoundError: No module named 'src'`:

```bash
# Make sure you're running from project root
cd /path/to/mixamo-blend-pipeline

# Verify virtual environment is activated
source venv/bin/activate

# Check Python path includes project root
python -c "import sys; print(sys.path)"
```

### GCS Upload Errors

If upload fails with authentication errors:

```bash
# Verify .env file exists and has required variables
cat .env

# Check GCS authentication
gcloud auth application-default login

# Test configuration
python scripts/test_upload.py sample.bvh
```

### Blend Failures

If blending fails:

```bash
# Verify input files are valid
file walk.bvh run.bvh

# Check file sizes (must be > 1KB)
ls -lh walk.bvh run.bvh

# Try verbose mode for details
python scripts/blend.py walk.bvh run.bvh -o output.bvh -v
```

## See Also

- [MIXAMO_INTEGRATION.md](MIXAMO_INTEGRATION.md) - Mixamo download integration
- [BLENDANIM_INTEGRATION.md](BLENDANIM_INTEGRATION.md) - Animation blending details
- [README.md](../README.md) - Project overview and setup
- `.env.example` - Environment configuration template
