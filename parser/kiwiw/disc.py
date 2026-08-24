"""Top-level convenience wrapper: open ALLDATA.KWI, parse the volume
header + Parcel Data Management tables, and locate/decode parcels by
coordinate.
"""
from __future__ import annotations

from dataclasses import dataclass

from .mesh import locate_parcel
from .model import Parcel
from .parcel import decode_parcel
from .volume import (
    MhrEntry,
    Pdmdh,
    VolumeHeader,
    getsector,
    parse_mhr_table,
    parse_pdmdh,
    parse_volume_header,
)

DATAVOL_SIZE = 2048
MHR_COUNT = 34
MHR_SIZE = 18


class AllData:
    def __init__(self, path: str):
        self._fh = open(path, "rb")
        header_buf = self._fh.read(DATAVOL_SIZE)
        self.header: VolumeHeader = parse_volume_header(header_buf)
        self.sector_sz = self.header.sector_size
        self.logical_sz = self.header.logical_sector_size

        mhr_buf = self._fh.read(MHR_COUNT * MHR_SIZE)
        self.mhr: list[MhrEntry] = parse_mhr_table(mhr_buf)

        # Record 1 (index 0) is the Parcel-related Data Management Record
        # (PDMDH + LMR + BSMR + BMT tables) for the main map / route
        # guidance frame -- see kiwiread.c `showalldata()`, `zdat[0]`.
        prdm = self.mhr[0]
        if prdm.name:
            raise NotImplementedError(
                "PDMDH record has a file-name reference instead of an "
                "inline DSA; file-based parcel management records "
                "(bmtfile_t) aren't implemented."
            )
        off = getsector(prdm.dsa, self.sector_sz, self.logical_sz)
        self._fh.seek(off)
        self._zdat0 = self._fh.read(prdm.size * self.logical_sz)
        self.pdmdh: Pdmdh = parse_pdmdh(self._zdat0)

    def close(self):
        self._fh.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    @property
    def levels(self):
        return self.pdmdh.levels

    def find_parcel(self, lat: float, lon: float, level: int = 0) -> Parcel | None:
        loc = locate_parcel(
            self._fh, self._zdat0, self.pdmdh, level, lat, lon,
            self.sector_sz, self.logical_sz,
        )
        if loc is None:
            return None
        off = getsector(loc.sector_addr, self.sector_sz, self.logical_sz)
        self._fh.seek(off)
        mapdata = self._fh.read(loc.size_logical_sectors * self.logical_sz)
        return decode_parcel(loc, mapdata)
