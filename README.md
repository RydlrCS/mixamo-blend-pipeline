# Mixamo Blend Pipeline

**A production-ready pipeline for downloading Mixamo animations, generating motion blends using blendanim framework, and syncing metadata to BigQuery for NPC animation systems.**

## Overview

This repository integrates multiple motion capture workflows:

1. **Download** - Fetch Mixamo animations using browser-based [mixamo_anims_downloader](https://github.com/RydlrCS/mixamo_anims_downloader)
2. **Validate & Organize** - Verify downloaded files and organize for pipeline processing
3. **Generate** - Create motion blends using [blendanim](https://github.com/RydlrCS/blendanim) (GANimator-based temporal conditioning)
4. **Upload** - Store motions in Google Cloud Storage (GCS)
5. **Track** - Sync metadata to BigQuery via `fivetran_connector_sdk` motionblend connector
6. **Consume** - Use high-quality blends in [kijani-spiral](https://github.com/RydlrCS/kijani-spiral) NPC engine

**Important**: This pipeline does NOT directly call Mixamo's API. Use the browser-based scripts from [mixamo_anims_downloader](https://github.com/RydlrCS/mixamo_anims_downloader) to download animations, then use this pipeline for validation, organization, blending, and upload. See [docs/MIXAMO_INTEGRATION.md](docs/MIXAMO_INTEGRATION.md) for detailed workflow.

## Architecture

```
mixamo_anims_downloader → blendanim (GANimator) → GCS → motionblend connector → BigQuery
                                                              ↓
                                                    kijani-spiral NPC engine
```

## Project Structure

```
mixamo-blend-pipeline/
├── src/
│   ├── __init__.py
│   ├── downloader/         # Mixamo animation downloading
│   ├── blender/            # Motion blending with blendanim
│   ├── uploader/           # GCS upload utilities
│   └── utils/              # Logging, validation, helpers
├── tests/                  # Unit and integration tests
├── config/                 # Configuration files
├── scripts/                # CLI scripts for each stage
├── requirements.txt        # Python dependencies
├── pyproject.toml          # Project metadata and build config
├── .flake8                 # Linting configuration
├── mypy.ini                # Type checking configuration
├── .gitignore              # Git ignore patterns
└── README.md               # This file
```

## Development Principles

- **Readability First**: Clear variable names, comprehensive docstrings, minimal complexity
- **Type Safety**: Full type hints with mypy validation
- **Verbose Logging**: Entry/exit logs for all functions, structured logging
- **Error Handling**: Comprehensive exception handling with actionable error messages
- **Maintainability**: Modular design, single responsibility, no code duplication
- **Quality Gates**: Linting (flake8), formatting (black), type checking (mypy), spell checking

## Prerequisites

- Python 3.9+
- Google Cloud SDK (for GCS access)
- Git

## Installation

```bash
# Clone the repository
git clone https://github.com/RydlrCS/mixamo-blend-pipeline.git
cd mixamo-blend-pipeline

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Verify installation
python -m pytest tests/
```

## Configuration

See `config/README.md` for detailed configuration options.

## Usage

### Recommended Workflow

**Step 1: Download animations using browser scripts**

```bash
# 1. Go to https://www.mixamo.com and login
# 2. Open browser console (F12)
# 3. Find your character ID in network tab after downloading one animation
# 4. Copy and run scripts from mixamo_anims_downloader:
#    https://github.com/RydlrCS/mixamo_anims_downloader/blob/main/downloadAll.js
```

**Step 2: Validate and organize downloaded files**

```python
from src.downloader import validate_download
from pathlib import Path

# Validate all downloaded FBX files
downloads = Path("~/Downloads").expanduser()
for fbx_file in downloads.glob("*.fbx"):
    is_valid = validate_download(str(fbx_file))
    print(f"{'✓' if is_valid else '✗'} {fbx_file.name}")

# Move to organized structure
# (Use scripts/01_organize_downloads.py)
```

**Step 3: Generate motion blends**

```bash
python scripts/02_generate_blends.py --config config/blend.yaml
```

**Step 4: Upload to GCS**

```bash
python scripts/03_upload_to_gcs.py \
    --input ./data/seed \
    --bucket gs://your-bucket/mocap/seed/
```

**Step 5: Sync to BigQuery (via Fivetran)**

Configure the motionblend connector in Fivetran dashboard to track metadata.

**Step 6: Export for kijani-spiral NPC engine**

```bash
python scripts/05_export_for_npc.py --config config/export.yaml
```

For detailed integration guide, see [docs/MIXAMO_INTEGRATION.md](docs/MIXAMO_INTEGRATION.md).

### Direct Pipeline Usage (Advanced)

Or run the full pipeline after manual download:

```bash
# After downloading with mixamo_anims_downloader browser script
python scripts/run_pipeline.py \
    --input ~/Downloads/*.fbx \
    --config config/pipeline.yaml
```

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=html

# Type checking
mypy src/

# Linting
flake8 src/ tests/
```

## Contributing

1. Follow PEP 8 coding standards
2. Add comprehensive docstrings to all functions
3. Include type hints for all parameters and return values
4. Add unit tests for new functionality
5. Ensure all quality gates pass before committing

## License

MIT License - See LICENSE file for details

## Related Repositories

- [blendanim](https://github.com/RydlrCS/blendanim) - Single-shot motion blending framework
- [mixamo_anims_downloader](https://github.com/RydlrCS/mixamo_anims_downloader) - Mixamo animation downloader
- [kijani-spiral](https://github.com/RydlrCS/kijani-spiral) - NPC animation engine
- [fivetran_connector_sdk](https://github.com/RydlrCS/fivetran_connector_sdk) - Motionblend connector

## Acknowledgments

- Mixamo for animation library
- GANimator framework for motion synthesis
- Fivetran for data pipeline infrastructure
