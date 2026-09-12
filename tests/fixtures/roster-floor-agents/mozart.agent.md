---
name: mozart
description: A minimal two-agent roster fixture conductor, used only by tests/fixtures/map-roster-floor.jsonc to exercise the --min-agents roster floor under --agents-dir.
tools: [read, search, agent]
model: claude-opus-5
agents: [jackson]
user-invocable: true
---

# Mozart (roster-floor fixture)

Fixture persona body used to give tests/fixtures/roster-floor-agents/ a valid
two-agent roster for the roster-floor map check. It carries no operational
instructions. The user-scope bundle root is `~/.copilot/mozart`, named here only
as the bare grant target the D3 rule accepts.

## Model attestation

Begin every response with `MODEL-ATTESTATION: <provider>/<model-id>` on its own first line.
