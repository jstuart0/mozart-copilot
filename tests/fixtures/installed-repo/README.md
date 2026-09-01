# acme-widgets

A simulated consuming repository, used only by the Phase-7 install-bundle
verification gate (`scripts/install-bundle.sh --target`). This file, and
`docs/`, exist to prove the installer is non-destructive to a repo's
pre-existing content — not to assume it. The gate copies this fixture to a
temp directory before installing into the copy; this file is never mutated
in place.

This repo has no `.github/` directory of its own before install, so a
correct `--target` install must create `.github/agents/` and
`.github/mozart/` without touching anything above them.
