---
name: trailing-comment
description: A fixture persona used to validate scripts/check_agents.py.
tools: [read, search]
model: gpt-5.4 # pinned per docs/COPILOT_PORT.md
agents: []
user-invocable: false
---

# Trailing comment form

Fixture persona body used to validate scripts/check_agents.py. This body exists only to
exercise the validator and carries no operational instructions.

## Model attestation

Begin every response with `MODEL-ATTESTATION: <provider>/<model-id>` on its own first line.

