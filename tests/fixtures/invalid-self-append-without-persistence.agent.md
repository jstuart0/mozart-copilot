---
name: invalid-self-append-without-persistence
description: A fixture persona used to validate scripts/check_agents.py.
tools: [read, search]
model: gpt-5.4
agents: []
user-invocable: false
---

# Self-append without persistence

Fixture persona body used to validate scripts/check_agents.py. This body exists only to
exercise the validator and carries no operational instructions.

## Field notes (append-only)

See the bundled `.github/mozart/LEARNINGS.md` for the protocol. Append cross-project patterns you discover here. **Do not edit any other section of this file** — those are human-authored contracts.

## Model attestation

Begin every response with `MODEL-ATTESTATION: <provider>/<model-id>` on its own first line.
