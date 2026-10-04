#!/usr/bin/env python3
"""K1 failure-dump triage (plan 04, Phase 3, brief 3-05).

Turns a `--dump-failures` directory (the 3-02/3-03 layout described by
`dump_manifest.json`) into the tables the Phase 3 cause table is built from, and
PROVES a proposed set of rules assigns every dump row to exactly one cause.

Offline: it reads dump files through ``kiwiw.dump_io`` bounded windows (default 65,536
rows) and loads no C library.  There is no Python loop over rows; the loops that remain
are over rules, kinds, levels and groups (the report rows).  Retained aggregation keys
own independent storage (no void-scalar views into unique arrays).

Subcommands
    summary   --dump DIR --out OUT
    classify  --dump DIR --rules RULES.json --out OUT
    enumerate --dump DIR --assign OUT --rule ID --out FILE

All output is byte-identical across runs (sorted keys, `%.6f` floats).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np

_PARSER = Path(__file__).resolve().parent.parent
if str(_PARSER) not in sys.path:
    sys.path.insert(0, str(_PARSER))
from kiwiw import dump_io  # noqa: E402

CHUNK = dump_io.DEFAULT_WINDOW  # bounded windows (was 2_000_000 whole-file memmap slices)
NO_RULE = 0xFFFF
INT32_MIN = np.iinfo(np.int32).min
CAUSES = ("checker", "build", "spool")
_OPERATORS = {"==", "!=", "<", "<=", ">", ">=", "in", "isnan", "notnan"}
_NP_TYPE = {"f64": "<f8", "i32": "<i4", "u16": "<u2", "u8": "u1"}

# summary needs every diagnostic column; a manifest without them cannot be triaged.
_SUMMARY_COLUMNS = (
    "level", "ix", "iy", "code", "shape", "vert",
    "p0", "p1", "p2", "p3", "p4", "p5", "p6",
    "onb", "d_any", "in_eo_same", "in_wn_same", "in_eo_any",
    "src_ix", "src_iy", "src_rec", "src_tall", "src_nv", "src_maxseg", "d_src",
)
_GROUP_COLS = ("level", "ix", "iy", "code", "p0", "p1", "p2", "p3", "p4", "p5", "p6",
               "shape")
_SRC_COLS = ("level", "src_ix", "src_iy", "src_rec", "src_tall", "src_nv",
             "src_maxseg", "code")
_GROUPS_HEADER = ("level", "ix", "iy", "type", "p0", "p1", "p2", "p3", "p4", "p5", "p6",
                  "shape", "rows", "first_vert", "last_vert", "d_src_min", "d_src_max")
_BY_SRC_HEADER = ("kind", "level", "src_ix", "src_iy", "src_rec", "src_tall", "src_nv",
                  "src_maxseg", "type", "rows", "groups")
_BY_LT_HEADER = ("kind", "level", "type", "rows", "onb_ne0", "in_eo_same_eq1",
                 "in_wn_same_eq1", "in_eo_any_eq1", "d_any_notnan", "src_sentinel")
_BY_SRC_CAP = 5000


class BadRules(Exception):
    """The rules file is malformed; `classify` exits 2 before reading any rows."""


# ------------------------------------------------------------------ dump layout

def _load_manifest(dump: Path):
    """Manifest fields, per-kind info and the aligned numpy row dtype (3-03 layout)."""
    manifest = json.loads((dump / "dump_manifest.json").read_text())
    fields = manifest["fields"]
    kinds = manifest["kinds"]
    dtype = np.dtype([(f["name"], _NP_TYPE[f["type"]]) for f in fields], align=True)
    for kind, info in kinds.items():
        if int(info.get("row_size", -1)) != dtype.itemsize:
            raise ValueError(f"manifest kind {kind}: row_size {info.get('row_size')} "
                             f"!= computed {dtype.itemsize}")
    return manifest, fields, kinds, dtype


def _own_key(void_or_row) -> np.ndarray:
    """Independent structured copy; does not keep unique-array storage alive."""
    a = np.asarray(void_or_row)
    return np.frombuffer(bytearray(a.tobytes()), dtype=a.dtype).reshape(())


def _f(x) -> str:
    return "%.6f" % float(x)


def _canon_f(x: np.ndarray) -> np.ndarray:
    """A float grouping key: NaN sentinels must compare equal, so map them to -1.0."""
    return np.where(np.isnan(x), np.float64(-1.0), x)


def _min2(a: float, b: float) -> float:
    if a != a:
        return b
    if b != b:
        return a
    return a if a < b else b


def _max2(a: float, b: float) -> float:
    if a != a:
        return b
    if b != b:
        return a
    return a if a > b else b


def _empty_like(dtype, n):
    # zeroed, so the padding bytes of the aligned key are deterministic: np.unique
    # dedups records by their bytes, and uninitialised padding makes it non-deterministic
    return np.zeros(n, dtype)


def _fill(k: np.ndarray, block, names) -> None:
    for n in names:
        k[n] = block[n]


def _group_key(block, rule=None) -> np.ndarray:
    fields = list(zip(_GROUP_COLS, ("u1", "i4", "i4", "i4",
                                    "u2", "u2", "u2", "u2", "u2", "u2", "u2", "i4")))
    if rule is not None:
        fields = [("rule", "u2")] + fields
    dt = np.dtype(fields, align=True)
    k = _empty_like(dt, len(block))
    if rule is not None:
        k["rule"] = rule
    _fill(k, block, [n for n in dt.names if n != "rule"])
    return k


def _level_type_key(block) -> np.ndarray:
    dt = np.dtype([("level", "u1"), ("code", "i4")], align=True)
    k = _empty_like(dt, len(block))
    _fill(k, block, dt.names)
    return k


def _src_key(block) -> np.ndarray:
    dt = np.dtype(list(zip(_SRC_COLS,
                           ("u1", "i4", "i4", "i4", "u1", "i4", "f8", "i4"))), align=True)
    k = _empty_like(dt, len(block))
    _fill(k, block, ("level", "src_ix", "src_iy", "src_rec", "src_tall", "src_nv",
                     "code"))
    k["src_maxseg"] = _canon_f(np.asarray(block["src_maxseg"]))
    return k


def _composite_key(block) -> np.ndarray:
    fields = list(zip(_SRC_COLS + ("ix", "iy", "p0", "p1", "p2", "p3", "p4", "p5", "p6",
                                   "shape"),
                      ("u1", "i4", "i4", "i4", "u1", "i4", "f8", "i4",
                       "i4", "i4", "u2", "u2", "u2", "u2", "u2", "u2", "u2", "i4")))
    dt = np.dtype(fields, align=True)
    k = _empty_like(dt, len(block))
    _fill(k, block, [n for n in dt.names if n != "src_maxseg"])
    k["src_maxseg"] = _canon_f(np.asarray(block["src_maxseg"]))
    return k


# ------------------------------------------------------------------ grouping

def _reduce(key, vert, dsrc):
    """Unique key, per-group row counts and vert/d_src min/max (NaN-aware)."""
    ukey, inv, counts = np.unique(key, return_inverse=True, return_counts=True)
    order = np.argsort(inv, kind="stable")
    starts = np.concatenate(([0], np.cumsum(counts)[:-1]))
    sv = vert[order]
    vmin = np.minimum.reduceat(sv, starts)
    vmax = np.maximum.reduceat(sv, starts)
    sd = dsrc[order]
    dmin = np.minimum.reduceat(np.where(np.isnan(sd), np.inf, sd), starts)
    dmax = np.maximum.reduceat(np.where(np.isnan(sd), -np.inf, sd), starts)
    dmin = np.where(np.isinf(dmin), np.nan, dmin)
    dmax = np.where(np.isinf(dmax), np.nan, dmax)
    return ukey, counts, vmin, vmax, dmin, dmax


def _merge_group(acc, ukey, counts, vmin, vmax, dmin, dmax):
    """Merge one chunk's groups into a dict keyed by the raw key bytes."""
    sz = ukey.dtype.itemsize
    raw = ukey.tobytes()
    for i in range(len(counts)):
        kb = raw[i * sz:(i + 1) * sz]
        e = acc.get(kb)
        if e is None:
            acc[kb] = [_own_key(ukey[i]), int(counts[i]), int(vmin[i]), int(vmax[i]),
                       float(dmin[i]), float(dmax[i])]
        else:
            e[1] += int(counts[i])
            if int(vmin[i]) < e[2]:
                e[2] = int(vmin[i])
            if int(vmax[i]) > e[3]:
                e[3] = int(vmax[i])
            e[4] = _min2(e[4], float(dmin[i]))
            e[5] = _max2(e[5], float(dmax[i]))


