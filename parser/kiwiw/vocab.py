"""OSM tag -> KIWI vocabulary code tables, loaded from checked-in
`parser/refdata/vocab/*.json`.

docs/design/target-disc.md, "Vocabulary is data, not code" (settled): "The
mapping tables from OSM tags to KIWI road types, display classes,
background types and name string types are checked-in data with a
coverage test against `R`'s censused vocabulary, not literals in a
converter." This module is the loader for that data; the tables
themselves (and the rationale for each non-obvious value) live in
`parser/refdata/vocab/README.md`.

Table format (one JSON file per vocabulary, e.g. `road_type.json`)::

    {
      "levels": [[0, 0], [2, 8], [10, 12]],
      "rules": [
        {"levels": 0, "match": {"highway": ["motorway", "trunk"]}, "value": 3},
        ...
      ],
      "default": <value or null>
    }

- ``levels``: the disjoint, even-level ranges this table covers, as
  ``[lo, hi]`` inclusive pairs. The union must equal the even levels
  0..12 (0, 2, 4, 6, 8, 10, 12); ranges must not overlap.
- ``rules``: ordered list of ``{"levels": <range-lo>, "match": {...},
  "value": <int>}``. ``levels`` here is the *lower bound* of one of the
  ranges declared above (identifying which range this rule applies to,
  since one range's lower bound is enough to key it uniquely). ``match``
  is a dict of ``tag_key -> [allowed values, ...]``; a rule matches a tag
  dict when every key in ``match`` is present in the tag dict with a value
  in the given list (AND across keys). The first matching rule (in file
  order) wins.
- ``default``: the fallback value when no rule matches for the range
  containing the queried level, or ``null`` meaning "omit the feature at
  this level" (brief 08's contract: "this is the *type* mapping only;
  unit 14 decides selection, so keep the default non-null wherever `R`
  has a plausible code").

This module imports only stdlib.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

_PACKAGE_DIR = Path(__file__).resolve().parent
_VOCAB_DIR = _PACKAGE_DIR.parent / "refdata" / "vocab"

EVEN_LEVELS = (0, 2, 4, 6, 8, 10, 12)


class VocabError(ValueError):
    """Raised when a vocab table fails validation on load."""


@dataclass(frozen=True)
class _Rule:
    range_lo: int
    match: dict
    value: int


@dataclass(frozen=True)
class _Range:
    lo: int
    hi: int

    def contains(self, level: int) -> bool:
        return self.lo <= level <= self.hi


class Vocab:
    """One loaded vocabulary table (road_type, display_class or bg_type)."""

    def __init__(self, name: str, ranges: list[_Range], rules: list[_Rule],
                 default: Optional[int]):
        self.name = name
        self._ranges = ranges
        self._rules = rules
        self._default = default

    # -- lookup -------------------------------------------------------

    def _range_for_level(self, level: int) -> Optional[_Range]:
        for r in self._ranges:
            if r.contains(level):
                return r
        return None

    def lookup(self, level: int, tags: dict) -> Optional[int]:
        """Return the vocabulary value for `tags` at `level`, or None if
        the level is outside every declared range, no rule matches and the
        default is null."""
        rng = self._range_for_level(level)
        if rng is None:
            return None
        for rule in self._rules:
            if rule.range_lo != rng.lo:
                continue
            if _tags_match(rule.match, tags):
                return rule.value
        return self._default

    def emitted_values(self, level: int) -> set:
        """The set of values this table can ever emit for `level`: every
        rule value for the range containing `level`, plus the default if
        non-null. Empty set if `level` is outside every declared range."""
        rng = self._range_for_level(level)
        if rng is None:
            return set()
        values = {rule.value for rule in self._rules if rule.range_lo == rng.lo}
        if self._default is not None:
            values.add(self._default)
        return values


def _tags_match(match: dict, tags: dict) -> bool:
    for key, allowed in match.items():
        if tags.get(key) not in allowed:
            return False
    return True


def _validate_and_build(name: str, data: dict) -> Vocab:
    if "levels" not in data or "rules" not in data or "default" not in data:
        raise VocabError(
            f"vocab table {name!r}: must have 'levels', 'rules' and 'default' keys")

    raw_ranges = data["levels"]
    if not isinstance(raw_ranges, list) or not raw_ranges:
        raise VocabError(f"vocab table {name!r}: 'levels' must be a non-empty list")

    ranges: list[_Range] = []
    covered: set = set()
    for raw in raw_ranges:
        if (not isinstance(raw, list) or len(raw) != 2
                or not all(isinstance(v, int) for v in raw)):
            raise VocabError(
                f"vocab table {name!r}: each 'levels' entry must be a "
                f"[lo, hi] pair of ints, got {raw!r}")
        lo, hi = raw
        if lo > hi:
            raise VocabError(
                f"vocab table {name!r}: range [{lo}, {hi}] has lo > hi")
        range_levels = {lv for lv in EVEN_LEVELS if lo <= lv <= hi}
        if not range_levels:
            raise VocabError(
                f"vocab table {name!r}: range [{lo}, {hi}] covers no "
                f"even level 0..12")
        overlap = covered & range_levels
        if overlap:
            raise VocabError(
                f"vocab table {name!r}: range [{lo}, {hi}] overlaps an "
                f"earlier range at level(s) {sorted(overlap)}")
        covered |= range_levels
        ranges.append(_Range(lo=lo, hi=hi))

    missing = set(EVEN_LEVELS) - covered
    if missing:
        raise VocabError(
            f"vocab table {name!r}: 'levels' ranges do not cover even "
            f"level(s) {sorted(missing)} (0..12 even must all be covered)")

    range_los = {r.lo for r in ranges}
    rules: list[_Rule] = []
    for i, raw_rule in enumerate(data["rules"]):
        if not isinstance(raw_rule, dict):
            raise VocabError(f"vocab table {name!r}: rule {i} must be an object")
        for key in ("levels", "match", "value"):
            if key not in raw_rule:
                raise VocabError(
                    f"vocab table {name!r}: rule {i} missing {key!r}")
        range_lo = raw_rule["levels"]
        if range_lo not in range_los:
            raise VocabError(
                f"vocab table {name!r}: rule {i} 'levels'={range_lo!r} does "
                f"not match any declared range's lower bound "
                f"({sorted(range_los)})")
        match = raw_rule["match"]
        if not isinstance(match, dict):
            raise VocabError(f"vocab table {name!r}: rule {i} 'match' must be an object")
        value = raw_rule["value"]
        if not isinstance(value, int) or isinstance(value, bool):
            raise VocabError(
                f"vocab table {name!r}: rule {i} 'value' must be an int, "
                f"got {value!r}")
        rules.append(_Rule(range_lo=range_lo, match=match, value=value))

    default = data["default"]
    if default is not None and (not isinstance(default, int) or isinstance(default, bool)):
        raise VocabError(
            f"vocab table {name!r}: 'default' must be an int or null, "
            f"got {default!r}")

    return Vocab(name=name, ranges=ranges, rules=rules, default=default)


def load(name: str, vocab_dir: Optional[str] = None) -> Vocab:
    """Load `<vocab_dir>/<name>.json` (default: `parser/refdata/vocab/`,
    resolved relative to this package -- never the current working
    directory)."""
    d = Path(vocab_dir) if vocab_dir is not None else _VOCAB_DIR
    path = d / f"{name}.json"
    with open(path, "r") as f:
        data = json.load(f)
    return _validate_and_build(name, data)
