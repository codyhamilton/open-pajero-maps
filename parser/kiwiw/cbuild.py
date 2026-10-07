"""Compile-on-demand build for the C extension and its C unit-test binary
(plan 03, Contract T: "It is built by the same mechanism that builds the
extension.").

One place lists the extension's C sources (`EXT_SOURCES`); a later unit adds
a file by adding one entry. `cenc.py` loads `_cenc.so` through `build_ext()`.
The test binary (`build_test_bin()`) compiles every `parser/kiwiw/ctest/*.c`
file -- each one `#include`s the extension source(s) it exercises directly,
so `static` internals are testable without exporting them, and no source is
compiled twice.

The C library is mandatory: a missing compiler or a failed compile raises
`BuildError`. The assembly binding in `cenc.py` also raises `BuildError` if
the library cannot be opened or lacks a required assembly symbol. No Python
fallback remains.

Staleness: a sha256 over every source's bytes plus the flag list, stored
beside the product as `<product>.hash`. Content hash, not mtime, because a
worktree checkout or `git stash` can leave source mtimes newer than a stale
product without the content having changed (or vice versa) -- content hash
is correct either way and costs one read of files we compile anyway. Build
is atomic (temp file in the product's own directory, then `os.replace`), so
concurrent builders never observe a partial product; the hash file is
written only after the rename, so a reader can at worst see a valid old
product paired with a hash that says "stale" and rebuild redundantly, never
a mismatched (product, hash) pair.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

_HERE = Path(__file__).parent

# Flags shared by every product this module builds (today's flags, unchanged).
CFLAGS: tuple[str, ...] = ("-O2", "-ffp-contract=off", "-fPIC")

# The extension's C sources, one place. 3C-06/3C-07 append E1/E2 sources here.
EXT_SOURCES: tuple[Path, ...] = (_HERE / "_cenc.c", _HERE / "_e1.c", _HERE / "_e2.c",
                                   _HERE / "_d1.c", _HERE / "_k1.c", _HERE / "_k1_bg.c",
                                   _HERE / "_k1_cmp.c")
EXT_SO = _HERE / "_cenc.so"

CTEST_DIR = _HERE / "ctest"
CTEST_BIN = CTEST_DIR / "_ctest_bin"


class BuildError(RuntimeError):
    """C compilation failed, or the assembly library could not be loaded."""


def _find_cc() -> str:
    cc = shutil.which("gcc") or shutil.which("cc")
    if cc is None:
        raise BuildError("no C compiler (gcc or cc) found on PATH")
    return cc


def _hash_path(product: Path) -> Path:
    return product.with_name(product.name + ".hash")

def _ext_headers() -> tuple[Path, ...]:
    """Every `*.h` beside the extension sources, evaluated per call so a new
    header is picked up without editing a list."""
    return tuple(sorted(_HERE.glob("*.h")))


def _content_hash(sources: tuple[Path, ...], flags: tuple[str, ...]) -> str:
    h = hashlib.sha256()
    for p in sorted(sources, key=str):
        h.update(str(p).encode())
        h.update(b"\0")
        h.update(p.read_bytes())
    h.update("\0".join(flags).encode())
    return h.hexdigest()


def is_stale(product: Path, sources: tuple[Path, ...], flags: tuple[str, ...]) -> bool:
    if not product.exists():
        return True
    hp = _hash_path(product)
    if not hp.exists():
        return True
    try:
        return hp.read_text().strip() != _content_hash(sources, flags)
    except OSError:
        return True


def _compile(args: list[str], product: Path, sources: tuple[Path, ...],
             flags: tuple[str, ...]) -> None:
    product.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_s = tempfile.mkstemp(suffix=product.suffix, dir=str(product.parent))
    os.close(fd)
    tmp = Path(tmp_s)
    try:
        proc = subprocess.run(args + ["-o", str(tmp)], capture_output=True, text=True)
        if proc.returncode != 0:
            raise BuildError(
                f"compile failed ({' '.join(args)}):\n{proc.stdout}{proc.stderr}")
        os.replace(tmp, product)
    finally:
        if tmp.exists():
            tmp.unlink()
    # Written only after the atomic rename above (see module docstring).
    _hash_path(product).write_text(_content_hash(sources, flags))


def build_ext(sources: tuple[Path, ...] = EXT_SOURCES, out: Path = EXT_SO,
              flags: tuple[str, ...] = CFLAGS, force: bool = False,
              headers: tuple[Path, ...] | None = None) -> Path:
    """Build (or reuse) the shared object at `out` from `sources`. Raises
    `BuildError` on a missing compiler or a compile failure. The C library
    is mandatory; no Python fallback remains.

    `headers` are hashed (so a header-only edit invalidates the product) but
    are not passed to the compiler; `None` means every `*.h` beside the
    extension sources (`_ext_headers()`)."""
    if headers is None:
        headers = _ext_headers()
    hashed = tuple(sources) + tuple(headers)
    if not force and not is_stale(out, hashed, flags):
        return out
    cc = _find_cc()
    _compile([cc, *flags, "-shared", *(str(s) for s in sources), "-lm"],
              out, hashed, flags)
    return out


def build_test_bin(ctest_dir: Path = CTEST_DIR, out: Path = CTEST_BIN,
                    ext_sources: tuple[Path, ...] = EXT_SOURCES,
                    flags: tuple[str, ...] = CFLAGS, force: bool = False,
                    headers: tuple[Path, ...] | None = None) -> Path:
    """Build (or reuse) the layer-(b) test executable from every
    `ctest_dir/*.c` file (each pulls in the extension source(s) it tests via
    `#include`, so nothing here is compiled twice). Raises `BuildError` --
    including on a missing compiler -- with no fallback: layer (b) has no
    Python double to fall back to.

    Staleness is hashed over the compiled `.c` files *and* `ext_sources`:
    a `ctest/*.c` file's own bytes don't change when it `#include`s an
    edited `_cenc.c`, so the extension sources must be in the hash too or
    an edit there would never be seen as invalidating the test binary."""
    compiled = tuple(sorted(ctest_dir.glob("*.c")))
    if not compiled:
        raise BuildError(f"no C test sources found in {ctest_dir}")
    if headers is None:
        headers = _ext_headers()
    hashed = compiled + tuple(ext_sources) + tuple(headers)
    if not force and not is_stale(out, hashed, flags):
        return out
    cc = _find_cc()
    _compile([cc, *flags, *(str(s) for s in compiled), "-lm"], out, hashed, flags)
    return out


# ---------------------------------------------------------------- Plan 48 Phase 2
# Output-neutral EO census: counters live in worker TLS inside `_cenc.c`.
# Production builds dlsym these symbols from the shared object and write a
# sidecar JSON beside ALLDATA (disc bytes unchanged).


EO_STATS_KEYS: tuple[str, ...] = (
    "eo_clip_entries", "eo_clip_complex",
    "decline_intersect", "decline_cut", "decline_connect",
    "decline_walk_used", "decline_walk_bound", "decline_walk_nobest",
    "decline_grow", "walk_starts",
)


def bind_eo_stats(lib) -> None:
    """Bind `kw__eo_stats_get` / `kw__eo_stats_reset` on a loaded CDLL (idempotent)."""
    import ctypes
    if getattr(lib, "_eo_stats_bound", False):
        return
    lib.kw__eo_stats_reset.argtypes = []
    lib.kw__eo_stats_reset.restype = None
    lib.kw__eo_stats_get.argtypes = (
        [ctypes.POINTER(ctypes.c_int64)] * 10 + [ctypes.POINTER(ctypes.c_double)]
    )
    lib.kw__eo_stats_get.restype = None
    lib._eo_stats_bound = True


def eo_stats_reset(lib) -> None:
    bind_eo_stats(lib)
    lib.kw__eo_stats_reset()


def eo_stats_get(lib) -> dict:
    """Snapshot the calling thread/process's EO census counters."""
    import ctypes
    bind_eo_stats(lib)
    vals = [ctypes.c_int64() for _ in range(10)]
    margin = ctypes.c_double()
    lib.kw__eo_stats_get(*[ctypes.byref(v) for v in vals], ctypes.byref(margin))
    out = {k: int(v.value) for k, v in zip(EO_STATS_KEYS, vals)}
    out["walk_min_margin"] = float(margin.value)
    out["declines_total"] = sum(out[k] for k in EO_STATS_KEYS if k.startswith("decline_"))
    out["guard_hits"] = int(out["decline_walk_used"])  # :885-class already-used
    return out


