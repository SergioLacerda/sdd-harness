# Mandate: Any change that could require users to update their code or governance artifacts must follow this RFC process

**Type:** HARD MANDATE
**ID:** M006
**Category:** Governance / Process

---

## 🎯 Goal

Any change that could require users to update their code or governance artifacts must follow this RFC process.

---

## 📜 Requirement

Breaking changes to the SDD framework (CLI commands, governance schema, artifact formats, or runtime contracts) MUST go through a formal Request for Comments (RFC) process before shipping.

---

## ⚖️ Rationale

Unilateral breaking changes erode trust between the framework and its adopters. The RFC process ensures backward-compatibility concerns are surfaced early and that impacted users have a migration path.

---

## ✅ Validation

- [ ] A GitHub issue or PR is opened with the `rfc` label before merging any breaking change.
- [ ] The RFC describes what breaks, who is affected, and what the migration path is.
- [ ] Downstream teams are notified via the RFC before the change ships.
