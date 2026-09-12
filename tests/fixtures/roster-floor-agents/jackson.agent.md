---
name: jackson
description: A minimal roster fixture builder, used only by tests/fixtures/map-roster-floor.jsonc to exercise the --min-agents roster floor under --agents-dir.
tools: [read, search, edit]
model: claude-sonnet-4.5
agents: []
user-invocable: false
---

# Jackson (roster-floor fixture)

Fixture persona body used to give tests/fixtures/roster-floor-agents/ a valid
two-agent roster for the roster-floor map check. It carries no operational
instructions.

## Model attestation

Begin every response with `MODEL-ATTESTATION: <provider>/<model-id>` on its own first line.
