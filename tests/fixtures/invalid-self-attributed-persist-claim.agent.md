---
name: invalid-self-attributed-persist-claim
description: A fixture persona used to validate scripts/check_agents.py.
tools: [read, search]
model: gpt-5.4
agents: []
user-invocable: false
---

# Self-attributed persist claim

Fixture persona body used to validate scripts/check_agents.py. This body exists only to
exercise the validator, except the line below, which uses "persist" — a word V7c's verb
list once missed — to claim a write this persona's grant cannot perform, with no mozart
in the sentence to attribute it to instead.

Persist your findings to the **absolute** path `<canonical-checkout>/.mozart/investigations/active/<slug>.md` when done.

## Model attestation

Begin every response with `MODEL-ATTESTATION: <provider>/<model-id>` on its own first line.
