# Governance Source And Runtime Model

## Authority

`docs/` is the authored source of truth for governance knowledge in this
repository.

`.sdd/` is runtime/build output. Agents and CLI flows consume `.sdd/`, but
governance documentation changes should be made in `docs/` and then generated
into `.sdd/`.

## Source Registry

The classification registry is:

```text
docs/spec/canonical/governance-sources.yaml
```

It declares which docs files are active mandate sources, guideline sources,
handbook sources, mirrors, or docs-only references. Runtime generation and drift
validation use this registry instead of scanning the whole docs tree.

## Runtime Outputs

Generated runtime artifacts include:

```text
.sdd/metadata.json
.sdd/compiled/governance-core.json
.sdd/compiled/governance-client.json
.sdd/source/mandates/mandates.md
.sdd/source/guidelines.*
.sdd/source/handbook/**
```

If these outputs disagree with `docs/spec/canonical/governance-sources.yaml`,
the mismatch is build drift. Fix the source in `docs/` or regenerate runtime
artifacts; do not treat `.sdd/` as the authored documentation source.

## Runtime Handbook

Consultive runtime guidance is generated from classified handbook docs into:

```text
.sdd/source/handbook/index.yaml
.sdd/source/handbook/**/*.yaml
```

The handbook is not an enforcement surface. Compiled mandates and guidelines
remain the first runtime authority. Agents may query the handbook by task type,
mandate reference, operation phase, or risk level after loading applicable
mandates and guidelines.

## Publication Rule

Published docs can link to active governance IDs, but a page only has runtime
authority when the source registry classifies it as an active runtime source.
Mirrors and generated/publication pages must identify their source or generated
status.
