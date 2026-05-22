"""Integration Engine."""

from pathlib import Path
from typing import Any

import yaml
from pydantic import TypeAdapter, ValidationError

from sdd_integration.engine.context import ExecutionContext
from sdd_integration.engine.step_executor import StepExecutor, StepResult
from sdd_integration.engine.types import (
    KNOWN_STEP_TYPES,
    CommandExecStep,
    ConfigValidateStep,
    ContextSpec,
    FilesystemCopyStep,
    FilesystemCreateStructureStep,
    GenericStep,
    GitCommitStep,
    IntegrationSpec,
    InvalidStep,
    KnownStepSpec,
    StepSpec,
)


class Report:
    """Report."""

    def __init__(self, steps: list[StepResult]) -> None:
        self.steps = steps

    def score(self) -> int:
        """Score."""
        total = len(self.steps)
        ok = sum(1 for s in self.steps if s.success)
        return int((ok / total) * 100) if total else 0

    def pretty(self) -> str:
        """Pretty."""
        lines = ["\n🔍 SDD Doctor Report\n"]

        for s in self.steps:
            icon = "✅" if s.success else "❌"
            lines.append(f"{s.name} {icon} {s.details}")

        lines.append(f"\nScore: {self.score()}/100")
        return "\n".join(lines)


class IntegrationEngine:
    """IntegrationEngine."""

    def __init__(
        self, spec_path: str, context_overrides: dict[str, Any] | None = None
    ) -> None:
        loaded_spec = yaml.safe_load(Path(spec_path).read_text(encoding="utf-8"))
        self.spec = self._coerce_spec(loaded_spec)
        self.spec_dir = Path(spec_path).parent
        self.executor = StepExecutor()
        self.context_overrides = context_overrides or {}

    def run(self) -> Report:
        """Run."""
        effective_spec = self._coerce_spec(dict(self.spec))
        if self.context_overrides:
            context_cfg = self._coerce_context_spec(effective_spec.get("context", {}))
            for key, value in self.context_overrides.items():
                context_cfg[key] = value
            effective_spec["context"] = context_cfg

        context = ExecutionContext.from_spec(effective_spec, self.spec_dir)
        steps = self._coerce_steps(effective_spec.get("steps", []))

        try:
            results = [self.executor.execute(step, context) for step in steps]

        finally:
            context.cleanup()

        return Report(results)

    def _coerce_steps(self, raw_steps: object) -> list[StepSpec]:
        if not isinstance(raw_steps, list):
            return []
        adapter: TypeAdapter[KnownStepSpec] = TypeAdapter(KnownStepSpec)
        steps: list[StepSpec] = []
        for item in raw_steps:
            # If already a Pydantic StepSpec model, append directly
            if isinstance(
                item,
                CommandExecStep
                | FilesystemCreateStructureStep
                | FilesystemCopyStep
                | ConfigValidateStep
                | GitCommitStep
                | GenericStep
                | InvalidStep,
            ):
                steps.append(item)
            elif isinstance(item, dict):
                step_type = str(item.get("type", ""))
                if step_type in KNOWN_STEP_TYPES:
                    try:
                        steps.append(adapter.validate_python(item))
                    except ValidationError as exc:
                        msg = exc.errors(include_url=False)[0].get("msg", str(exc))
                        steps.append(
                            InvalidStep(
                                type=step_type,
                                id=str(item.get("id", "")),
                                parse_error=f"invalid inputs for {step_type}: {msg}",
                            )
                        )
                else:
                    steps.append(GenericStep.model_validate(item))
        return steps

    def _coerce_context_spec(self, raw_context: object) -> ContextSpec:
        context: ContextSpec = {}
        if not isinstance(raw_context, dict):
            return context
        for key, value in raw_context.items():
            context[str(key)] = value
        if "isolation" in context:
            context["isolation"] = bool(context["isolation"])
        if "working_dir" in context:
            context["working_dir"] = str(context["working_dir"])
        return context

    def _coerce_spec(self, raw_spec: object) -> IntegrationSpec:
        spec: IntegrationSpec = {}
        if not isinstance(raw_spec, dict):
            return spec
        spec["context"] = self._coerce_context_spec(raw_spec.get("context", {}))
        spec["steps"] = self._coerce_steps(raw_spec.get("steps", []))
        return spec
