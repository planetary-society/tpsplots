#!/usr/bin/env python3
"""
s3_sync.py - DEPRECATED: Use `tpsplots s3-sync` instead.

This script is kept for backwards compatibility but will be removed in a future release.
"""

import sys
import warnings


def main():
    warnings.warn(
        "scripts/s3_sync.py is deprecated. Use 'tpsplots s3-sync' instead.",
        DeprecationWarning,
        stacklevel=2,
    )

    # Forward to the new CLI command
    from tpsplots.cli import app

    sys.argv = ["tpsplots", "s3-sync", *sys.argv[1:]]
    app()


if __name__ == "__main__":
    main()
