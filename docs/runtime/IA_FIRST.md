# IA First Runtime Authoring Standard

## Context Budget

- Scope: Runtime docs only (`docs/runtime/**`)
- Consumer priority: AI agents first, humans second
- Budget rule: keep sections compact and deterministic

## Scope

- This standard governs runtime authoring patterns and PATH-family documents.
- It does not rewrite canonical specs, ADRs, or product guides.

## Entry Checklist

- Use fixed section order for same-family files.
- Keep each section to at most 5 bullet items.
- Use exact file references for cross-links.

## MUST

- Use list-first writing; avoid long prose blocks.
- Keep section headers stable for machine parsing.
- Declare explicit constraints and escalation triggers.
- Keep path-specific guidance distinct by execution type.

## MUST NOT

- Duplicate the same body across PATH files.
- Mix operational guidance and canonical governance definitions.
- Rely on implicit references like "the previous file".

## Escalation

- If a runtime doc needs architectural policy changes, escalate to `docs/spec/canonical/**` decision flow.
- If a PATH file exceeds schema limits, split concerns into dedicated runtime docs.

## PATH Family Schema

```markdown
# PATH {X} - {LABEL}

## Context Budget
## Scope
## Entry Checklist
## MUST
## MUST NOT
## Escalation
```
