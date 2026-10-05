# Phase 1 name_anchor byte witness

Verdict: **A**.

R lacks the byte-equal G string at G's position within ±0.5 raw per axis. G≠R for this item; the pinned O03 stale-spool clamp is the root cause.

G historical disc pin `4ed9cd801bdd70992a9b7bd090803ffae349515f87546f044b21157e68e99d72`; frame leaf `[928]`, offset 197597600, length 320, sha256 `3c927c6b4868664907ab14c8a8c49fbf34d5debb8e5ef4d4a22d28e323251b48`.

G name `France, Terres australes et antarctiques françaises, Îles Saint-Paul et Nouvelle-Amsterdam - Île Saint-Paul (eaux territoriales)`; string hex `4672616e63652c20546572726573206175737472616c657320657420616e74617263746971756573206672616ee761697365732c20ce6c6573205361696e742d5061756c206574204e6f7576656c6c652d416d7374657264616d202d20ce6c65205361696e742d5061756c202865617578207465727269746f7269616c657329` (latin-1), stored hex `4672616e63652c20546572726573206175737472616c657320657420616e74617263746971756573206672616ee761697365732c20ce6c6573205361696e742d5061756c206574204e6f7576656c6c652d416d7374657264616d202d20ce6c65205361696e742d5061756c202865617578207465727269746f7269616c657329`; string_type 6, class 288, raw [0, 370], lat/lon -38.727284749348954/90.0. Record offset 197597764, length 144, sha256 `a681fcc453e60a6ea0bde560254ab0d5f66ee58644e22de7632480f944d6b92a`.

Spool L0 [0, 541] record 0: lat/lon -38.727285888405795/77.51903576666666, UTF-8 string hex `4672616e63652c20546572726573206175737472616c657320657420616e74617263746971756573206672616ec3a761697365732c20c38e6c6573205361696e742d5061756c206574204e6f7576656c6c652d416d7374657264616d202d20c38e6c65205361696e742d5061756c202865617578207465727269746f7269616c657329`. Record-column bytes sha256 `e2a39a45284bd347400a40e313a7eaa5c2245994fef706710a0aac98fc618f9c`; exact offsets/hex are in spool.json. Its columnar layout has no single contiguous name-record extent. Cell offset 248992624, length 2616, sha256 `5b7c1a75a573ca9efbd55c6961b02b1fce06b0dd041b3f6f517f38a79f25d44c`.

Source-anchor distance 1635904.9439914674 raw. Region nearest distance 1635904.9439914674; K1 bucket result inf (saved K1 error_raw null), tolerance 0.5 raw; halo eligible False. The saved live report has name_anchor totals {'checked': 2317056, 'failing': 1, 'worst_error_raw': 0.499999} and failure samples [{'cell': [0, 541], 'error_raw': None, 'kind': 'name_anchor', 'leaf_path': [928], 'reason': 'no spool record within half a raw unit', 'vertex': {'lat': -38.727284749, 'lon': 90.0, 'raw': [0, 370]}}].

R historical disc pin `8c2d20275227b9d2abb0f1802d4e0cbb6697f46545794d19e1a2024b6f169275`. Index offsets/hex/SHA-256, decoded DSA/size and outside-coverage geometry are retained in the R JSON and replayed by this verdict. Full disc pins are cited from prior evidence, not re-hashed by this bounded witness. All nine requested cells follow; ix=-1 is outside coverage.

| Cell | Status / reason | Covering frames (offset / length / sha256) |
| --- | --- | --- |
| [-1, 540] | outside_coverage / cell_outside_L0_grid | none |
| [0, 540] | empty_slot / absent_BMT_sentinel | none |
| [1, 540] | empty_slot / absent_BMT_sentinel | none |
| [-1, 541] | outside_coverage / cell_outside_L0_grid | none |
| [0, 541] | empty_slot / absent_BMT_sentinel | none |
| [1, 541] | empty_slot / absent_BMT_sentinel | none |
| [-1, 542] | outside_coverage / cell_outside_L0_grid | none |
| [0, 542] | empty_slot / absent_BMT_sentinel | none |
| [1, 542] | empty_slot / absent_BMT_sentinel | none |

R byte-equal names: none (0 covering-slot observations, including aliases). Full name-record byte equality at the matching position: False.

Tip extractor assignment → None; mesh twin → None. Existing controls: parser/tests/test_name_anchor_o03_extractor.py, test_parcel_geometry.py:119, test_descriptor.py:47.

Spool extractor provenance `34a04cc` is recorded in plan 14's recovery and docs/provenance.md, not stored intrinsically in the spool. `git merge-base --is-ancestor 34a04cc 16e2931` exit 0.

Whole-spool anchored names checked 2006629; plan-18-rejectable 1; without anchors 0. Per-level counts: `{"0": {"checked": 1971463, "rejected": 1, "without_anchor": 0}, "10": {"checked": 8, "rejected": 0, "without_anchor": 0}, "12": {"checked": 8, "rejected": 0, "without_anchor": 0}, "2": {"checked": 30286, "rejected": 0, "without_anchor": 0}, "4": {"checked": 3354, "rejected": 0, "without_anchor": 0}, "6": {"checked": 1223, "rejected": 0, "without_anchor": 0}, "8": {"checked": 287, "rejected": 0, "without_anchor": 0}}`. Every reject, including any extras, is listed in `/home/codyh/workspace/open-pajero-maps-14-completeness/docs/plans/29-k1-name-anchor-failure/witnesses/scan_rejects.tsv`.

Heavy runs use parser/tools/run_heavy_python.py and its output/.heavy.lock. No disc/spool/encoder/checker/rule change or K1 re-run is part of Phase 1.

Drift: none

Concerns: none
