---
name: invalid-unquoted-colon-description
description: A fixture persona used to validate scripts/check_agents.py: this value is deliberately unquoted and contains a colon-space, reproducing the live-parser incident (copilot CLI 1.0.82, 2026-09-01).
tools: [read, search]
model: gpt-5.4
agents: []
user-invocable: false
---

# Invalid unquoted colon description

Fixture persona body used to validate scripts/check_agents.py. This body exists only to
exercise the validator and carries no operational instructions.

## Model attestation

Begin every response with `MODEL-ATTESTATION: <provider>/<model-id>` on its own first line.
