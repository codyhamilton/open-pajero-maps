"""`pointers`: an out-of-buffer mfde entry (index >= 3) must point at bytes
that decode as a Map Frame, not merely at an offset inside the file."""
from __future__ import annotations

import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from harness.checks.decode import _check_mfde_entry, _decodes_as_map_frame

SECTOR = 2048
LOGICAL = 512
FRAME_SIZE = 1000
# sector index 2, logical sub-index 0 -> byte offset 4096
RAW_OFF = 2 << 8
FILE_SIZE = 8192


def _valid_header() -> bytes:
    # llpid lat/lon 3-byte values near zero, llcode 0, nregion 0.
    return bytes(36)


def _file(target: bytes) -> io.BytesIO:
    buf = bytearray(FILE_SIZE)
    buf[4096:4096 + len(target)] = target
    return io.BytesIO(bytes(buf))


def _check(fh):
    return _check_mfde_entry(5, RAW_OFF, 10, FRAME_SIZE, FILE_SIZE, SECTOR,
                             LOGICAL, [0, 0], fh)


def test_target_that_is_a_map_frame_passes():
    assert _check(_file(_valid_header())) is None


def test_target_into_non_frame_bytes_fails():
    # 0xFF everywhere: llpid out of range and nregion 0xFFFF.
    err = _check(_file(b"\xff" * 64))
    assert err is not None and "not a Map Frame" in err


def test_target_near_eof_fails():
    assert _decodes_as_map_frame(_file(b""), FILE_SIZE - 10, FILE_SIZE) is not None


def test_in_file_offset_alone_no_longer_passes():
    # Inside the file, but bytes are 0xA5 poison, not a frame.
    assert _check(_file(b"\xa5" * 64)) is not None