def _merge_rows(acc, ukey, counts):
    sz = ukey.dtype.itemsize
    raw = ukey.tobytes()
    for i in range(len(counts)):
        kb = raw[i * sz:(i + 1) * sz]
        e = acc.get(kb)
        if e is None:
            acc[kb] = [_own_key(ukey[i]), int(counts[i])]
        else:
            e[1] += int(counts[i])


# ------------------------------------------------------------------ output

def _write(path: Path, header, lines) -> None:
    with path.open("w") as fh:
        fh.write("\t".join(header) + "\n")
        for line in lines:
            fh.write("\t".join(str(x) for x in line) + "\n")


def _group_row(e):
    v = e[0]
    return [int(v[c]) for c in _GROUP_COLS] + [e[1], e[2], e[3], _f(e[4]), _f(e[5])]


def _src_maxseg(v) -> float:
    return np.nan if float(v) == -1.0 else float(v)


def _src_row(kind, e):
    v = e[0]
    return [kind, int(v["level"]), int(v["src_ix"]), int(v["src_iy"]), int(v["src_rec"]),
            int(v["src_tall"]), int(v["src_nv"]), _src_maxseg(v["src_maxseg"]),
            int(v["code"]), e[1]]


# ------------------------------------------------------------------ summary

def cmd_summary(args) -> int:
    dump = Path(args.dump)
    out = Path(args.out)
    manifest, fields, kinds, dtype = _load_manifest(dump)
    names = {f["name"] for f in fields}
    missing = [n for n in _SUMMARY_COLUMNS if n not in names]
    if missing:
        print(f"k1_triage: manifest lacks summary columns: {missing}", file=sys.stderr)
        return 2
    out.mkdir(parents=True, exist_ok=True)

    totals, by_lt = [], {}
    src_rows, src_groups = {}, {}

    for kind in sorted(kinds):
        info = kinds[kind]
        nrows = int(info["rows"])
        path = dump / info["file"]
        read = dump_io.file_rows(path, dtype.itemsize)
        totals.append((kind, nrows, read, 1 if nrows == read else 0))
        gacc = {}
        ksrc = src_rows.setdefault(kind, {})
        kgrp = src_groups.setdefault(kind, {})
        window = int(getattr(args, "window_rows", CHUNK) or CHUNK)
        with dump_io.WindowedReader(path, dtype, window, rows=read) as reader:
            for _lo, _n, block in reader.windows():
                ukey, counts, vmin, vmax, dmin, dmax = _reduce(
                    _group_key(block), np.asarray(block["vert"]), np.asarray(block["d_src"]))
                _merge_group(gacc, ukey, counts, vmin, vmax, dmin, dmax)

                ltk = _level_type_key(block)
                ltu, linv, ltc = np.unique(ltk, return_inverse=True, return_counts=True)
                conds = (
                    np.asarray(block["onb"]) != 0,
                    np.asarray(block["in_eo_same"]) == 1,
                    np.asarray(block["in_wn_same"]) == 1,
                    np.asarray(block["in_eo_any"]) == 1,
                    ~np.isnan(np.asarray(block["d_any"])),
                    np.asarray(block["src_ix"]) == INT32_MIN,
                )
                sums = [np.bincount(linv, weights=c.astype(np.int64), minlength=len(ltu))
                        for c in conds]
                for i in range(len(ltu)):
                    key = (kind, int(ltu[i]["level"]), int(ltu[i]["code"]))
                    e = by_lt.get(key)
                    if e is None:
                        e = by_lt[key] = [0] * 7
                    e[0] += int(ltc[i])
                    for j in range(6):
                        e[j + 1] += int(sums[j][i])

                sk = _src_key(block)
                su, sc = np.unique(sk, return_counts=True)
                _merge_rows(ksrc, su, sc)

                ck, gk = _composite_key(block), _group_key(block)
                cu, first = np.unique(ck, return_index=True)
                gsz, ssz = gk.dtype.itemsize, sk.dtype.itemsize
                graw, sraw = gk[first].tobytes(), sk[first].tobytes()
                for i in range(len(cu)):
                    skb = sraw[i * ssz:(i + 1) * ssz]
                    s = kgrp.get(skb)
                    if s is None:
                        kgrp[skb] = s = set()
                    s.add(graw[i * gsz:(i + 1) * gsz])
                del block, ukey, sk, ck, gk
        _write(out / f"groups_{kind}.tsv", _GROUPS_HEADER,
               [r for r in sorted((_group_row(e) for e in gacc.values()),
                                  key=_group_sort_key)])
        del gacc

    _write(out / "totals.tsv", ("kind", "rows_manifest", "rows_read", "equal"),
           sorted(totals))
    _write(out / "by_level_type.tsv", _BY_LT_HEADER,
           [list(k) + v for k, v in sorted(by_lt.items())])

    src_entries = []
    for kind in sorted(kinds):
        for e in src_rows[kind].values():
            srckey = e[0].tobytes()
            groups = len(src_groups[kind].get(srckey, ()))
            src_entries.append(_src_row(kind, e) + [groups])
    src_entries.sort(key=_src_sort_key)
    cut = max(0, len(src_entries) - _BY_SRC_CAP)
    lines = [r[:7] + [_f(r[7])] + r[8:] for r in src_entries[:_BY_SRC_CAP]]
    lines.append([f"# cut {cut} rows"])
    _write(out / "by_src.tsv", _BY_SRC_HEADER, lines)
    return 0


