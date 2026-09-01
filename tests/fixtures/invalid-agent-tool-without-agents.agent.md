---
name: invalid-agent-tool-without-agents
description: A fixture persona used to validate scripts/check_agents.py.
tools: [read, search, agent]
model: gpt-5.4
agents: []
user-invocable: false
---

# Agent tool without agents

Fixture persona body used to validate scripts/check_agents.py. This body exists only to
exercise the validator and carries no operational instructions.

## Model attestation

Begin every response with `MODEL-ATTESTATION: <provider>/<model-id>` on its own first line.

