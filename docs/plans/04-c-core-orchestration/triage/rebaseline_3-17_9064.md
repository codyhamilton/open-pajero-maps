# Unit 3-17 — Re-baseline the historic unattributed ledger

**Status: done with concerns.** Local Codex, 2026-10-04 Australia/Brisbane,
branch `feat/3-17-9064-rebaseline`, base
`ced98f8272fc1e4a34ba0d34b0dbbb1535c5f205`.
[Brief](../briefs/3-17-9064-rebaseline.md). Docs only; Execute owns landing.

The historic background and boundary buckets are absent from the current failing
set. Every historic completeness row is still failing and still unattributed
under the live rules. The complete classify aborts on an empty kind; the
completeness-only classify gives `PARTITION FAIL`. No assigned build-caused row
appeared. Phase 3 remains open.

## Preconditions and cited facts

- **C1 PASS:** HEAD is exactly the requested base; `e97c968` is an ancestor;
  `docs/plans/07-g-new-nonpayload/PHASE.md` is present on that base; the base
  contains no `briefs/3-17*.md`. The supplied untracked brief is included in
  this documentation commit. Design 170 already records Map Frame allocation
  padding; its folder is unchanged.
- **C2 PASS:** the existing read-only AU disc is
  `/home/codyh/workspace/open-pajero-maps-3-14/output/scratch-3-14/G_new/ALLDATA.KWI`.
  Fresh `sha256sum`, saved as `output/scratch-3-17/disc.sha256`, equals
  `4ed9cd801bdd70992a9b7bd090803ffae349515f87546f044b21157e68e99d72`.
  The retained `new_sha256.txt`, `dump_new.py`, `k1_full.log` and extended dump
  manifest tie the reused dump to that disc. No replacement disc or fresh K1
  run was needed.
- **C3 PASS, quoted once without recomputation:** historic **9,064 = 137 +
  8,739 + 188** ([3-13 review](review_3-13.md)); 3-14 kind failing:
  **background 0, background_boundary 0, interior_cover 0, completeness 776,
  name_anchor 1** ([implementation](../IMPLEMENTATION.md), 3-14);
  **776 = 363 + 132 + 7 + 274** ([3-15 packet](completeness_3-15_cell_local.md));
  3-16 **0 pass / 89 fail / 0 untested**
  ([3-16 packet](completeness_3-16_window_cf.md)). The historic composition,
  representability science, corrected mechanism recount and 89 tally were not
  re-derived.
- **C4 PASS:** pre-append R01 is `cause: checker` with
  `where: [["in_eo_same", "==", 1]]`; `rules_other.json` has no R01.
  Its note was read and saved in `output/scratch-3-17/rules_bg.before.json`.
  Both original rule files and their concatenation were captured before the
  note append. All classify runs use those pre-append rules.

## Historic bucket outcomes

| Historic kind | Historic rows | Current kind failing | Outcome for historic rows |
| --- | ---: | ---: | --- |
| background | 137 | 0 | All 137 **not in the failing set**. Empty-kind classify aborts; no partition result. |
| background_boundary | 8,739 | 0 | All 8,739 **not in the failing set**. Empty-kind classify aborts; no partition result. |
| completeness | 188 | 776 | All 188 **still failing and still unattributed**, matched at full item identity. |

Kind failing counts above come from the retained 3-14 `k1_full.json`; its empty
background and boundary dumps each contain zero bytes. The old keys are
recoverable in the retained 3-12 `dump_ext` and corresponding `classify/assign_*.u16`.
`identity_audit.py` selects the historic `NO_RULE` rows from those existing
assignments, checks the supplied bucket sizes, and records each native old row
and full key in `output/scratch-3-17/historic_<kind>_rows.tsv`. No missing identity
was reconstructed. The completeness keys also match the already-recorded
3-15 `historic188_status.tsv` exactly.

The identity tuple is `(level, ix, iy, code, p0, p1, p2, p3, p4, p5, p6, shape,
vert)`. All historic completeness keys occur in the current dump, and each has
current assignment `65535` (`NO_RULE`). The full old→new native-row correspondence
is preserved below and in the scratch TSV. **these rows stay unattributed.**
The separate 3-15 science disposition does not register a rule or change these
live assignments; no new cause is named here.

