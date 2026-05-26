# ⚙️ Runtime --- Execution Layer

## 🎯 Purpose

Define how the agent executes tasks under governance.

## 📂 Components

- AGENT_ENTRYPOINT.md → full pipeline
- HANDSHAKE.md → initialization
- AGENT_RUNTIME_PROTOCOL.md → minimal contract

## 🔁 Execution Order

HANDSHAKE → ENTRYPOINT → EXECUTION → VALIDATION

## 🔒 Rule

ENTRYPOINT is source of truth.

## 🚨 Failure Mode

Any failure → DEGRADED MODE
