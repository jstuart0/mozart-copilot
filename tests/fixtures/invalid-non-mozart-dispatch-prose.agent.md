---
name: invalid-non-mozart-dispatch-prose
description: A fixture persona used to validate scripts/check_agents.py.
tools: [read, search]
model: gpt-5.4
agents: []
user-invocable: false
---

# Non-mozart dispatch prose

Fixture persona body used to validate scripts/check_agents.py. This body exists only to
exercise the validator, except the line below, whose frontmatter is clean (no `agent`
tool, no non-empty `agents:` allowlist — D10 has nothing to say about it) but whose
prose attributes dispatch to a non-mozart caller.

A specialist invokes you directly when it needs a quick lookup.

## Model attestation

Begin every response with `MODEL-ATTESTATION: <provider>/<model-id>` on its own first line.