def _group_sort_key(r):
    return (-r[12],) + tuple(r[:12])


def _src_sort_key(r):
    maxseg = -1.0 if r[7] != r[7] else r[7]
    return (-r[9], r[0], r[1], r[2], r[3], r[4], r[5], r[6], maxseg, r[8])


# ------------------------------------------------------------------ classify

def _load_rules(path, names):
    doc = json.loads(Path(path).read_text())
    if not isinstance(doc, dict) or doc.get("version") != 1:
        raise BadRules("rules file: version must be 1")
    rules = []
    for r in doc.get("rules", []):
        rid, cause, kind = r.get("id"), r.get("cause"), r.get("kind")
        if not isinstance(rid, str) or not rid:
            raise BadRules("a rule has no id")
        if cause not in CAUSES:
            raise BadRules(f"rule {rid}: unknown cause {cause!r}")
        where = []
        for t in r.get("where", []) or []:
            if not isinstance(t, (list, tuple)) or len(t) < 2:
                raise BadRules(f"rule {rid}: bad where term {t!r}")
            col, op = t[0], t[1]
            if col not in names:
                raise BadRules(f"rule {rid}: unknown column {col!r}")
            if op not in _OPERATORS:
                raise BadRules(f"rule {rid}: unknown operator {op!r}")
            if op in ("isnan", "notnan"):
                where.append((col, op))
            elif op == "in":
                if len(t) != 3 or not isinstance(t[2], (list, tuple)):
                    raise BadRules(f"rule {rid}: operator 'in' needs a list")
                where.append((col, op, tuple(t[2])))
            else:
                if len(t) != 3:
                    raise BadRules(f"rule {rid}: operator {op!r} needs a value")
                where.append((col, op, t[2]))
        rules.append({"id": rid, "cause": cause, "kind": kind, "where": where})
    return rules


