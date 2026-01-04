"""
Mixamo animation downloader module.

This module provides utilities for downloading animations from Mixamo,
integrating with the mixamo_anims_downloader repository.

Exports:
    download_animation: Download a single animation from Mixamo
    download_batch: Download multiple animations in batch
    validate_download: Verify downloaded file integrity
"""

from src.downloader.downloader import download_animation, download_batch, validate_download

__all__ = ["download_animation", "download_batch", "validate_download"]
