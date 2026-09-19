"""Frame spill file for the streaming ALLDATA.KWI assembler (plan 02).

Encoded Map Frames are appended to one temp file as they are produced and
represented by a `FrameRef` (offset, length) so the assembler holds only an
index in memory. A `FrameRef` supports `len()` and `.read()`; `bytes` frames
and `FrameRef`s are interchangeable everywhere the assembler accepts frames.
"""
from __future__ import annotations

import os
import tempfile


class FrameRef:
    __slots__ = ("spill", "offset", "length")

    def __init__(self, spill: "FrameSpill", offset: int, length: int):
        self.spill = spill
        self.offset = offset
        self.length = length

    def __len__(self) -> int:
        return self.length

    def read(self) -> bytes:
        return self.spill.read(self.offset, self.length)


class FrameSpill:
    def __init__(self, directory: str | None = None):
        self._fh = tempfile.NamedTemporaryFile(prefix="kwi_spill_", dir=directory,
                                               delete=True)
        self._end = 0

    def add(self, data: bytes) -> FrameRef:
        self._fh.seek(self._end)
        self._fh.write(data)
        ref = FrameRef(self, self._end, len(data))
        self._end += len(data)
        return ref

    def read(self, offset: int, length: int) -> bytes:
        self._fh.flush()
        return os.pread(self._fh.fileno(), length, offset)

    def close(self) -> None:
        self._fh.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def frame_bytes(frame) -> bytes:
    """Resolve a frame that is either raw bytes or a `FrameRef`."""
    return frame if isinstance(frame, (bytes, bytearray)) else frame.read()
