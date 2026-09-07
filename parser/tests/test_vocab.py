"""Checks for `parser/refdata/vocab/*.json` and the `kiwiw.vocab` loader.

The core correctness property (brief 08, docs/design/target-disc.md
"Vocabulary is data, not code") is coverage: every value a table can ever
emit at a level must be a value the reference disc `R`'s own census
(`parser/refdata/profile/map.json`) actually observed at that level. These
tests read the profile directly rather than importing
`parser.harness.checks.vocab` (that check compares a *built disc's*
histogram against the profile; this only checks the table's declared
range against the profile -- a narrower, table-only property that must
hold before a build can ever pass the harness check).
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kiwiw import vocab  # noqa: E402

PROFILE_PATH = (
    Path(__file__).resolve().parent.parent / "refdata" / "profile" / "map.json"
)

EVEN_LEVELS = (0, 2, 4, 6, 8, 10, 12)

# (table name, profile histogram path under levels[<level>][...])
TABLES = [
    ("road_type", ("road", "road_type_hist")),
    ("display_class", ("road", "display_class_hist")),
    ("bg_type", ("background", "type_code_hist")),
]


def _load_profile():
    with open(PROFILE_PATH) as f:
        return json.load(f)


def _profile_values(profile, level: int, path) -> set:
    node = profile["levels"][str(level)]
    for key in path:
        node = node[key]
    return {int(k) for k in node.keys()}


def test_all_tables_load_without_error():
    for name, _ in TABLES:
        vocab.load(name)


def test_coverage_against_reference_census():
    """emitted_values(level) subset of R's censused vocabulary, for every
    table and every even level 0..12 -- the property this whole unit
    exists to guarantee."""
    profile = _load_profile()
    failures = []
    for name, path in TABLES:
        v = vocab.load(name)
        for level in EVEN_LEVELS:
            emitted = v.emitted_values(level)
            allowed = _profile_values(profile, level, path)
            extra = emitted - allowed
            if extra:
                failures.append(
                    f"{name} level={level}: emits {sorted(extra)} not in "
                    f"R's census {sorted(allowed)}"
                )
    assert not failures, "\n".join(failures)


def test_road_type_level_0_lookup():
    v = vocab.load("road_type")
    assert v.lookup(0, {"highway": "motorway"}) == 0
    assert v.lookup(0, {"highway": "trunk_link"}) == 10
    assert v.lookup(0, {"highway": "residential"}) == 6
    assert v.lookup(0, {"highway": "not_a_real_tag"}) is None


def test_road_type_level_2_to_8_collapse_to_shared_rule():
    v = vocab.load("road_type")
    for level in (2, 4, 6, 8):
        assert v.lookup(level, {"highway": "motorway"}) == 0
        assert v.lookup(level, {"highway": "trunk"}) == 10
        assert v.lookup(level, {"highway": "primary"}) == 7
        # secondary..track all collapse to the one remaining shared code
        for hw in ("secondary", "tertiary", "unclassified", "residential",
                    "service", "track"):
            assert v.lookup(level, {"highway": hw}) == 2


def test_road_type_level_10_12_always_none():
    """R has zero road links at levels 10/12; the table must never emit a
    value there regardless of tags."""
    v = vocab.load("road_type")
    for level in (10, 12):
        assert v.lookup(level, {"highway": "motorway"}) is None
        assert v.lookup(level, {"highway": "residential"}) is None


def test_display_class_level_0_lookup():
    v = vocab.load("display_class")
    assert v.lookup(0, {"highway": "motorway"}) == 12
    assert v.lookup(0, {"highway": "trunk"}) == 0
    assert v.lookup(0, {"highway": "service"}) == 2


def test_bg_type_level_0_lookup():
    v = vocab.load("bg_type")
    assert v.lookup(0, {"natural": "water"}) == 290
    assert v.lookup(0, {"natural": "coastline"}) == 289
    assert v.lookup(0, {"landuse": "industrial"}) == 322
    assert v.lookup(0, {"aeroway": "aerodrome"}) == 640
    # catch-all: anything unmatched still gets a value at level 0
    assert v.lookup(0, {"building": "yes"}) == 288


def test_bg_type_level_10_12_narrow_vocabulary():
    v = vocab.load("bg_type")
    for level in (10, 12):
        assert v.lookup(level, {"natural": "water"}) == 289
        assert v.lookup(level, {"boundary": "administrative", "admin_level": "4"}) == 306
        # no catch-all at this level -- most tags map to nothing
        assert v.lookup(level, {"building": "yes"}) is None


def test_loader_rejects_overlapping_level_range():
    bad = {
        "levels": [[0, 4], [2, 12]],
        "rules": [],
        "default": None,
    }
    import io
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "bad.json"
        p.write_text(json.dumps(bad))
        try:
            vocab.load("bad", vocab_dir=d)
            assert False, "expected VocabError for overlapping ranges"
        except vocab.VocabError:
            pass


def test_loader_rejects_incomplete_level_coverage():
    bad = {
        "levels": [[0, 8]],  # missing 10, 12
        "rules": [],
        "default": None,
    }
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "bad.json"
        p.write_text(json.dumps(bad))
        try:
            vocab.load("bad", vocab_dir=d)
            assert False, "expected VocabError for incomplete level coverage"
        except vocab.VocabError:
            pass
