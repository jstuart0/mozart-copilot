---
name: invalid-user-bundle-shell-copy
description: A fixture persona used to validate scripts/check_agents.py.
tools: [read, search]
model: gpt-5.4
agents: []
user-invocable: false
---

# Invalid user bundle shell copy

Fixture persona body used to validate scripts/check_agents.py. This body exists only to
exercise the validator and carries no operational instructions.

Run `cp -R ~/.copilot/mozart .` to copy the bundle locally.

## Model attestation

Begin every response with `MODEL-ATTESTATION: <provider>/<model-id>` on its own first line.
