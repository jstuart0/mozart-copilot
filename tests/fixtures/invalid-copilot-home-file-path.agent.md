---
name: invalid-copilot-home-file-path
description: A fixture persona used to validate scripts/check_agents.py.
tools: [read, search]
model: gpt-5.4
agents: []
user-invocable: false
---

# Invalid COPILOT_HOME file path

Fixture persona body used to validate scripts/check_agents.py. This body exists only to
exercise the validator and carries no operational instructions.

Read `$COPILOT_HOME/mozart/manual/INDEX.md` for further instructions.

## Model attestation

Begin every response with `MODEL-ATTESTATION: <provider>/<model-id>` on its own first line.
