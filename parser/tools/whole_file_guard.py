#!/usr/bin/env python3
"""Refuse whole-file materialization of large Maps discs / spool data (plan 25).

Plan-14 triage and similar OpenCode paths must stream or window large inputs.
``refuse_whole_file_read`` raises if a caller is about to ``read()`` /
``read_bytes()`` a file at or above ``WHOLE_FILE_REFUSE_BYTES`` (default 64 MiB).
ALLDATA.KWI (~1.5–1.6 GiB) and spool ``level_0.data`` (~4.2 GiB) therefore
cannot be silently pulled into anon RSS through a whole-file read helper.
"""
from __future__ import annotations

from pathlib import Path

# 64 MiB: large enough for spool *index* files (~10 MiB L0) and small dumps;
# far below ALLDATA / level_0.data. Override via env MAPS_WHOLE_FILE_REFUSE_BYTES.
import os

WHOLE_FILE_REFUSE_BYTES = int(os.environ.get("MAPS_WHOLE_FILE_REFUSE_BYTES", str(64 * 1024 * 1024)))


class WholeFileReadError(RuntimeError):
    """Raised when a whole-file read would exceed the refuse threshold."""


def refuse_whole_file_read(path, *, size: int | None = None,
                           limit: int = WHOLE_FILE_REFUSE_BYTES) -> int:
    """Return file size if below ``limit``; else raise ``WholeFileReadError``."""
    p = Path(path)
    n = int(size) if size is not None else p.stat().st_size
    if n >= limit:
        raise WholeFileReadError(
            f"refuse whole-file read of {p} ({n} bytes >= limit {limit}); "
            f"use pread/windowed/leaf decode instead (plan 25)"
        )
    return n


def read_bytes_guarded(path, *, limit: int = WHOLE_FILE_REFUSE_BYTES) -> bytes:
    """``Path.read_bytes`` after ``refuse_whole_file_read``."""
    p = Path(path)
    refuse_whole_file_read(p, limit=limit)
    return p.read_bytes()