def _eval_where(where, block) -> np.ndarray:
    out = np.ones(len(block), bool)
    for term in where:
        col, op = term[0], term[1]
        x = np.asarray(block[col])
        if op == "isnan":
            c = np.isnan(x)
        elif op == "notnan":
            c = ~np.isnan(x)
        elif op == "in":
            c = np.isin(x, np.asarray(term[2]))
        else:
            v = term[2]
            c = {"==": x == v, "!=": x != v, "<": x < v, "<=": x <= v,
                 ">": x > v, ">=": x >= v}[op]
        out &= c
    return out


def cmd_classify(args) -> int:
    dump = Path(args.dump)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    # Any rejected invocation must not leave a prior successful partition
    # looking current, including failures while loading the manifest or rules.
    (out / "partition.txt").unlink(missing_ok=True)
    try:
        manifest, fields, kinds, dtype = _load_manifest(dump)
    except Exception as exc:  # noqa: BLE001 - report the manifest problem, exit 2
        print(f"k1_triage: {exc}", file=sys.stderr)
        return 2
    names = {f["name"] for f in fields}
    try:
        rules = _load_rules(args.rules, names)
        for r in rules:
            if r["kind"] not in kinds:
                raise BadRules(f"rule {r['id']}: unknown kind {r['kind']!r}")
    except (BadRules, json.JSONDecodeError) as exc:
        print(f"k1_triage: {exc}", file=sys.stderr)
        return 2

    (out / "rules.json").write_bytes(Path(args.rules).read_bytes())

    cause_rows, cause_groups = {}, {}
    unclassified = {}
    partition = []
    for kind in sorted(kinds):
        info = kinds[kind]
        nrows = int(info["rows"])
        path = dump / info["file"]
        try:
            read_rows = dump_io.file_rows(path, dtype.itemsize, allow_empty=True)
            if read_rows != nrows:
                raise ValueError(
                    f"{path}: manifest rows {nrows} != file rows {read_rows}")
            if read_rows == 0:
                # file_rows stats the path; also open and read it so a claimed empty
                # kind is accepted only after inspecting the named, readable file.
                fd = os.open(path, os.O_RDONLY)
                try:
                    if os.fstat(fd).st_size != 0 or os.read(fd, 1):
                        raise ValueError(f"{path}: changed while validating empty dump")
                finally:
                    os.close(fd)
        except Exception as exc:  # noqa: BLE001 - malformed input is a classify error
            print(f"k1_triage: {exc}", file=sys.stderr)
            return 2
        rk = [(i, r) for i, r in enumerate(rules) if r["kind"] == kind]
        kind_rules = {i for i, _ in rk}
        unclass = {}
        window = int(getattr(args, "window_rows", CHUNK) or CHUNK)
        if nrows == 0:
            # Do not construct a WindowedReader/AssignWriter: their default
            # contract continues to reject zero-row kinds for other consumers.
            assign_path = out / f"assign_{kind}.u16"
            fd = os.open(assign_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW,
                         0o666)
            os.close(fd)
            partition.append((kind, 0, 0, 0, 0))
            unclassified[kind] = unclass
            continue
        with dump_io.WindowedReader(path, dtype, window, rows=nrows) as reader,                 dump_io.AssignWriter(out / f"assign_{kind}.u16", nrows, window) as assign:
            for lo, n, block in reader.windows():
                a = np.full(n, NO_RULE, np.uint16)
                for idx, rule in rk:
                    sel = _eval_where(rule["where"], block) & (a == NO_RULE)
                    a[sel] = idx
                assign.write_window(lo, n, a)
                ukey, counts, vmin, vmax, dmin, dmax = _reduce(
                    _group_key(block, rule=a), np.asarray(block["vert"]),
                    np.asarray(block["d_src"]))
                sz = ukey.dtype.itemsize
                raw = ukey.tobytes()
                for i in range(len(counts)):
                    kb = raw[i * sz:(i + 1) * sz]
                    ri = int(ukey[i]["rule"])
                    if ri == NO_RULE:
                        _merge_one(unclass, kb, ukey[i], counts[i], vmin[i], vmax[i],
                                   dmin[i], dmax[i])
                    else:
                        key = (ri, int(ukey[i]["level"]))
                        cause_rows[key] = cause_rows.get(key, 0) + int(counts[i])
                        cause_groups.setdefault(key, set()).add(kb)
                del block, a, ukey
        assigned = sum(v for (ri, _), v in cause_rows.items() if ri in kind_rules)
        un_rows = sum(e[1] for e in unclass.values())
        partition.append((kind, nrows, assigned, un_rows, assigned))
        unclassified[kind] = unclass

    ok = all(man == asgn and un == 0
             for _k, man, asgn, un, _c in partition)
    _write_partition(out / "partition.txt", partition, ok)

    cc = []
    for (ri, lvl), n in cause_rows.items():
        r = rules[ri]
        cc.append((r["id"], r["cause"], r["kind"], lvl, n,
                   len(cause_groups[(ri, lvl)]), r["kind"], ri))
    cc.sort(key=lambda x: (x[6], x[7], x[3]))
    _write(out / "cause_counts.tsv",
           ("rule_id", "cause", "kind", "level", "rows", "groups"),
           [x[:6] for x in cc])

    un_lines = []
    for kind in sorted(unclassified):
        for e in sorted((_group_row(e) for e in unclassified[kind].values()),
                        key=_group_sort_key):
            un_lines.append(e)
    _write(out / "unclassified_groups.tsv", _GROUPS_HEADER, un_lines)
    return 0 if ok else 1


