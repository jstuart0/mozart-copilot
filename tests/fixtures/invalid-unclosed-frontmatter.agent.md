---
name: invalid-unclosed-frontmatter
description: A fixture proving unclosed frontmatter is a parse error, never a partial parse.
tools: [read, search]
model: gpt-5.4
agents: []
user-invocable: false

# No closing delimiter

This file never closes its frontmatter block, so it must be rejected outright rather than
partially parsed.
