"""
ORCA Evidence Service — Phase 6
High-level service coordinating seed corpus indexing, store access,
retrieval, and context preparation for reasoning and synthesis.
"""

from typing import Dict, Any, List, Optional
from evidence.schemas import (
    EvidenceDocument,
    EvidenceQuery,
    EvidenceResult,
    EvidenceContext,
    RetrievalStatus,
)
from evidence.store import InMemoryEvidenceStore, BaseEvidenceStore
from evidence.retriever import EvidenceRetriever
from evidence.corpus import SEED_EVIDENCE_DOCUMENTS


class EvidenceService:
    """
    Singleton-capable Service managing ORCA's maritime evidence corpus,
    indexing, and retrieval operations.
    """

    def __init__(self, store: Optional[BaseEvidenceStore] = None):
        if store is None:
            self.store = InMemoryEvidenceStore()
            # Populate with official seed reference corpus
            self.store.add_documents(SEED_EVIDENCE_DOCUMENTS)
        else:
            self.store = store

        self.retriever = EvidenceRetriever(store=self.store)

    def retrieve_context(
        self,
        query: str,
        language: str = "en",
        max_results: int = 3,
        filters: Optional[Dict[str, Any]] = None,
    ) -> EvidenceContext:
        """
        Retrieve contextual reference evidence for a given query.
        Returns an EvidenceContext object with chunks, citations, status, and caveats.
        """
        ev_query = EvidenceQuery(
            query=query,
            language=language,
            filters=filters or {},
            max_results=max_results,
        )

        result: EvidenceResult = self.retriever.retrieve(ev_query)

        uncertainties: List[str] = []
        if result.retrieval_status == RetrievalStatus.EMPTY:
            uncertainties.append("No specific reference documentation or regulatory guidance matched this query.")
        elif result.retrieval_status == RetrievalStatus.UNAVAILABLE:
            uncertainties.append("Maritime reference knowledge base is currently unavailable.")
        elif result.retrieval_status == RetrievalStatus.ERROR:
            uncertainties.append(f"Error querying maritime reference knowledge base: {', '.join(result.errors)}")

        return EvidenceContext(
            query=query,
            retrieved_evidence=result.chunks,
            source_count=result.source_count,
            retrieval_status=result.retrieval_status,
            uncertainties=uncertainties,
            citations=result.citations,
        )

    def add_custom_document(self, doc: EvidenceDocument) -> None:
        """Add custom authoritative document to knowledge store."""
        self.store.add_document(doc)

    def get_document(self, doc_id: str) -> Optional[EvidenceDocument]:
        """Fetch document by id."""
        return self.store.get_document(doc_id)

    @property
    def document_count(self) -> int:
        return self.store.count()
