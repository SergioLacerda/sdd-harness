# Compiler I/O Contract

**Phase 0 freeze — 2026-06-29**
**Applies to:** current Python `GovernanceCompiler` and future Go `sdd-compile` binary.

This document defines the exact artifact format the Go binary must produce.
The contract tests in `tests/contract/test_compiler_output_contract.py` enforce
every schema and behavioral claim listed here.

---

## 1. Artifact Inventory

| File | Format | Direction |
|------|--------|-----------|
| `governance-core.json` | UTF-8 JSON | input to GovernanceCompiler; output to consumers |
| `governance-client.json` | UTF-8 JSON | input to GovernanceCompiler; output to consumers |
| `governance-core.compiled.msgpack` | plain msgpack (no header) | output only |
| `governance-client-template.compiled.msgpack` | plain msgpack (no header) | output only |
| `metadata-core.json` | UTF-8 JSON | output only |
| `metadata-client-template.json` | UTF-8 JSON | output only |
| `governance-core.json.sig` | UTF-8 JSON manifest | output, optional (signing) |
| `governance-client.json.sig` | UTF-8 JSON manifest | output, optional (signing) |

---

## 2. `governance-core.json` Schema

```json
{
  "category": "CORE",
  "version": "3.0",
  "fingerprint": "<64 lowercase hex chars>",
  "items": [
    {
      "id": "<letter><2-3 digits>",
      "type": "MANDATE",
      "title": "<string>",
      "status": "<string>",
      "criticality": "<high|medium|low>",
      "summary_minimal": "<string or null>",
      "summary_runtime": "<string or null>"
    }
  ]
}
```

Required fields: `category`, `version`, `fingerprint`, `items`.
Each item must have at minimum: `id`, `type`, `title`.
Item `id` must match `^[A-Z]\d{2,3}$`.

---

## 3. `governance-client.json` Schema

```json
{
  "category": "CLIENT",
  "version": "3.0",
  "fingerprint": "<64 lowercase hex chars>",
  "fingerprint_core_salt": "<64 lowercase hex chars>",
  "items": [...]
}
```

Required fields: `category`, `version`, `fingerprint`, `fingerprint_core_salt`, `items`.

Invariant: `fingerprint_core_salt` MUST equal `governance-core.json["fingerprint"]`.
Invariant: `fingerprint` MUST differ from `governance-core.json["fingerprint"]`.

---

## 4. `governance-core.compiled.msgpack` and `governance-client-template.compiled.msgpack`

- **Format:** plain msgpack dictionary, no magic header prefix.
- **Content:** same structure as the corresponding JSON artifact.
- **Decoding:** `msgpack.unpackb(raw, raw=False)` returns a `dict`.
- First byte is a msgpack fixmap tag (0x8x) or map16/32 (0xde/0xdf), never a file-type magic byte.

---

## 5. `metadata-core.json` Schema

```json
{
  "version": "3.0",
  "type": "core",
  "generated_at": "<ISO 8601 UTC string>",
  "fingerprint": "<64 lowercase hex chars>",
  "item_count": <positive integer>,
  "items_by_type": { "<TYPE>": <count> },
  "items_by_criticality": { "<level>": <count> },
  "readonly": true,
  "customizable": false
}
```

Required fields: `version`, `type`, `generated_at`, `fingerprint`, `item_count`.

Invariant: `fingerprint` MUST equal `governance-core.json["fingerprint"]`.

---

## 6. `metadata-client-template.json` Schema

Same shape as `metadata-core.json` with:
- `"type": "client-template"`
- `"readonly": false`
- `"customizable": true`
- `"fingerprint_core_salt": "<64 lowercase hex chars>"` (equals core fingerprint)

---

## 7. Signature Manifest Schema (`*.sig`)

```json
{
  "schema_version": "1.0",
  "algorithm": "ed25519",
  "key_id": "<string>",
  "artifact_name": "<filename.json>",
  "profile": "<master|client>",
  "payload_hash": "<64 lowercase hex chars>",
  "signature": "<base64-encoded Ed25519 signature>",
  "signed_at": "<ISO 8601 UTC string ending in Z>"
}
```

`payload_hash` is `SHA-256(raw_bytes_of_artifact_json_file)` — the SHA-256 of the
exact bytes written to disk (with indentation and encoding preserved).

Signing is optional: controlled by `SDD_SIGNING_PRIVATE_KEY_FILE` and
`SDD_SIGNING_REQUIRED` environment variables.

---

## 8. Fingerprint Behavior (SQ-004 Resolution)

The `fingerprint` field in compiled artifacts is the **governance workspace fingerprint** —
a SHA-256 hash computed by the SDD compilation pipeline from the source governance rules
(mandates, guidelines, policies). It is NOT derived from the compiled artifact bytes.

**Go binary behavior:**
1. Read the fingerprint from the input JSON data (pre-computed upstream by the pipeline).
2. Preserve it unchanged in output artifacts and metadata.
3. Do NOT recompute the fingerprint from output bytes.

**Fingerprint invariants:**
- `governance-core.json["fingerprint"]` == `metadata-core.json["fingerprint"]`
- `governance-client.json["fingerprint_core_salt"]` == `governance-core.json["fingerprint"]`
- `governance-core.json["fingerprint"]` != `governance-client.json["fingerprint"]`
- All fingerprint fields are exactly 64 lowercase hex chars (SHA-256 hex digest).

**Signing vs. governance fingerprint:**
- Governance fingerprint: opaque to the compiler, comes from pipeline input, identifies the governance version.
- Signing payload hash: `SHA-256(raw_file_bytes)` of the written JSON file, used only in `.sig` manifests.
These are two distinct hashes with different purposes.

---

## 9. Go/no-go Gate

Phase 0 is complete when `tests/contract/test_compiler_output_contract.py` passes
against the Python compiler output with `make ci-pr` green. This establishes the
behavioral baseline the Go binary must satisfy.
