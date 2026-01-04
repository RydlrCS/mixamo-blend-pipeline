# Mixamo Integration Guide

## Overview

The [mixamo_anims_downloader](https://github.com/RydlrCS/mixamo_anims_downloader) repository provides browser-based JavaScript scripts for downloading animations from Mixamo. This document explains how to use it with the mixamo-blend-pipeline.

## Important Note

**mixamo_anims_downloader is NOT a Python library** - it's a collection of JavaScript scripts designed to run in the browser console on mixamo.com.

## Integration Strategies

### Strategy 1: Manual Download (Current Recommended Approach)

Use the browser scripts to download animations, then use our pipeline for processing:

1. **Download animations using mixamo_anims_downloader**:
   ```bash
   # 1. Go to https://mixamo.com and login
   # 2. Open browser console (F12)
   # 3. Get character ID from network tab after downloading one animation
   # 4. Use downloadAll.js script to download all animations
   ```

2. **Organize downloaded files**:
   ```bash
   # Create proper directory structure
   mkdir -p ./data/seed
   mv ~/Downloads/*.fbx ./data/seed/
   ```

3. **Use our pipeline for upload and tracking**:
   ```python
   from src.uploader import upload_to_gcs
   from src.downloader import validate_download
   
   # Validate all downloads
   for file in Path("./data/seed").glob("*.fbx"):
       is_valid = validate_download(str(file))
       print(f"{file.name}: {'✓' if is_valid else '✗'}")
   
   # Upload to GCS
   upload_to_gcs("./data/seed", "gs://your-bucket/mocap/seed/")
   ```

### Strategy 2: Automated Browser Automation (Advanced)

Use Selenium/Playwright to automate the browser-based download:

```python
# Future implementation
from selenium import webdriver
from src.downloader import download_animation

# This would automate the browser script execution
# Not currently implemented - requires browser automation
```

### Strategy 3: Direct API Implementation (Most Complex)

Reverse-engineer Mixamo API and implement in Python:

```python
# This requires authentication token extraction and API reverse engineering
# Not currently implemented - mixamo_anims_downloader uses browser tokens
```

## Mixamo API Details (from mixamo_anims_downloader)

The JavaScript scripts use these Mixamo API endpoints:

### Authentication
```javascript
const bearer = localStorage.access_token  // Retrieved from browser session
```

### Key Endpoints
1. **List Animations**: `GET /api/v1/products?page={page}&limit=96&type=Motion`
2. **Get Product Details**: `GET /api/v1/products/{animId}?character_id={characterId}`
3. **Export Animation**: `POST /api/v1/animations/export`
4. **Monitor Export**: `GET /api/v1/characters/{characterId}/monitor`
5. **Upload Character**: `POST /api/v1/characters`

### Export Parameters
```javascript
{
  preferences: {
    format: "fbx7_2019",  // or "bvh", "dae_mixamo"
    skin: "true",
    fps: "30",
    reducekf: "0"  // reduce keyframes
  },
  product_name: "animation_name",
  type: "Motion"
}
```

## Current Pipeline Implementation

Our `src/downloader/downloader.py` module is designed as a **wrapper** that:

1. **Validates downloaded files** - Ensures FBX/BVH files are valid
2. **Organizes file structure** - Creates proper directory layout
3. **Tracks download metadata** - Records file sizes, timestamps
4. **Integrates with pipeline** - Connects to blendanim and GCS upload

### Usage with Manual Downloads

```python
from src.downloader import download_batch, validate_download
from pathlib import Path

# After using mixamo_anims_downloader browser script
downloads_dir = Path("~/Downloads").expanduser()
output_dir = "./data/seed"

# Find all downloaded animations
fbx_files = list(downloads_dir.glob("*.fbx"))
print(f"Found {len(fbx_files)} FBX files")

# Validate and organize
configs = [
    {
        "animation_id": file.stem,  # Use filename as ID
        "output_filename": file.name
    }
    for file in fbx_files
]

# Move to organized structure
for file in fbx_files:
    target = Path(output_dir) / file.name
    target.parent.mkdir(parents=True, exist_ok=True)
    file.rename(target)
    
    # Validate
    is_valid = validate_download(str(target))
    print(f"{'✓' if is_valid else '✗'} {file.name}")
```

## Future Implementation: Direct API

To implement direct Mixamo API access in Python, we would need to:

1. **Extract Bearer Token**:
   ```python
   # Manual: Copy from browser localStorage.access_token
   # Automated: Use Selenium to login and extract token
   ```

2. **Implement API Client**:
   ```python
   class MixamoAPIClient:
       def __init__(self, bearer_token: str):
           self.bearer = bearer_token
           self.base_url = "https://www.mixamo.com/api/v1"
       
       def list_animations(self, page: int = 1) -> dict:
           # Implement pagination
           pass
       
       def export_animation(self, character_id: str, anim_id: str) -> str:
           # Implement export request
           pass
       
       def monitor_export(self, character_id: str) -> str:
           # Poll until complete, return download URL
           pass
   ```

3. **Handle Authentication**:
   - Mixamo requires browser-based OAuth login
   - Bearer token expires periodically
   - Would need to implement token refresh

## Recommended Workflow

For now, use this hybrid approach:

```bash
# 1. Download using browser script
# (Use downloadAll.js from mixamo_anims_downloader)

# 2. Organize with our pipeline
python scripts/01_organize_downloads.py \
    --source ~/Downloads \
    --output ./data/seed \
    --validate

# 3. Upload to GCS
python scripts/03_upload_to_gcs.py \
    --input ./data/seed \
    --bucket gs://your-bucket/mocap/seed/

# 4. Run blending pipeline
python scripts/02_generate_blends.py \
    --config config/blend.yaml
```

## References

- [mixamo_anims_downloader](https://github.com/RydlrCS/mixamo_anims_downloader) - Browser scripts
- [Mixamo](https://www.mixamo.com) - Adobe's animation library
- [blendanim](https://github.com/RydlrCS/blendanim) - Motion blending framework
