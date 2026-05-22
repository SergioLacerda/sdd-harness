"""Tests for SDD Extension Framework."""

from pathlib import Path
from typing import Any, cast

import pytest

from sdd_cli.extensions.framework.extension_framework import (
    BaseExtension,
    Category,
    CustomGuideline,
    CustomMandate,
    ExtensionMetadata,
    ExtensionRegistry,
    get_registry,
)
from sdd_cli.extensions.framework.plugin_loader import PluginLoader


def _registry() -> Any:
    return cast(Any, ExtensionRegistry)()


class TestCustomMandate:
    """Test CustomMandate creation and validation"""

    def test_create_valid_mandate(self) -> None:
        """Test creating valid mandate"""
        mandate = CustomMandate(
            id="M001",
            type="HARD",
            title="Test Mandate",
            description="Test description",
            category=Category.GENERAL.value,
        )

        assert mandate.id == "M001"
        assert mandate.type == "HARD"
        assert len(mandate.validate()) == 0

    def test_mandate_missing_id(self) -> None:
        """Test mandate with missing ID fails validation"""
        mandate = CustomMandate(
            id="",
            type="HARD",
            title="Test",
            description="Test",
        )

        errors = mandate.validate()
        assert any("ID" in e for e in errors)

    def test_mandate_invalid_type(self) -> None:
        """Test mandate with invalid type fails validation"""
        mandate = CustomMandate(
            id="M001",
            type="INVALID",
            title="Test",
            description="Test",
        )

        errors = mandate.validate()
        assert any("type" in e.lower() for e in errors)

    def test_mandate_missing_title(self) -> None:
        """Test mandate with missing title fails validation"""
        mandate = CustomMandate(
            id="M001",
            type="HARD",
            title="",
            description="Test",
        )

        errors = mandate.validate()
        assert any("title" in e.lower() for e in errors)

    def test_mandate_to_dict(self) -> None:
        """Test mandate conversion to dict"""
        mandate = CustomMandate(
            id="M001",
            type="HARD",
            title="Test",
            description="Test Description",
            category=Category.ARCHITECTURE.value,
            domain="test-domain",
        )

        d = mandate.to_dict()

        assert d["id"] == "M001"
        assert d["type"] == "HARD"
        assert d["title"] == "Test"
        assert d["domain"] == "test-domain"


class TestCustomGuideline:
    """Test CustomGuideline creation and validation"""

    def test_create_valid_guideline(self) -> None:
        """Test creating valid guideline"""
        guideline = CustomGuideline(
            id="G01",
            type="SOFT",
            title="Test Guideline",
            category=Category.GENERAL.value,
        )

        assert guideline.id == "G01"
        assert guideline.type == "SOFT"
        assert len(guideline.validate()) == 0

    def test_guideline_invalid_type(self) -> None:
        """Test guideline with invalid type fails validation"""
        guideline = CustomGuideline(
            id="G01",
            type="MAYBE",
            title="Test",
        )

        errors = guideline.validate()
        assert any("type" in e.lower() for e in errors)

    def test_guideline_to_dict(self) -> None:
        """Test guideline conversion to dict"""
        guideline = CustomGuideline(
            id="G01",
            type="SOFT",
            title="Test Guideline",
            category=Category.TESTING.value,
            domain="test-domain",
            examples=["Example 1", "Example 2"],
        )

        d = guideline.to_dict()

        assert d["id"] == "G01"
        assert d["examples"] == ["Example 1", "Example 2"]
        assert d["domain"] == "test-domain"


class TestExtensionMetadata:
    """Test ExtensionMetadata"""

    def test_create_metadata(self) -> None:
        """Test creating extension metadata"""
        meta = ExtensionMetadata(
            name="Test Extension",
            version="1.0.0",
            author="Test Author",
            description="Test description",
            domain="test-domain",
        )

        assert meta.name == "Test Extension"
        assert meta.version == "1.0.0"
        assert meta.domain == "test-domain"

    def test_metadata_to_dict(self) -> None:
        """Test metadata conversion to dict"""
        meta = ExtensionMetadata(
            name="Test",
            version="1.0.0",
            author="Author",
            description="Desc",
            domain="test",
            dependencies=["dep1", "dep2"],
        )

        d = meta.to_dict()

        assert d["name"] == "Test"
        assert d["dependencies"] == ["dep1", "dep2"]


