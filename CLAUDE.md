# Project Instructions — open-pajero-maps

## Git workflow

- **Always commit and push after making changes**, unless the user explicitly says
  otherwise for that turn. Commit only the actual code/docs; never stage large or
  regenerable binaries (OSM extracts, disc images, archived third-party specs, cloned
  tool repos, script log output) — see `.gitignore` and `docs/provenance.md`.

## Non-committed materials (BOM)

Every file this project uses that is *not* tracked in git — because it's large,
third-party, or regenerable — must be recorded in `docs/provenance.md`: what it is,
where it came from, and how to reproduce it. When adding a new `.gitignore` rule for
a class of file, add its entry to `docs/provenance.md` in the same commit.
