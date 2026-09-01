---
name: valid-grant-line
description: A fixture persona used to validate scripts/check_agents.py.
tools: [read, search]
model: gpt-5.4
agents: []
user-invocable: false
---

# Valid grant line

Fixture persona body used to validate scripts/check_agents.py. This body exists only to
exercise the validator and carries no operational instructions.

The user-scope root ~/.copilot/mozart is empty; run `scripts/install-bundle.sh --user-scope --apply` to populate it (D3 rule 1's remediation sentence, root and grant instruction on one line).

## Model attestation

Begin every response with `MODEL-ATTESTATION: <provider>/<model-id>` on its own first line.
