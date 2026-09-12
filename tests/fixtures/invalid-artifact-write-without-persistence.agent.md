---
name: invalid-artifact-write-without-persistence
description: A fixture persona used to validate scripts/check_agents.py.
tools: [read, search]
model: gpt-5.4
agents: []
user-invocable: false
---

# Artifact write without persistence

Fixture persona body used to validate scripts/check_agents.py. This body exists only to
exercise the validator and carries no operational instructions, except the line below,
which claims a write this persona's grant cannot perform.

Write your findings to the **absolute** path `<canonical-checkout>/.mozart/investigations/active/<slug>.md` when done.

## Model attestation

Begin every response with `MODEL-ATTESTATION: <provider>/<model-id>` on its own first line.
