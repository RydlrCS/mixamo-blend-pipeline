"""
Mixamo Blend Pipeline

A production-ready pipeline for downloading Mixamo animations, generating motion blends
using the blendanim framework, and syncing metadata to BigQuery for NPC animation systems.

This package provides modular components for each stage of the pipeline:
- downloader: Mixamo animation downloading
- blender: Motion blending with blendanim (GANimator-based)
- uploader: GCS upload utilities
- utils: Logging, validation, and helper functions

See README.md for detailed documentation and usage examples.
"""

__version__ = "0.1.0"
__author__ = "Ted Iro <ted@rydlrcloudservices.com>"

# Package-level imports
from src.utils.logging import setup_logging

# Initialize default logging configuration
setup_logging()
