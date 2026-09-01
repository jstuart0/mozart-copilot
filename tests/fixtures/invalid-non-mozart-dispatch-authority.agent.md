---
name: invalid-non-mozart-dispatch-authority
description: A fixture persona used to validate scripts/check_agents.py.
tools: [read, search, agent]
model: gpt-5.4
agents: [bob, dexter]
user-invocable: false
---

# Non-mozart dispatch authority

Fixture persona body used to validate scripts/check_agents.py. This body exists only to
exercise the validator and carries no operational instructions. D10 reserves dispatch
authority (the `agent` tool plus a non-empty `agents:` allowlist) for `mozart` alone —
this fixture is internally self-consistent (agent-tool/agents-nonempty correlation holds)
but must still be rejected because it isn't `mozart`.

## Model attestation

Begin every response with `MODEL-ATTESTATION: <provider>/<model-id>` on its own first line.
