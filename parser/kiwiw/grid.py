"""Reference LMR grid parameters, loaded from checked-in `parser/refdata/`.

This module never reads the mounted reference disc (see
docs/design/target-disc.md, "Grid contract": "Those parameters are
checked-in data derived once from `R`; a build never reads the mounted
reference."). `parser/extract_reference_data.py` is the only code that
reads the disc; it writes `parser/refdata/grid.json` and
`parser/refdata/mht29_frame.bin`, which `ReferenceGrid` loads.

Derivations here (grid `nx`/`ny`, `cell_lat`/`cell_lon`, `lon_span`) mirror
`kiwiw.mesh.locate_parcel()` / `kiwiw.mesh._lon_span()` exactly, so a level's
`ReferenceGrid.level(n)` matches what a disc-reading decode would compute.

This module imports only `kiwiw.model` and stdlib.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .model import LevelMgmtRecord

_PACKAGE_DIR = Path(__file__).resolve().parent
_REFDATA_DIR = _PACKAGE_DIR.parent / "refdata"
DEFAULT_GRID_JSON = _REFDATA_DIR / "grid.json"


def _lon_span(lo: float, hi: float) -> float:
    """Same wrap rule as `kiwiw.mesh._lon_span()`: a negative raw span means
    the coverage box crosses the antimeridian."""
    span = hi - lo
    return span + 360.0 if span < 0 else span


@dataclass
class LevelGrid:
    """One level's grid, matching `osm_to_parcel_geometry.TileGrid`'s
    cell-size derivation (`disc_*_span / n*`)."""
    level: int
    nx: int
    ny: int
    cell_lat: float
    cell_lon: float
    lmr: dict  # raw LevelMgmtRecord fields as loaded from grid.json


def _grid_dims(lmr: dict) -> tuple[int, int]:
    """Reproduce `kiwiw.mesh.locate_parcel()`'s nx/ny derivation:
    (1+n_blocksets) * (1+n_blocks) * (1+n_parcels[0]) per axis."""
    nx = (1 + lmr["n_blocksets_lng"]) * (1 + lmr["n_blocks_lng"]) * (1 + lmr["n_parcels_lng"][0])
    ny = (1 + lmr["n_blocksets_lat"]) * (1 + lmr["n_blocks_lat"]) * (1 + lmr["n_parcels_lat"][0])
    return nx, ny


@dataclass
class ReferenceGrid:
    """Parsed `grid.json`: reference-disc coverage box, PDMDH header
    fields, and per-level LMR grid parameters."""
    data: dict
    _refdata_dir: Path

    @classmethod
    def load(cls, path: Optional[str] = None) -> "ReferenceGrid":
        """Load `grid.json`. `path` defaults to `parser/refdata/grid.json`
        resolved relative to this package -- never the current working
        directory -- so callers get the same data regardless of cwd."""
        p = Path(path) if path is not None else DEFAULT_GRID_JSON
        with open(p, "r") as f:
            data = json.load(f)
        return cls(data=data, _refdata_dir=p.resolve().parent)

    @property
    def coverage(self) -> dict:
        return self.data["coverage"]

    @property
    def lat_span(self) -> float:
        c = self.coverage
        return c["lat_hi"] - c["lat_lo"]

    @property
    def lon_span(self) -> float:
        c = self.coverage
        return _lon_span(c["lon_lo"], c["lon_hi"])

    @property
    def pdmdh(self) -> dict:
        return self.data["pdmdh"]

    def _level_dict(self, n: int) -> dict:
        for lvl in self.data["levels"]:
            if lvl["level"] == n:
                return lvl
        raise ValueError(f"no LMR for level {n} in grid.json; available: "
                          f"{[l['level'] for l in self.data['levels']]}")

    def level(self, n: int) -> LevelGrid:
        lmr = self._level_dict(n)
        nx, ny = _grid_dims(lmr)
        return LevelGrid(
            level=n,
            nx=nx,
            ny=ny,
            cell_lat=self.lat_span / ny,
            cell_lon=self.lon_span / nx,
            lmr=lmr,
        )

    def to_level_mgmt_record(self, n: int) -> LevelMgmtRecord:
        """Build the `LevelMgmtRecord` for level `n`, field order and all,
        so downstream writers (unit 12's assembler) don't have to
        re-derive it from `grid.json`."""
        g = self.level(n)
        fields = dict(g.lmr)
        fields["grid_nx"] = g.nx
        fields["grid_ny"] = g.ny
        return LevelMgmtRecord(**fields)

    def mht29_frame_bytes(self) -> bytes:
        """The record-29 management-header frame, carried byte-identical
        from `R` (docs/design/target-disc.md, "Copy-through management
        data")."""
        return (self._refdata_dir / "mht29_frame.bin").read_bytes()
