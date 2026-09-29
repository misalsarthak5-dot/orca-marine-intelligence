"""
ORCA Evidence & RAG Layer — Phase 6 Package
Exposes schemas, store, retriever, seed corpus, provenance, and service.
"""

from evidence.schemas import (
    SourceAuthority,
    EvidenceClassification,
    RetrievalStatus,
    EvidenceDocument,
    EvidenceChunk,
    EvidenceCitation,
    EvidenceQuery,
    EvidenceResult,
    EvidenceContext,
)
from evidence.store import BaseEvidenceStore, InMemoryEvidenceStore
from evidence.retriever import EvidenceRetriever
from evidence.corpus import SEED_EVIDENCE_DOCUMENTS
from evidence.provenance import verify_telemetry_isolation, format_citations_block
from evidence.service import EvidenceService

__all__ = [
    "SourceAuthority",
    "EvidenceClassification",
    "RetrievalStatus",
    "EvidenceDocument",
    "EvidenceChunk",
    "EvidenceCitation",
    "EvidenceQuery",
    "EvidenceResult",
    "EvidenceContext",
    "BaseEvidenceStore",
    "InMemoryEvidenceStore",
    "EvidenceRetriever",
    "SEED_EVIDENCE_DOCUMENTS",
    "verify_telemetry_isolation",
    "format_citations_block",
    "EvidenceService",
]
