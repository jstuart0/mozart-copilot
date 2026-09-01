# Page templates

Persona-private overflow for `scott.agent.md` (step 17). Read this when
writing a GitHub wiki feature page, an external-wiki post-mortem, or a
service runbook — the three page shapes below.

### GitHub wiki — Feature page

```markdown
# <Feature name>

<One-sentence description of what it does.>

## What it is

<Two or three paragraphs: what problem it solves, how it fits in the system, who uses it.>

## How to use it

<Concrete: commands, code snippets, configuration examples.>

```language
example
```

## Configuration

<If applicable — env vars, config file keys, defaults.>

## Related

- Ticket: [<ticket-id>](<url>) (if ticketing configured)
- Implementation plan: [`.mozart/plans/<slug>.md`](<repo-relative-or-link>)
- Commits: <SHA>, <SHA>
- Code: [`<path>`](<github-blob-url>)

---
*Documented by scott on <date>. Last updated <date>.*
```

### External wiki — Post-mortem

```markdown
# <Incident summary>

**Date**: <ISO date>
**Severity**: <Critical | High | Medium | Low>
**Duration**: <how long the issue persisted>
**Detection**: <how we noticed — alert? user report? routine check?>

## What happened

<Plain-language summary, two or three paragraphs.>

## Timeline

- **<time>**: <event>
- **<time>**: <event>
- **<time>**: <resolution>

## Root cause

<From dick's investigation. Short summary; link to full investigation doc.>

## Impact

<Who/what was affected. Quantify where possible.>

## What fixed it

<Summary of remediation, with commit SHAs.>

## What we'd do differently

<Prevention or detection improvements.>

## Related

- Ticket: [<ticket-id>](<url>) (if ticketing configured)
- Investigation: `.mozart/investigations/<slug>.md`
- Plan: `.mozart/plans/<slug>.md`
- Commits: <SHAs>

---
*Documented by scott on <date>.*
```

### External wiki — Service runbook

```markdown
# <Service name> runbook

**Service**: <name>
**Repo**: [<repo>](<github-url>)
**Owner**: <person/team>
**Maintained**: <date>

## What this service does

<One paragraph.>

## Where it lives

- Namespace: <k8s namespace>
- URL: <if applicable>
- Dependencies: <upstream services, databases>

## Common operations

### Deploying

<Commands, manifests, what to verify.>

### Restarting

<Commands.>

### Rolling back

<Commands.>

## Troubleshooting

### <Common failure mode 1>
- Symptom:
- Cause:
- Fix:

### <Common failure mode 2>
- Symptom:
- Cause:
- Fix:

## Related

- GitHub wiki (technical details): <link>
- Recent post-mortems: <links>
- Architectural decisions: <links>

---
*Maintained by scott. Last updated <date>.*
```
