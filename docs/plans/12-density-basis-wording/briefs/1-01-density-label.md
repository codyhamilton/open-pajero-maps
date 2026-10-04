# Correct the carried density basis label

Consumer: density report readers and the next plan 03 worker.
Owned paths: census `LENGTH_BASIS` and plan 03 implementation resolution note.
Depends on: calculation already landed at `2f874e3`. Runs alongside: nothing.

## Contract and goal

Read the committed design's Road-density report contract. Change the stale
leaf-bounds phrase to frame-bounds wording without changing the calculation
or historical profiles. Record the existing carried item's resolution.

## Done evidence

Inspect the emitted basis using `Census.to_dict()`; run the existing four
density tests. No new test for a string replacement. Write a report before
committing, including deviations and any remaining work. One worker only.
