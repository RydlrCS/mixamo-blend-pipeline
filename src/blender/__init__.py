"""
Blendanim framework integration module.

This module provides a simplified interface for integrating the blendanim
motion blending framework (https://github.com/RydlrCS/blendanim).

NOTE: This module provides a PLACEHOLDER interface. Actual blendanim integration
requires:
- PyTorch 1.13+
- moai framework (https://github.com/moverseai/moai)
- Pre-trained GANimator checkpoints
- CUDA-capable GPU (recommended)

See docs/BLENDANIM_INTEGRATION.md for complete integration guide.
"""

from .blender import (
    BlendConfig,
    BlendResult,
    blend_motions,
    blend_batch,
    load_bvh,
    save_bvh,
)

__all__ = [
    "BlendConfig",
    "BlendResult",
    "blend_motions",
    "blend_batch",
    "load_bvh",
    "save_bvh",
]