def _merge_one(acc, kb, void, count, vmin, vmax, dmin, dmax):
    e = acc.get(kb)
    if e is None:
        acc[kb] = [_own_key(void), int(count), int(vmin), int(vmax), float(dmin), float(dmax)]
    else:
        e[1] += int(count)
        if int(vmin) < e[2]:
            e[2] = int(vmin)
        if int(vmax) > e[3]:
            e[3] = int(vmax)
        e[4] = _min2(e[4], float(dmin))
        e[5] = _max2(e[5], float(dmax))


def _write_partition(path: Path, partition, ok: bool) -> None:
    lines = [("kind", "rows_manifest", "rows_assigned", "rows_unclassified",
              "cause_counts_sum")]
    lines += [tuple(x) for x in partition]
    with path.open("w") as fh:
        for line in lines:
            fh.write("\t".join(str(x) for x in line) + "\n")
        fh.write("PARTITION OK\n" if ok else "PARTITION FAIL\n")


# ------------------------------------------------------------------ enumerate

def cmd_enumerate(args) -> int:
    dump = Path(args.dump)
    adir = Path(args.assign)
    try:
        rules_doc = json.loads((adir / "rules.json").read_text())
    except Exception as exc:  # noqa: BLE001
        print(f"k1_triage: {adir}/rules.json: {exc}", file=sys.stderr)
        return 2
    idx = kind = None
    for i, r in enumerate(rules_doc.get("rules", [])):
        if r.get("id") == args.rule:
            idx, kind = i, r.get("kind")
            break
    if idx is None:
        print(f"k1_triage: no rule with id {args.rule!r}", file=sys.stderr)
        return 2
    _manifest, _fields, kinds, dtype = _load_manifest(dump)
    if kind not in kinds:
        print(f"k1_triage: rule kind {kind!r} not in the dump", file=sys.stderr)
        return 2
    nrows = int(kinds[kind]["rows"])
    path = dump / kinds[kind]["file"]
    dump_io.file_rows(path, dtype.itemsize)
    acc = {}
    window = int(getattr(args, "window_rows", CHUNK) or CHUNK)
    with dump_io.WindowedReader(path, dtype, window, rows=nrows) as reader,             dump_io.AssignReader(adir / f"assign_{kind}.u16", nrows, window) as assign:
        for lo, n, block in reader.windows():
            a = assign.read_window(lo, n)
            sel = a == idx
            if not sel.any():
                continue
            u, c = np.unique(_group_key(block[sel]), return_counts=True)
            _merge_rows(acc, u, c)
            del block, a, u, c
    rows = []
    for e in acc.values():
        rows.append([kind] + [int(e[0][n]) for n in _GROUP_COLS] + [e[1]])
    rows.sort(key=lambda r: tuple(r))
    _write(Path(args.out),
           ("kind", "level", "ix", "iy", "type", "p0", "p1", "p2", "p3", "p4", "p5",
            "p6", "shape", "rows"), rows)
    return 0


# ------------------------------------------------------------------ CLI

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="k1_triage",
                                 description="group, summarise and classify a K1 dump")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("summary")
    s.add_argument("--dump", required=True)
    s.add_argument("--out", required=True)
    s.add_argument("--window-rows", type=int, default=CHUNK)
    c = sub.add_parser("classify")
    c.add_argument("--dump", required=True)
    c.add_argument("--rules", required=True)
    c.add_argument("--out", required=True)
    c.add_argument("--window-rows", type=int, default=CHUNK)
    e = sub.add_parser("enumerate")
    e.add_argument("--dump", required=True)
    e.add_argument("--assign", required=True)
    e.add_argument("--rule", required=True)
    e.add_argument("--out", required=True)
    e.add_argument("--window-rows", type=int, default=CHUNK)
    args = ap.parse_args(argv)
    return {"summary": cmd_summary, "classify": cmd_classify,
            "enumerate": cmd_enumerate}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
