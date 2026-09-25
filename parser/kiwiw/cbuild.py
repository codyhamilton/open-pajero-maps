"""Compile-on-demand build for the C extension and its C unit-test binary
(plan 03, Contract T: "It is built by the same mechanism that builds the
extension.").

One place lists the extension's C sources (`EXT_SOURCES`); a later unit adds
a file by adding one entry. `cenc.py` loads `_cenc.so` through `build_ext()`.
The test binary (`build_test_bin()`) compiles every `parser/kiwiw/ctest/*.c`
file -- each one `#include`s the extension source(s) it exercises directly,
so `static` internals are testable without exporting them, and no source is
compiled twice.

No Python fallback lives here: a missing compiler or a failed compile raises
`BuildError`. (`cenc.py`'s own degrade-to-Python-oracle behaviour on a
missing compiler is unchanged by this unit -- it catches `BuildError` itself;
that fallback is deleted later, by 3C-08/3C-12, not here.)

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
EXT_SOURCES: tuple[Path, ...] = (_HERE / "_cenc.c",)
EXT_SO = _HERE / "_cenc.so"

CTEST_DIR = _HERE / "ctest"
CTEST_BIN = CTEST_DIR / "_ctest_bin"


class BuildError(RuntimeError):
    """No compiler is available, or a source failed to compile."""


def _find_cc() -> str:
    cc = shutil.which("gcc") or shutil.which("cc")
    if cc is None:
        raise BuildError("no C compiler (gcc or cc) found on PATH")
    return cc


def _hash_path(product: Path) -> Path:
    return product.with_name(product.name + ".hash")


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
              flags: tuple[str, ...] = CFLAGS, force: bool = False) -> Path:
    """Build (or reuse) the shared object at `out` from `sources`. Raises
    `BuildError` on a missing compiler or a compile failure; never falls
    back silently -- that is the caller's choice (`cenc.py` today)."""
    if not force and not is_stale(out, sources, flags):
        return out
    cc = _find_cc()
    _compile([cc, *flags, "-shared", *(str(s) for s in sources), "-lm"],
              out, sources, flags)
    return out


def build_test_bin(ctest_dir: Path = CTEST_DIR, out: Path = CTEST_BIN,
                    ext_sources: tuple[Path, ...] = EXT_SOURCES,
                    flags: tuple[str, ...] = CFLAGS, force: bool = False) -> Path:
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
    hashed = compiled + tuple(ext_sources)
    if not force and not is_stale(out, hashed, flags):
        return out
    cc = _find_cc()
    _compile([cc, *flags, *(str(s) for s in compiled), "-lm"], out, hashed, flags)
    return out
