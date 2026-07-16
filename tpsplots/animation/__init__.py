"""Animated chart rendering for the ``tpsplots animate`` command.

This package must stay cheap to import: nothing here may import
``matplotlib.animation`` or ``imageio_ffmpeg`` at module load time (guarded by
an import-order regression test). The config/easing modules are stdlib-only so
they are re-exported eagerly; only the renderer — which pulls in the heavy
encoder stack — loads lazily via PEP 562 ``__getattr__``.
"""

from tpsplots.animation.config import ResolvedAnimation, resolve_animation
from tpsplots.animation.easing import EASINGS, get_easing

__all__ = [
    "EASINGS",
    "ResolvedAnimation",
    "animate_yaml",
    "get_easing",
    "resolve_animation",
]

_LAZY_EXPORTS = {
    "animate_yaml": "tpsplots.animation.renderer",
}


def __getattr__(name: str):
    module_path = _LAZY_EXPORTS.get(name)
    if module_path is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    import importlib

    return getattr(importlib.import_module(module_path), name)
