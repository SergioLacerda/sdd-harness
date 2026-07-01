"""sdd_pages — GitHub Pages publishing, metadata, compression, and indexing.

Public API:
    PublisherInterface, GitHubPagesPublisher, PublishResult — publishing
    MetadataExtractor, DocumentMetadata — YAML frontmatter parsing
    CompressionEngine, CompressionResult — gzip/brotli compression
    SelectorGenerator, DocumentIndexer, DocumentEntry — indexing
    IndexValidator, ValidationResult — index validation
    DeltaIndexer — incremental indexing via git diff / hash cache
"""

from sdd_pages.compression import CompressionEngine, CompressionResult
from sdd_pages.delta import DeltaIndexer
from sdd_pages.metadata import DocumentMetadata, MetadataExtractor
from sdd_pages.publisher import (
    GitHubPagesPublisher,
    PublisherInterface,
    PublishResult,
)
from sdd_pages.selector import DocumentEntry, DocumentIndexer, SelectorGenerator
from sdd_pages.validator import IndexValidator, ValidationResult

__all__ = [
    "CompressionEngine",
    "CompressionResult",
    "DeltaIndexer",
    "DocumentMetadata",
    "MetadataExtractor",
    "GitHubPagesPublisher",
    "PublisherInterface",
    "PublishResult",
    "DocumentEntry",
    "DocumentIndexer",
    "SelectorGenerator",
    "IndexValidator",
    "ValidationResult",
]
