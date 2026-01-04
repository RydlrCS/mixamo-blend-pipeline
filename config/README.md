# Configuration Files

YAML configuration files for batch processing and pipeline orchestration.

## Directory Structure

```
config/
├── examples/          # Example configuration templates
│   ├── blend_batch.yaml        # Batch blend multiple animations
│   ├── download_batch.yaml     # Batch download from Mixamo
│   ├── upload_batch.yaml       # Batch upload to GCS
│   └── full_pipeline.yaml      # Complete download→blend→upload
└── README.md          # This file
```

## Configuration Format

All configuration files use YAML format with the following structure:

```yaml
version: "1.0"          # Configuration format version (required)
workflow: <type>        # Workflow type (required)
# ... workflow-specific settings
```

### Supported Workflows

1. **blend_batch** - Batch blend multiple animation pairs
2. **download_batch** - Batch download animations from Mixamo
3. **upload_batch** - Batch upload files to Google Cloud Storage
4. **full_pipeline** - Complete pipeline orchestration

## Usage

### Using with CLI

```bash
# Run batch blend workflow
python scripts/pipeline.py --config config/examples/blend_batch.yaml

# With verbose logging
python scripts/pipeline.py --config config/examples/blend_batch.yaml -v
```

### Using with Python API

```python
from src.utils.config_loader import load_config, validate_config

# Load configuration
config = load_config("config/examples/blend_batch.yaml")

# Validate before use
errors = validate_config(config)
if errors:
    for error in errors:
        print(f"❌ {error}")
else:
    print("✓ Configuration valid")
```

## Workflow: blend_batch

Batch process multiple animation blends.

**Example:**

```yaml
version: "1.0"
workflow: blend_batch

blends:
  - name: walk_to_run
    input1: seed/walk.bvh
    input2: seed/run.bvh
    ratio: 0.5
    method: linear
    output: blend/walk_run.bvh

  - name: idle_to_jump
    input1: seed/idle.bvh
    input2: seed/jump.bvh
    ratio: 0.3
    method: snn
    output: blend/idle_jump.bvh

upload:
  folder: blend/
  metadata:
    source: mixamo
    pipeline: batch
```

**Fields:**
- `blends` (required): List of blend configurations
  - `name` (optional): Descriptive name for the blend
  - `input1` (required): Path to first animation file
  - `input2` (required): Path to second animation file
  - `ratio` (optional, default: 0.5): Blend ratio (0.0-1.0)
  - `method` (optional, default: linear): Blending method (linear, snn, spade)
  - `output` (required): Output file path
- `upload` (optional): Upload configuration after blending
  - `folder`: GCS destination folder
  - `metadata`: Key-value metadata pairs

**Usage:**
```bash
python scripts/pipeline.py --config config/examples/blend_batch.yaml
```

## Workflow: download_batch

Batch download multiple animations from Mixamo.

**Example:**

```yaml
version: "1.0"
workflow: download_batch

downloads:
  - animation_id: "walk_forward"
    output: seed/walk.fbx
    format: fbx

  - animation_id: "running"
    output: seed/run.fbx
    format: fbx

character: ybot
validate: true
```

**Fields:**
- `downloads` (required): List of download configurations
  - `animation_id` (required): Mixamo animation ID or name
  - `output` (required): Output file path
  - `format` (optional, default: fbx): File format (fbx, bvh)
- `character` (optional): Character name for all downloads
- `validate` (optional, default: true): Validate files after download

**Status:** ⚠️ Not yet implemented (placeholder module)

## Workflow: upload_batch

Batch upload multiple files to Google Cloud Storage.

**Example:**

```yaml
version: "1.0"
workflow: upload_batch

uploads:
  - file: blend/walk_run.bvh
    folder: blend/
    metadata:
      source: mixamo
      method: linear
      ratio: 0.5

  - file: seed/walk.fbx
    folder: seed/
    metadata:
      source: mixamo
      type: source

settings:
  make_public: false
  timeout_seconds: 300
```

**Fields:**
- `uploads` (required): List of upload configurations
  - `file` (required): Local file path to upload
  - `folder` (optional): GCS destination folder
  - `metadata` (optional): Key-value metadata pairs
- `settings` (optional): Global upload settings
  - `make_public`: Make files publicly accessible
  - `timeout_seconds`: Upload timeout

**Status:** ⚠️ Not yet implemented

## Workflow: full_pipeline

Complete pipeline orchestration (download → blend → upload).

**Example:**

```yaml
version: "1.0"
workflow: full_pipeline

download:
  animations:
    - animation_id: "walk_forward"
      output: work/walk.fbx
    - animation_id: "running"
      output: work/run.fbx
  format: fbx

blend:
  pairs:
    - input1: work/walk.fbx
      input2: work/run.fbx
      ratio: 0.5
      method: linear
      output: work/walk_run_blend.fbx

upload:
  files:
    - work/walk_run_blend.fbx
  folder: experimental/
  metadata:
    pipeline: full
    automated: true

cleanup: true
```

**Fields:**
- `download` (required): Download configuration
  - `animations`: List of animations to download
  - `format`: File format for downloads
- `blend` (required): Blend configuration
  - `pairs`: List of animation pairs to blend
- `upload` (required): Upload configuration
  - `files`: Files to upload
  - `folder`: GCS destination folder
  - `metadata`: Upload metadata
- `cleanup` (optional, default: false): Remove intermediate files after completion

**Status:** ⚠️ Not yet implemented

## Creating Custom Configurations

1. **Copy an example:**
   ```bash
   cp config/examples/blend_batch.yaml config/my_workflow.yaml
   ```

2. **Edit configuration:**
   - Update paths to your local files
   - Adjust blend ratios and methods
   - Add custom metadata
   - Configure upload settings

3. **Validate configuration:**
   ```bash
   python -c "from src.utils.config_loader import load_config, validate_config; \
   config = load_config('config/my_workflow.yaml'); \
   errors = validate_config(config); \
   print('✓ Valid' if not errors else errors)"
   ```

4. **Run workflow:**
   ```bash
   python scripts/pipeline.py --config config/my_workflow.yaml
   ```

## Configuration Validation

The config loader validates:

- **Required fields** - Ensures all mandatory fields are present
- **Field types** - Checks that values match expected types (string, number, list, etc.)
- **Value ranges** - Validates ratios are 0.0-1.0, etc.
- **Enum values** - Ensures methods, formats match allowed values
- **Workflow structure** - Verifies workflow-specific requirements

**Example validation errors:**

```
❌ Configuration validation failed:
   • version: Missing required field
   • blends[0].ratio: Must be between 0.0 and 1.0 (got: 1.5)
   • blends[1].method: Invalid method (valid: linear, snn, spade) (got: invalid)
```

## See Also

- [CLI.md](../docs/CLI.md) - Command-line interface documentation
- [BLENDANIM_INTEGRATION.md](../docs/BLENDANIM_INTEGRATION.md) - Blending methods guide
- [README.md](../README.md) - Project overview
