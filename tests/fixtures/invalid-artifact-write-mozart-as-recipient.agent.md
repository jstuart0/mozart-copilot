---
name: invalid-artifact-write-mozart-as-recipient
description: A fixture persona used to validate scripts/check_agents.py.
tools: [read, search]
model: gpt-5.4
agents: []
user-invocable: false
---

# Artifact write with mozart as recipient, not writer

Fixture persona body used to validate scripts/check_agents.py. This body exists only to
exercise the validator, except the line below — the exact shape valerie's validation found
V7c missing: mozart named as the recipient of the artifact, or as a possessive modifier of
it, never as the one performing the write. A whole-sentence "does this name mozart"
check is too wide to catch this; only a subject-position check (mozart immediately
before the verb) does.

Save your findings to the absolute path in mozart's brief, conventionally `<canonical-checkout>/.mozart/investigations/active/<slug>.md`.

## Model attestation

Begin every response with `MODEL-ATTESTATION: <provider>/<model-id>` on its own first line.
