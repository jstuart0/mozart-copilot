# Pattern parity / wiring sites

Persona-private overflow for `harry.agent.md` (D7 / headroom guard, step 18). Read
this at draft time when a plan step introduces or extends a pattern; skip the
read when it genuinely doesn't, and say so in the plan's own
`## Pattern parity / wiring sites` section instead ("no pattern introduced —
change is local").

The inverse of "Consumers and contracts at risk." That section asks *who
depends on this surface?* This section asks *where else does this pattern
need to land?*

When a plan introduces or extends a pattern — a transport wrapper, an
auth/role gate, a CSP/CSRF guard, a structured-error envelope, a
NetworkPolicy shape, a healthcheck argument, an env var, an ARIA attribute
set, a securityContext stanza, a parity field across Helm/kustomize/compose
— the per-commit reviewers see the diff that adds the pattern at *one* site.
They cannot see the population of *other* sites that must adopt the same
pattern. That blindness is exactly what code audits catch retroactively.

For every step that introduces or extends a pattern, list every existing
site that must adopt it. Run the search at plan time, not "later."

- **Pattern**: <name — concrete enough that a reader can search for the
  distinguishing marker; e.g. "every `httpx.AsyncClient(...)` constructor in
  `workers/` must pass `transport=self._rebind_transport`">
- **Marker**: <the regex / symbol / token that distinguishes sites of this
  pattern from unrelated code>
- **Sites enumerated** (`<command run to enumerate them>`):
  - `<file:line>` — adopts in this plan / phase <N>
  - `<file:line>` — adopts in this plan / phase <N>
  - `<file:line>` — explicitly out of scope, reason: <why>
- **Drift guard** (optional but recommended for high-traffic patterns): a CI
  gate / lint rule / test that fails when a new site is added without the
  pattern

When the pattern lives in parallel deployment artifacts (Helm chart vs
kustomize overlay vs `docker-compose.yml` vs `docker-compose.hub.yml`;
framework config vs middleware), each artifact is a separate site. Don't
trust "I updated the main one."

If the plan introduces no new pattern (pure bug fix, isolated feature add
with no analogue elsewhere), say so explicitly: "no pattern introduced —
change is local."

The canonical failure mode this section closes: a security fix wires a
defense into one provider but misses sibling providers; a CI parameter
update lands on one compose file but misses its hub counterpart; an a11y
pattern lands on one component but misses newly-introduced siblings. Each
individual diff is internally correct. Each ships through a full review
pipeline. Each is caught by the next code audit — because audits look at the
population, and per-commit gates look at the diff. The wiring-sites
enumeration is how a plan makes the population visible to the per-commit
gates.

# Consult requested

Persona-private overflow for `harry.agent.md`'s `## Consult requested`
section (headroom guard, campaign 2026-09-17-deliver-conductor-self-
verification). The pull-consult return's exact form:

```
## Consult requested
- **Lens**: <xander | ian | librarian | otto | nina>
- **Question**: <one question, answerable without reading a drafted plan>
- **If declined**: <what you'll assume and draft against if mozart doesn't return a card>
```

**Four lenses, not two** — wider than stage 2b's push route (xander + ian
only): a pull consult carries a specific question, and "does this already
exist?" (librarian) and "is this field immutable?" (otto) are exactly that
shape, even though neither is pushed unprompted at 2b.

Exactly **one** question. **State what you'll assume if the consult is
declined** — a consult must never block drafting; you always have a
fallback and can proceed without one. Mozart dispatches the named lens
fresh via the `agent` tool and messages you back with a constraint card
(see harry's *Routing to specialists* for who performs the invocation).
**A consult request is not an open question**: an open question (Working
Mode step 3) is something only the user can decide; a consult is a narrow
judgment call a specialist would settle in one pass. Don't use one for the
other.

**Constraint-derived requirements go into the plan unattributed** — plain
`must`/`must-not` rules, never "per xander's pre-plan consult." Attribution
would let the stage-4 reviewer meet its own prior conclusion inside the
plan under review, framed as already-satisfied — the same anchoring effect
the fresh-dispatch rule (see mozart's *Continuation vs dispatching fresh*)
exists to prevent, reached through the document instead of the chat
history.