class TestExtensionRegistry:
    """Test ExtensionRegistry"""

    def test_create_registry(self) -> None:
        """Test creating empty registry"""
        registry = _registry()

        assert len(registry.get_all()) == 0

    def test_register_extension(self) -> None:
        """Test registering an extension"""
        registry = _registry()

        # Create a mock extension
        class MockExtension(BaseExtension):
            metadata = ExtensionMetadata("Test", "1.0", "Author", "Desc", "test")
            mandates = []
            guidelines = []

            def initialize(self) -> None:
                pass

            def validate(self) -> list[str]:
                return []

        ext = MockExtension()
        result = registry.register("test-domain", ext)

        assert result is True
        assert registry.get("test-domain") is not None

    def test_get_mandates_all(self) -> None:
        """Test getting all mandates from registry"""
        registry = _registry()

        class MockExtension(BaseExtension):
            metadata = ExtensionMetadata("Test", "1.0", "Author", "Desc", "test")
            mandates = [
                CustomMandate("M001", "HARD", "Test", "Test", category="general")
            ]
            guidelines = []

            def initialize(self) -> None:
                pass

            def validate(self) -> list[str]:
                return []

        ext = MockExtension()
        registry.register("test-domain", ext)

        mandates = registry.get_mandates()
        assert len(mandates) == 1

    def test_get_stats(self) -> None:
        """Test getting registry statistics"""
        registry = _registry()

        class MockExtension(BaseExtension):
            metadata = ExtensionMetadata("Test", "1.0", "Author", "Desc", "test")
            mandates = [
                CustomMandate("M001", "HARD", "Test", "Test", category="general")
            ]
            guidelines = [CustomGuideline("G01", "SOFT", "Test", category="general")]

            def initialize(self) -> None:
                pass

            def validate(self) -> list[str]:
                return []

        ext = MockExtension()
        registry.register("test-domain", ext)

        stats = registry.get_stats()

        assert stats["total_extensions"] == 1
        assert stats["total_mandates"] == 1
        assert stats["total_guidelines"] == 1
        assert "test-domain" in stats["domains"]


class TestPluginLoader:
    """Test PluginLoader (if plugin examples exist)"""

    def test_discover_plugins(self) -> None:
        """Test plugin discovery"""
        # Create a test loader pointing to examples directory
        loader = PluginLoader(str(Path(__file__).parent.parent / "examples"))

        plugins = loader.discover_plugins()

        # Should find at least the examples (if they exist)
        # For now, just test that the method works
        assert isinstance(plugins, list)


class TestGlobalRegistry:
    """Test global registry functions"""

    def test_get_registry(self) -> None:
        """Test getting global registry"""
        registry = get_registry()

        assert registry is not None
        assert isinstance(registry, ExtensionRegistry)

    def test_get_registry_singleton(self) -> None:
        """Test that global registry is singleton"""
        registry1 = get_registry()
        registry2 = get_registry()

        assert registry1 is registry2


# Stub for testing (would be replaced by actual plugin)
class MockGameMasterExtension(BaseExtension):
    """Mock Game Master extension for testing"""

    metadata = ExtensionMetadata(
        name="Game Master API",
        version="1.0.0",
        author="Test",
        description="Test GM extension",
        domain="game-master-api",
    )
    mandates = [
        CustomMandate(
            "GMM001", "HARD", "Narrative State", "Test", category="architecture"
        )
    ]
    guidelines = [
        CustomGuideline("GMG01", "SOFT", "Random Generation", category="security")
    ]

    def initialize(self) -> None:
        pass

    def validate(self) -> list[str]:
        return []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