## Classify evidence and limits

The unchanged entry point was run as:

```text
/home/codyh/workspace/open-pajero-maps/.venv-rp/bin/python -B parser/tools/k1_triage.py classify --dump /home/codyh/workspace/open-pajero-maps-3-14/output/scratch-3-14/dump_ext --rules output/scratch-3-17/rules_all.before.json --out output/scratch-3-17/classify
```

Exit **1**; stdout is empty and stderr is retained at
`output/scratch-3-17/classify.stderr`. The exception ends:

```text
ValueError: /home/codyh/workspace/open-pajero-maps-3-14/output/scratch-3-14/dump_ext/background.bin: zero-row kinds are unsupported (as in the baseline)
```

At this base, the rejection is in `dump_io.file_rows`, called by
`cmd_classify`, rather than the old `_memmap` implementation named in the brief.
No full partition was emitted. This abort is **not `PARTITION OK`**.

To reach the nonempty kinds without a code change, scratch kind views retain
the exact field layout and the single original kind entry, symlink the unchanged
binary, and select only that kind's original rules (including their original
order, predicates and causes). These manifest/rule projections do not assign new
causes. Commands, stdout and stderr are saved in
`output/scratch-3-17/kind_views/<kind>/`; results are in
`output/scratch-3-17/classify_kinds/<kind>/`. Separate background,
background_boundary and interior_cover runs each exit 1 with the same zero-row
rejection and do **not** partition their kind.

The completeness-only entry completes its table generation, exits **1**, and
has empty stdout/stderr. `classify_kinds/completeness/partition.txt` says:

```text
kind	rows_manifest	rows_assigned	rows_unclassified	cause_counts_sum
completeness	776	468	308	468
PARTITION FAIL
```

Its `cause_counts.tsv` reports O01 checker **363**, O04 spool **3**, O05 checker
**102**, all L0. No O06 or other build rule has an assigned row. The name_anchor
kind view assigns its one row to the unchanged O03 spool rule and emits
`PARTITION OK` **for that kind alone**; no name-anchor investigation occurred.

The raw-dump **308** unattributed total is not the quoted 3-15 **274** corrected
mechanism recount. The retained 3-14 extension explicitly reuses `other_mechanism`
only in byte-unchanged cells and conservatively zeroes it on changed cells.
[3-15](completeness_3-15_cell_local.md) already identifies inherited/forced-zero
mechanism bytes and uses a recomputed tally. This unit runs the existing CLI on
the unchanged dump; it neither recomputes that science nor replaces those flags.
The historic 188 match and remain unattributed in either record. The raw dump's
other unmatched rows are left unattributed; no blanket live-ledger equivalence,
new cause or global partition success is claimed.

`inputs.json` preserves input hashes and sizes; `classify.command.json`,
`classify.exit.json`, `classify_kinds.exit.json` and `identity_summary.json`
retain the invocation and audit results. Input hashes were checked again before
recording the documentation. Bytecode writes were disabled, all new artifacts
are under this worktree's ignored `output/scratch-3-17/`, and no encode, disc
write, fresh dump, C build or heavy work was run.

## R01 note and phase boundary

R01's original note remains verbatim and is followed by exactly this appendix:

> R01 exclusivity vs the build defect is unproven (review_3-13 finding 3; causes_rootcause.md): in the L0/291 window, 31 type-291 in_eo_same=1 fills vanish after repair and may overlap build; not tested beyond that window. Unit 3-14 saw R01 checker background 920,786 → 0 and did not reclassify the cause. Note only.

Only that note string changes in `rules_bg.json`; R01 stays checker and its
predicate stays `in_eo_same == 1`. All other rules, predicates, causes and order
are untouched.

[DESIGN.md Phase 3](../DESIGN.md) requires:

> On the oracle disc in force at phase close, the checker reports build-caused and checker-caused failures of 0 in every kind, and the failures that remain are exactly the enumerated spool-caused list (item identity, not only counts), carried to the successor design.

