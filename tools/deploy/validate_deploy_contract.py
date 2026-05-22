#!/usr/bin/env python3
"""Validate deploy contract inputs for local-first CI/CD readiness checks."""

from __future__ import annotations

import argparse
import json
import os
import re
from collections.abc import Sequence
from typing import TypedDict

DEFAULT_CANARY = (10, 25, 50, 100)
_ENVIRONMENTS = {"staging", "production"}
_MODES = {"contract", "real"}
_DIGEST_RE = re.compile(r"^sha256:[a-f0-9]{64}$")


class ValidationResult(TypedDict):
    ok: bool
    errors: list[str]
    warnings: list[str]
    canary_steps: tuple[int, ...]


class DeployReport(TypedDict):
    ok: bool
    target_env: str
    mode: str
    enable_real_deploy: bool
    image_digest: str
    rollback_to: str
    canary_steps: list[int]
    errors: list[str]
    warnings: list[str]


def _parse_canary(raw: str) -> tuple[int, ...]:
    parts = [chunk.strip() for chunk in raw.split(",") if chunk.strip()]
    if not parts:
        raise ValueError("canary policy is empty")
    values = tuple(int(part) for part in parts)
    if values[-1] != 100:
        raise ValueError("canary policy must end at 100")
    if any(value <= 0 or value > 100 for value in values):
        raise ValueError("canary percentages must be within 1..100")
    if any(values[i] >= values[i + 1] for i in range(len(values) - 1)):
        raise ValueError("canary percentages must be strictly increasing")
    return values


def validate_contract(
    *,
    target_env: str,
    mode: str,
    image_digest: str,
    rollback_to: str,
    canary_policy: str,
    enable_real_deploy: bool,
) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []

    if target_env not in _ENVIRONMENTS:
        errors.append(
            f"target_env must be one of {sorted(_ENVIRONMENTS)}; got '{target_env}'"
        )

    if mode not in _MODES:
        errors.append(f"mode must be one of {sorted(_MODES)}; got '{mode}'")

    if not _DIGEST_RE.match(image_digest):
        errors.append("image_digest must match sha256:<64 hex chars>")

    if not rollback_to:
        errors.append("rollback_to is required for auditable rollback contract")
    elif rollback_to != "previous" and not _DIGEST_RE.match(rollback_to):
        errors.append("rollback_to must be 'previous' or sha256:<64 hex chars>")

    canary_steps: tuple[int, ...]
    try:
        canary_steps = _parse_canary(canary_policy)
    except ValueError as exc:
        canary_steps = DEFAULT_CANARY
        errors.append(f"invalid canary_policy: {exc}")

    if mode == "real" and not enable_real_deploy:
        errors.append("mode=real requires ENABLE_REAL_DEPLOY=true (safety guardrail)")

    if mode == "contract" and enable_real_deploy:
        warnings.append(
            "ENABLE_REAL_DEPLOY=true ignored because mode=contract; no cluster action will run"
        )

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "canary_steps": canary_steps,
    }


def _build_report(args: argparse.Namespace, result: ValidationResult) -> DeployReport:
    return {
        "ok": result["ok"],
        "target_env": args.target_env,
        "mode": args.mode,
        "enable_real_deploy": args.enable_real_deploy,
        "image_digest": args.image_digest,
        "rollback_to": args.rollback_to,
        "canary_steps": list(result["canary_steps"]),
        "errors": result["errors"],
        "warnings": result["warnings"],
    }


def _write_summary(path: str | None, report: DeployReport) -> None:
    if not path:
        return
    lines = [
        "## Deployment Readiness Report",
        f"- Status: {'READY' if report['ok'] else 'BLOCKED'}",
        f"- Environment: {report['target_env']}",
        f"- Mode: {report['mode']}",
        f"- Canary policy: {', '.join(str(step) for step in report['canary_steps'])}",
        f"- Rollback target: {report['rollback_to']}",
    ]
    errors = report["errors"]
    warnings = report["warnings"]
    if errors:
        lines.append("- Errors:")
        lines.extend(f"  - {item}" for item in errors)
    if warnings:
        lines.append("- Warnings:")
        lines.extend(f"  - {item}" for item in warnings)
    with open(path, "a", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate deploy contract")
    parser.add_argument("--target-env", required=True, help="staging|production")
    parser.add_argument("--mode", default="contract", help="contract|real")
    parser.add_argument("--image-digest", required=True, help="sha256:<64 hex chars>")
    parser.add_argument(
        "--rollback-to",
        required=True,
        help="'previous' or sha256:<64 hex chars>",
    )
    parser.add_argument(
        "--canary-policy",
        default=",".join(map(str, DEFAULT_CANARY)),
        help="comma-separated percentages, default 10,25,50,100",
    )
    parser.add_argument(
        "--enable-real-deploy",
        action="store_true",
        help="enable real deploy mode",
    )
    parser.add_argument("--json", action="store_true", help="print json report")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    result = validate_contract(
        target_env=args.target_env,
        mode=args.mode,
        image_digest=args.image_digest,
        rollback_to=args.rollback_to,
        canary_policy=args.canary_policy,
        enable_real_deploy=args.enable_real_deploy,
    )

    report = _build_report(args, result)
    summary_file = os.getenv("GITHUB_STEP_SUMMARY")
    _write_summary(summary_file, report)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        for warning in result["warnings"]:
            print(f"WARNING: {warning}")
        if result["ok"]:
            print(
                "Deploy contract OK: "
                f"env={args.target_env} mode={args.mode} canary={result['canary_steps']}"
            )
        else:
            print("ERROR: deploy contract validation failed:")
            for error in result["errors"]:
                print(f"  - {error}")

    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
