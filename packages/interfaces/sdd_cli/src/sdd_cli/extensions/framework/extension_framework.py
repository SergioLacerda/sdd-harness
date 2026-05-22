"""
SDD v3.1 Extension Framework - Core Components

Allows users to create custom mandates and guidelines for domain-specific specializations.
Built with Pydantic for schema validation and plugin discovery.

Example:
    >>> from extensions.framework import CustomExtension, ExtensionRegistry
    >>>
    >>> @CustomExtension.register("my-domain")
    >>> class MyDomainExtension:
    ...     mandates = [...]
    ...     guidelines = [...]
    >>>
    >>> registry = ExtensionRegistry()
    >>> extensions = registry.load_all()
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ItemType(str, Enum):
    """SDD item type enumeration"""

    MANDATE = "mandate"
    GUIDELINE = "guideline"


class Category(str, Enum):
    """Standard SDD categories"""

    ARCHITECTURE = "architecture"
    GENERAL = "general"
    PERFORMANCE = "performance"
    SECURITY = "security"
    GIT = "git"
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    NAMING = "naming"
    CODE_STYLE = "code-style"


@dataclass
class CustomMandate:
    """Base class for custom mandates in specialized domains"""

    id: str
    type: str  # "HARD" or "SOFT"
    title: str
    description: str
    category: str = Category.GENERAL.value
    domain: str | None = None
    rationale: str | None = None
    validation_commands: list[str] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> list[str]:
        """Validate mandate structure"""
        errors = []

        if not self.id:
            errors.append("Mandate ID cannot be empty")

        if not self.type or self.type not in ["HARD", "SOFT"]:
            errors.append(f"Invalid type: {self.type} (must be HARD or SOFT)")

        if not self.title or len(self.title.strip()) == 0:
            errors.append("Mandate title cannot be empty")

        if not self.description or len(self.description.strip()) == 0:
            errors.append("Mandate description cannot be empty")

        if self.category not in [c.value for c in Category]:
            errors.append(f"Invalid category: {self.category}")

        return errors

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "type": self.type,
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "domain": self.domain,
            "rationale": self.rationale,
            "validation_commands": self.validation_commands,
            "metadata": self.metadata,
        }


@dataclass
class CustomGuideline:
    """Base class for custom guidelines in specialized domains"""

    id: str
    type: str  # "HARD" or "SOFT"
    title: str
    category: str = Category.GENERAL.value
    domain: str | None = None
    description: str | None = None
    examples: list[str] | None = None
    related_mandate: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> list[str]:
        """Validate guideline structure"""
        errors = []

        if not self.id:
            errors.append("Guideline ID cannot be empty")

        if not self.type or self.type not in ["HARD", "SOFT"]:
            errors.append(f"Invalid type: {self.type} (must be HARD or SOFT)")

        if not self.title or len(self.title.strip()) == 0:
            errors.append("Guideline title cannot be empty")

        if self.category not in [c.value for c in Category]:
            errors.append(f"Invalid category: {self.category}")

        return errors

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "type": self.type,
            "title": self.title,
            "category": self.category,
            "domain": self.domain,
            "description": self.description,
            "examples": self.examples,
            "related_mandate": self.related_mandate,
            "metadata": self.metadata,
        }


class ExtensionMetadata:
    """Metadata for extension packages"""

    def __init__(
        self,
        name: str,
        version: str,
        author: str,
        description: str,
        domain: str,
        dependencies: list[str] | None = None,
        license: str = "MIT",
    ):
        self.name = name
        self.version = version
        self.author = author
        self.description = description
        self.domain = domain
        self.dependencies = dependencies or []
        self.license = license

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "version": self.version,
            "author": self.author,
            "description": self.description,
            "domain": self.domain,
            "dependencies": self.dependencies,
            "license": self.license,
        }


class BaseExtension(ABC):
    """Base class for all SDD extensions"""

    # Subclasses must define these
    metadata: ExtensionMetadata
    mandates: list[CustomMandate] = []
    guidelines: list[CustomGuideline] = []

    @abstractmethod
    def initialize(self) -> None:
        """Initialize extension - called on load"""
        pass

    @abstractmethod
    def validate(self) -> list[str]:
        """Validate extension structure"""
        pass

    def get_mandates(self) -> list[CustomMandate]:
        """Get all mandates from this extension"""
        return self.mandates

    def get_guidelines(self) -> list[CustomGuideline]:
        """Get all guidelines from this extension"""
        return self.guidelines

    def to_dict(self) -> dict[str, Any]:
        """Convert extension to dictionary"""
        return {
            "metadata": self.metadata.to_dict(),
            "mandates": [m.to_dict() for m in self.mandates],
            "guidelines": [g.to_dict() for g in self.guidelines],
        }


class ExtensionRegistry:
    """Registry for managing SDD extensions"""

    def __init__(self) -> None:
        self.extensions: dict[str, BaseExtension] = {}
        self.errors: list[str] = []

    def register(self, domain: str, extension: BaseExtension) -> bool:
        """Register an extension"""
        validation_errors = extension.validate()

        if validation_errors:
            self.errors.extend([f"{domain}: {e}" for e in validation_errors])
            return False

        self.extensions[domain] = extension
        return True

    def get(self, domain: str) -> BaseExtension | None:
        """Get extension by domain"""
        return self.extensions.get(domain)

    def get_all(self) -> dict[str, BaseExtension]:
        """Get all registered extensions"""
        return self.extensions.copy()

    def get_mandates(self, domain: str | None = None) -> list[CustomMandate]:
        """Get all mandates, optionally filtered by domain"""
        mandates = []

        if domain:
            ext = self.get(domain)
            if ext:
                mandates = ext.get_mandates()
        else:
            for ext in self.extensions.values():
                mandates.extend(ext.get_mandates())

        return mandates

    def get_guidelines(self, domain: str | None = None) -> list[CustomGuideline]:
        """Get all guidelines, optionally filtered by domain"""
        guidelines = []

        if domain:
            ext = self.get(domain)
            if ext:
                guidelines = ext.get_guidelines()
        else:
            for ext in self.extensions.values():
                guidelines.extend(ext.get_guidelines())

        return guidelines

    def get_stats(self) -> dict[str, Any]:
        """Get statistics about registered extensions"""
        total_mandates = sum(
            len(ext.get_mandates()) for ext in self.extensions.values()
        )
        total_guidelines = sum(
            len(ext.get_guidelines()) for ext in self.extensions.values()
        )

        return {
            "total_extensions": len(self.extensions),
            "domains": list(self.extensions.keys()),
            "total_mandates": total_mandates,
            "total_guidelines": total_guidelines,
            "errors": len(self.errors),
        }


# Global registry
_global_registry: ExtensionRegistry | None = None


def get_registry() -> ExtensionRegistry:
    """Get or create global extension registry"""
    global _global_registry
    if _global_registry is None:
        _global_registry = ExtensionRegistry()
    return _global_registry


def register_extension(domain: str, extension: BaseExtension) -> bool:
    """Register extension in global registry"""
    registry = get_registry()
    return registry.register(domain, extension)


def get_extension(domain: str) -> BaseExtension | None:
    """Get extension from global registry"""
    registry = get_registry()
    return registry.get(domain)


if __name__ == "__main__":
    # Example usage
    print("SDD Extension Framework")  # noqa: T201
    print("=" * 50)  # noqa: T201

    # Create example mandate
    mandate = CustomMandate(
        id="DM001",
        type="HARD",
        title="Domain-Specific Architecture",
        description="Custom architecture rules",
        category=Category.ARCHITECTURE.value,
        domain="example",
    )

    errors = mandate.validate()
    if not errors:
        print("OK: Mandate valid")  # noqa: T201
        print(f"  {mandate.title}")  # noqa: T201
    else:
        print("ERROR: Mandate invalid")  # noqa: T201
        for error in errors:
            print(f"  - {error}")  # noqa: T201

    # Create example guideline
    guideline = CustomGuideline(
        id="DG001",
        type="SOFT",
        title="Domain-Specific Coding Standard",
        category=Category.CODE_STYLE.value,
        domain="example",
        description="Custom coding standards",
    )

    errors = guideline.validate()
    if not errors:
        print("OK: Guideline valid")  # noqa: T201
        print(f"  {guideline.title}")  # noqa: T201
    else:
        print("ERROR: Guideline invalid")  # noqa: T201
        for error in errors:
            print(f"  - {error}")  # noqa: T201