def merge_eo_stats(dst: dict, src: dict) -> None:
    """Sum additive EO census fields; keep the minimum walk_min_margin (>0 preferred)."""
    for k in EO_STATS_KEYS:
        dst[k] = int(dst.get(k, 0)) + int(src.get(k, 0))
    dst["declines_total"] = sum(dst[k] for k in EO_STATS_KEYS if k.startswith("decline_"))
    dst["guard_hits"] = int(dst["decline_walk_used"])
    sm = float(src.get("walk_min_margin", -1.0))
    dm = float(dst.get("walk_min_margin", -1.0))
    if sm < 0:
        pass
    elif dm < 0 or sm < dm:
        dst["walk_min_margin"] = sm
    else:
        dst["walk_min_margin"] = dm


def empty_eo_stats() -> dict:
    out = {k: 0 for k in EO_STATS_KEYS}
    out["walk_min_margin"] = -1.0
    out["declines_total"] = 0
    out["guard_hits"] = 0
    return out


def write_eo_census_sidecar(path: Path | str, stats: dict, *, meta: dict | None = None) -> Path:
    """Write `eo_census.json` beside a build product. Does not touch disc bytes."""
    import json
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"eo_census": dict(stats)}
    if meta:
        payload["meta"] = meta
    path.write_text(json.dumps(payload, indent=2) + "\n")
    return path
