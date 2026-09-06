"""Append-only per-level spool for streamed parcel content.

`osm_to_parcel_geometry.extract_parcel_geometry` makes one pass over the PBF
and, for every way/node it reads, tiles it into every requested map level
immediately (it does not hold the whole file's geometry in memory). Content
for a given parcel accumulates in a small in-memory buffer per level and is
flushed to disk once that buffer's item count crosses a threshold -- this is
what keeps peak memory bounded on the full-Australia extract.

Because the same parcel can be touched by ways read at different points in
the pass, and its buffer may already have been flushed in between, the
*same* `(ix, iy)` key can appear in more than one record in the level's
append-only data file. `close()` builds a per-level index that groups every
record's file offset by `(ix, iy)`, sorted by `(iy, ix)` (ascending) --
that's the deterministic order `iter_level` yields in -- and the reader
merges every offset for a key into one content dict, so a parcel appears
exactly once to callers.

On-disk layout::

    <spool_dir>/level_<level>.data   -- append-only pickle stream, one
                                         (ix, iy, content_dict) record per
                                         append. Written only by SpoolWriter.
    <spool_dir>/level_<level>.idx    -- pickled dict:
                                           {"cells": [(ix, iy, [offsets...]), ...]  # sorted by (iy, ix)
                                            "totals": {"parcels": int, "roads": int,
                                                       "backgrounds": int, "names": int}}
                                         Written once, by SpoolWriter.close().

`content_dict` is always ``{"roads": [...], "backgrounds": [...], "names": [...]}``.
"""
from __future__ import annotations

import pickle
from collections import defaultdict
from pathlib import Path
from typing import Callable, Iterator, Optional

_CONTENT_KEYS = ("roads", "backgrounds", "names")


def _empty_content() -> dict:
    return {"roads": [], "backgrounds": [], "names": []}


def _data_path(spool_dir: Path, level: int) -> Path:
    return spool_dir / f"level_{level}.data"


def _idx_path(spool_dir: Path, level: int) -> Path:
    return spool_dir / f"level_{level}.idx"


class SpoolWriter:
    """Single-writer-process append-only spooler, bucketed per level.

    Call `add(level, ix, iy, roads=..., backgrounds=..., names=...)` as
    content is produced; buffers are flushed to disk automatically once a
    level's buffered item count reaches `flush_threshold`, and finally by
    `close()`, which also builds each touched level's index file.
    """

    def __init__(self, spool_dir, flush_threshold: int = 200_000):
        self.spool_dir = Path(spool_dir)
        self.spool_dir.mkdir(parents=True, exist_ok=True)
        self.flush_threshold = flush_threshold
        self._buffers: dict[int, dict[tuple[int, int], dict]] = defaultdict(dict)
        self._buffer_counts: dict[int, int] = defaultdict(int)
        self._files: dict[int, "object"] = {}
        self._levels_seen: set[int] = set()
        self._closed = False

    def _file_for(self, level: int):
        f = self._files.get(level)
        if f is None:
            f = open(_data_path(self.spool_dir, level), "ab")
            self._files[level] = f
        return f

    def add(self, level: int, ix: int, iy: int,
            roads: Optional[list] = None,
            backgrounds: Optional[list] = None,
            names: Optional[list] = None) -> None:
        if self._closed:
            raise RuntimeError("SpoolWriter is closed")
        n_new = len(roads or []) + len(backgrounds or []) + len(names or [])
        if n_new == 0:
            return
        buf = self._buffers[level]
        content = buf.get((ix, iy))
        if content is None:
            content = _empty_content()
            buf[(ix, iy)] = content
        if roads:
            content["roads"].extend(roads)
        if backgrounds:
            content["backgrounds"].extend(backgrounds)
        if names:
            content["names"].extend(names)
        self._buffer_counts[level] += n_new
        if self._buffer_counts[level] >= self.flush_threshold:
            self._flush_level(level)

    def _flush_level(self, level: int) -> None:
        buf = self._buffers.get(level)
        if not buf:
            return
        f = self._file_for(level)
        for (ix, iy), content in buf.items():
            pickle.dump((ix, iy, content), f, protocol=4)
        f.flush()
        buf.clear()
        self._buffer_counts[level] = 0
        self._levels_seen.add(level)

    def flush_all(self) -> None:
        for level in list(self._buffers):
            self._flush_level(level)

    def _finalize_index(self, level: int) -> None:
        data_path = _data_path(self.spool_dir, level)
        by_key: dict[tuple[int, int], list[int]] = defaultdict(list)
        totals = {"parcels": 0, "roads": 0, "backgrounds": 0, "names": 0}
        with open(data_path, "rb") as fh:
            while True:
                pos = fh.tell()
                try:
                    ix, iy, content = pickle.load(fh)
                except EOFError:
                    break
                by_key[(ix, iy)].append(pos)
        cells = []
        for (ix, iy) in sorted(by_key.keys(), key=lambda k: (k[1], k[0])):
            offsets = by_key[(ix, iy)]
            cells.append((ix, iy, offsets))
            totals["parcels"] += 1
        # Compute content totals by replaying (cheap relative to the pass
        # itself; only done once, at the end, per level).
        with open(data_path, "rb") as fh:
            for ix, iy, offsets in cells:
                for off in offsets:
                    fh.seek(off)
                    _, _, content = pickle.load(fh)
                    for key in _CONTENT_KEYS:
                        totals[key] += len(content.get(key, []))
        idx = {"cells": cells, "totals": totals}
        with open(_idx_path(self.spool_dir, level), "wb") as fh:
            pickle.dump(idx, fh, protocol=4)

    def close(self) -> None:
        if self._closed:
            return
        self.flush_all()
        for f in self._files.values():
            f.close()
        for level in sorted(self._levels_seen):
            self._finalize_index(level)
        self._closed = True

    def __enter__(self) -> "SpoolWriter":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


class SpoolReader:
    """Reads a spool directory written by `SpoolWriter`."""

    def __init__(self, spool_dir):
        self.spool_dir = Path(spool_dir)

    def _load_idx(self, level: int) -> Optional[dict]:
        p = _idx_path(self.spool_dir, level)
        if not p.exists():
            return None
        with open(p, "rb") as fh:
            return pickle.load(fh)

    def iter_level(self, level: int) -> Iterator[tuple[int, int, dict]]:
        """Yield `(ix, iy, content)` for every non-empty parcel at `level`,
        in ascending `(iy, ix)` order, with per-parcel content merged."""
        idx = self._load_idx(level)
        if idx is None:
            return
        data_path = _data_path(self.spool_dir, level)
        with open(data_path, "rb") as fh:
            for ix, iy, offsets in idx["cells"]:
                merged = _empty_content()
                for off in offsets:
                    fh.seek(off)
                    _, _, content = pickle.load(fh)
                    for key in _CONTENT_KEYS:
                        merged[key].extend(content.get(key, []))
                yield ix, iy, merged

    def stats(self, level: int) -> dict:
        """Return `{"parcels": int, "roads": int, "backgrounds": int, "names": int}`
        for `level`, or all-zero if the level has no spooled content."""
        idx = self._load_idx(level)
        if idx is None:
            return {"parcels": 0, "roads": 0, "backgrounds": 0, "names": 0}
        return dict(idx["totals"])

    def levels(self) -> list[int]:
        """Levels with an index file in this spool directory."""
        out = []
        for p in sorted(self.spool_dir.glob("level_*.idx")):
            try:
                out.append(int(p.stem.split("_", 1)[1]))
            except (IndexError, ValueError):
                continue
        return sorted(out)