This scoped re-baseline does not satisfy that phase-close outcome: the live
completeness remainder is unattributed, and empty kinds lack a CLI partition.
There is no contradiction between that outcome and an open-phase documentation
unit. No Phase 3 close, successor spool list, follow-on unit or phase trailer is
written. The brief's instruction to land on master is superseded by the user's
feature-branch-only commit instruction; Maps Execute owns landing. No push, PR
or workflow-service call/post occurred.

## Preserved live completeness identities

Every row below is still failing and still unattributed. Shared identity fields:
`level=0`, `p0=p1=p2=p3=p4=p5=p6=0`, `shape=-1`, `vert=-1`.
Row indices are zero-based in the original 3-12 and current 3-14 extended dumps;
the varying `(ix, iy, code)` plus those shared fields is the full identity.

| ix | iy | code | 3-12 native row | 3-14 native row |
| ---: | ---: | ---: | ---: | ---: |
| 1852 | 746 | 288 | 238 | 187 |
| 1454 | 766 | 288 | 251 | 200 |
| 1454 | 767 | 288 | 252 | 201 |
| 1075 | 796 | 288 | 264 | 215 |
| 1248 | 885 | 288 | 293 | 245 |
| 1903 | 995 | 291 | 307 | 260 |
| 1248 | 1061 | 288 | 337 | 292 |
| 1248 | 1063 | 288 | 338 | 293 |
| 1248 | 1065 | 288 | 339 | 294 |
| 1248 | 1067 | 288 | 340 | 295 |
| 1248 | 1070 | 288 | 341 | 296 |
| 1248 | 1074 | 288 | 343 | 298 |
| 1248 | 1076 | 288 | 345 | 300 |
| 1248 | 1078 | 288 | 346 | 301 |
| 1248 | 1083 | 288 | 347 | 302 |
| 1248 | 1085 | 288 | 348 | 303 |
| 1248 | 1087 | 288 | 349 | 304 |
| 1248 | 1089 | 288 | 351 | 306 |
| 1248 | 1091 | 288 | 352 | 307 |
| 1248 | 1093 | 288 | 353 | 308 |
| 1248 | 1095 | 288 | 354 | 309 |
| 1248 | 1098 | 288 | 355 | 310 |
| 1248 | 1100 | 288 | 356 | 311 |
| 1248 | 1102 | 288 | 357 | 312 |
| 1248 | 1104 | 288 | 358 | 313 |
| 1248 | 1106 | 288 | 360 | 315 |
| 1248 | 1108 | 288 | 361 | 316 |
| 1248 | 1111 | 288 | 363 | 318 |
| 1248 | 1113 | 288 | 364 | 319 |
| 1248 | 1121 | 288 | 368 | 323 |
| 1248 | 1124 | 288 | 369 | 325 |
| 1348 | 1125 | 288 | 370 | 326 |
| 1248 | 1128 | 288 | 371 | 329 |
| 1248 | 1130 | 288 | 372 | 330 |
| 1248 | 1132 | 288 | 373 | 331 |
| 1248 | 1134 | 288 | 374 | 333 |
| 1248 | 1136 | 288 | 375 | 334 |
| 1248 | 1141 | 288 | 377 | 338 |
| 1248 | 1143 | 288 | 386 | 347 |
| 1248 | 1149 | 288 | 388 | 351 |
| 1348 | 1152 | 288 | 391 | 355 |
| 1371 | 1152 | 288 | 392 | 357 |
| 1374 | 1152 | 288 | 393 | 358 |
| 1377 | 1152 | 288 | 394 | 359 |
| 1248 | 1156 | 288 | 395 | 362 |
| 1248 | 1158 | 288 | 396 | 363 |
| 1214 | 1159 | 291 | 397 | 364 |
| 1248 | 1160 | 288 | 398 | 365 |
| 1248 | 1162 | 288 | 399 | 366 |
| 1248 | 1165 | 288 | 400 | 367 |
| 1248 | 1167 | 288 | 401 | 368 |
| 1248 | 1169 | 288 | 402 | 369 |
| 1248 | 1171 | 288 | 404 | 371 |
| 1248 | 1173 | 288 | 406 | 373 |
| 1248 | 1175 | 288 | 407 | 374 |
| 1248 | 1177 | 288 | 409 | 376 |
| 1248 | 1180 | 288 | 410 | 377 |
| 1248 | 1182 | 288 | 411 | 378 |
| 1248 | 1184 | 288 | 413 | 380 |
| 1248 | 1186 | 288 | 414 | 381 |
| 1248 | 1188 | 288 | 415 | 382 |
| 1248 | 1195 | 288 | 416 | 383 |
| 1248 | 1197 | 288 | 417 | 384 |
| 1248 | 1199 | 288 | 419 | 386 |
| 1248 | 1203 | 288 | 420 | 387 |
| 1248 | 1206 | 288 | 421 | 388 |
| 1248 | 1208 | 288 | 422 | 389 |
| 1248 | 1210 | 288 | 424 | 391 |
| 1248 | 1214 | 288 | 425 | 392 |
| 1248 | 1216 | 288 | 426 | 393 |
| 1248 | 1219 | 288 | 427 | 394 |
| 1248 | 1223 | 288 | 428 | 395 |
| 1248 | 1225 | 288 | 514 | 482 |
| 1248 | 1227 | 288 | 515 | 483 |
| 1248 | 1229 | 288 | 516 | 484 |
| 1248 | 1231 | 288 | 517 | 485 |
| 1248 | 1234 | 288 | 518 | 486 |
| 1248 | 1236 | 288 | 519 | 487 |
| 1248 | 1238 | 288 | 520 | 489 |
| 1248 | 1242 | 288 | 521 | 491 |
| 1248 | 1244 | 288 | 522 | 492 |
| 1248 | 1247 | 288 | 523 | 493 |
| 1248 | 1249 | 288 | 524 | 494 |
| 1248 | 1251 | 288 | 525 | 495 |
| 1248 | 1255 | 288 | 527 | 497 |
| 1109 | 1257 | 288 | 528 | 498 |
| 1248 | 1257 | 288 | 529 | 499 |
| 1248 | 1260 | 288 | 531 | 501 |
| 1248 | 1262 | 288 | 532 | 502 |
| 1109 | 1263 | 288 | 533 | 503 |
| 1248 | 1264 | 288 | 535 | 505 |
| 1248 | 1266 | 288 | 536 | 506 |
| 1109 | 1268 | 288 | 537 | 507 |
| 1712 | 1274 | 288 | 542 | 512 |
| 1248 | 1277 | 288 | 544 | 514 |
| 1777 | 1279 | 291 | 546 | 517 |
| 1401 | 1281 | 288 | 547 | 519 |
| 1248 | 1290 | 288 | 548 | 522 |
| 1248 | 1292 | 288 | 550 | 524 |
| 1248 | 1303 | 288 | 552 | 529 |
| 1248 | 1305 | 288 | 553 | 530 |
| 1248 | 1307 | 288 | 554 | 531 |
| 1248 | 1309 | 288 | 555 | 532 |
| 1248 | 1311 | 288 | 556 | 533 |
| 1248 | 1361 | 288 | 589 | 572 |
| 1248 | 1363 | 288 | 591 | 574 |
| 1248 | 1365 | 288 | 592 | 575 |
| 1248 | 1368 | 288 | 593 | 576 |
| 1248 | 1370 | 288 | 594 | 577 |
| 1248 | 1372 | 288 | 595 | 578 |
| 1248 | 1374 | 288 | 596 | 579 |
| 1248 | 1376 | 288 | 598 | 581 |
| 1248 | 1378 | 288 | 600 | 583 |
| 1152 | 1392 | 288 | 607 | 590 |
| 1248 | 1398 | 288 | 608 | 593 |
| 1248 | 1400 | 288 | 609 | 594 |
| 1248 | 1402 | 288 | 611 | 596 |
| 1248 | 1463 | 288 | 618 | 612 |
| 1248 | 1478 | 288 | 630 | 630 |
| 1248 | 1480 | 288 | 631 | 631 |
| 1248 | 1484 | 288 | 633 | 633 |
| 1248 | 1486 | 288 | 634 | 634 |
| 1248 | 1489 | 288 | 636 | 636 |
| 1248 | 1491 | 288 | 638 | 638 |
| 1248 | 1495 | 288 | 640 | 641 |
| 1248 | 1497 | 288 | 642 | 643 |
| 1248 | 1499 | 288 | 644 | 645 |
| 1248 | 1502 | 288 | 645 | 646 |
| 1248 | 1508 | 288 | 650 | 653 |
| 1248 | 1510 | 288 | 651 | 654 |
| 1248 | 1512 | 288 | 652 | 655 |
| 1248 | 1514 | 288 | 655 | 658 |
| 1288 | 1527 | 288 | 660 | 671 |
| 1299 | 1527 | 288 | 661 | 678 |
| 1248 | 1534 | 288 | 665 | 685 |
| 1248 | 1536 | 288 | 667 | 687 |
| 1248 | 1538 | 288 | 669 | 689 |
| 1248 | 1545 | 288 | 670 | 692 |
| 1248 | 1547 | 288 | 671 | 693 |
| 1248 | 1549 | 288 | 672 | 694 |
| 1126 | 1568 | 288 | 674 | 703 |
| 1126 | 1569 | 288 | 675 | 704 |
| 1248 | 1569 | 288 | 676 | 705 |
| 1248 | 1575 | 288 | 677 | 709 |
| 1248 | 1577 | 288 | 678 | 710 |
| 1248 | 1586 | 288 | 680 | 712 |
| 1248 | 1588 | 288 | 682 | 714 |
| 1248 | 1590 | 288 | 683 | 715 |
| 1248 | 1592 | 288 | 684 | 716 |
| 1248 | 1594 | 288 | 686 | 718 |
| 1139 | 1596 | 288 | 687 | 719 |
| 1139 | 1597 | 288 | 688 | 720 |
| 1248 | 1597 | 288 | 689 | 721 |
| 1139 | 1598 | 288 | 690 | 722 |
| 1139 | 1599 | 288 | 691 | 723 |
| 1248 | 1599 | 288 | 692 | 724 |
| 1139 | 1600 | 288 | 694 | 726 |
| 1139 | 1601 | 288 | 695 | 727 |
| 1139 | 1602 | 288 | 696 | 729 |
| 1139 | 1603 | 288 | 697 | 730 |
| 1248 | 1603 | 288 | 698 | 731 |
| 1139 | 1604 | 288 | 699 | 732 |
| 1139 | 1605 | 288 | 700 | 733 |
| 1248 | 1605 | 288 | 701 | 734 |
| 1248 | 1607 | 288 | 702 | 735 |
| 1248 | 1612 | 288 | 703 | 737 |
| 1248 | 1614 | 288 | 704 | 738 |
| 1360 | 1615 | 288 | 705 | 739 |
| 1248 | 1616 | 288 | 706 | 740 |
| 1248 | 1618 | 288 | 707 | 741 |
| 1248 | 1620 | 288 | 708 | 742 |
| 1248 | 1627 | 288 | 709 | 743 |
| 1248 | 1629 | 288 | 710 | 744 |
| 1248 | 1631 | 288 | 711 | 745 |
| 1281 | 1642 | 288 | 712 | 746 |
| 1248 | 1648 | 288 | 713 | 747 |
| 1248 | 1651 | 288 | 714 | 749 |
| 1248 | 1653 | 288 | 715 | 750 |
| 1248 | 1655 | 288 | 716 | 751 |
| 1248 | 1657 | 288 | 717 | 752 |
| 1194 | 1662 | 291 | 719 | 754 |
| 1248 | 1668 | 288 | 721 | 756 |
| 1248 | 1670 | 288 | 722 | 757 |
| 1248 | 1672 | 288 | 723 | 758 |
| 1248 | 1677 | 288 | 724 | 760 |
| 1248 | 1683 | 288 | 725 | 761 |
| 1365 | 1708 | 291 | 728 | 764 |
| 1307 | 1756 | 291 | 729 | 765 |
