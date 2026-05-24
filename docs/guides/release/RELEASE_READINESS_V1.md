# Release Readiness v1.0 Checklist

Approved: yes
Decision-Owner: Sergio Lacerda
Decision-Date: 2026-05-24
Target-Version: v1.0.0

## Pre-Release Criteria

- [x] SemVer tag validation gate exists (`release.yml`, `release-dry-run.yml`)
- [x] Changelog entry validation gate exists
- [x] Unit/integration release-critical tests run in release workflows
- [x] Strict golden policy gate runs in release workflows
- [x] Version/tag consistency check is enforced
- [x] Build + artifact upload stage is defined
- [x] SBOM generation is defined
- [x] Artifact signing step is defined
- [x] Provenance/attestation step is defined

## Gate Points

1. `release-dry-run.yml` validates release candidate before publish
2. `release.yml` blocks release on validate/build failures
3. strict golden policy is required in both release paths

## Rollback Contract

### Trigger Conditions

Rollback is recommended when one or more conditions are true after release:

- critical regression in release-critical tests (post-release verification)
- signing/provenance verification fails downstream
- operational severity exceeds accepted threshold

### Rollback Command Path

1. Identify last known good tag in GitHub Releases.
2. Re-deploy previous artifact set from signed release assets.
3. Open incident entry in `docs/incidents/FAILURE_LEDGER.md`.
4. Record postmortem and update playbooks in `docs/incidents/PLAYBOOKS.md`.
