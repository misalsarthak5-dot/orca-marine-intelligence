"""
ORCA Evidence Store — Phase 6
Provides deterministic local document and chunk indexing, BM25-style lexical scoring,
and filtering. Isolates retrieval implementation behind an abstract BaseEvidenceStore
to allow future plug-in vector implementations without altering consumer interfaces.
"""

from abc import ABC, abstractmethod
import math
import re
from typing import Dict, List, Optional, Set
from evidence.schemas import (
    EvidenceDocument,
    EvidenceChunk,
    EvidenceQuery,
    SourceAuthority,
    EvidenceClassification,
)

# Relative authority multipliers for deterministic scoring
AUTHORITY_WEIGHTS: Dict[SourceAuthority, float] = {
    SourceAuthority.OFFICIAL_GOVERNMENT: 1.30,
    SourceAuthority.OFFICIAL_RESEARCH: 1.20,
    SourceAuthority.OFFICIAL_DOCUMENTATION: 1.15,
    SourceAuthority.VERIFIED_REFERENCE: 1.00,
    SourceAuthority.GENERAL_REFERENCE: 0.80,
    SourceAuthority.UNKNOWN: 0.50,
}

AUTHORITY_HIERARCHY: List[SourceAuthority] = [
    SourceAuthority.UNKNOWN,
    SourceAuthority.GENERAL_REFERENCE,
    SourceAuthority.VERIFIED_REFERENCE,
    SourceAuthority.OFFICIAL_DOCUMENTATION,
    SourceAuthority.OFFICIAL_RESEARCH,
    SourceAuthority.OFFICIAL_GOVERNMENT,
]


def tokenize(text: str) -> List[str]:
    """Tokenize lowercase alphanumeric words with basic normalization."""
    words = re.findall(r"\b[a-zA-Z0-9_-]{2,}\b", text.lower())
    # Strip basic English stopwords
    stopwords = {
        "the", "and", "for", "with", "this", "that", "from", "are", "was", "were",
        "has", "have", "had", "been", "will", "would", "can", "could", "should",
        "about", "into", "through", "during", "before", "after", "above", "below",
    }
    return [w for w in words if w not in stopwords]


class BaseEvidenceStore(ABC):
    """Abstract interface for ORCA Evidence Storage and Indexing."""

    @abstractmethod
    def add_document(self, doc: EvidenceDocument) -> None:
        """Add and chunk a document into the store."""
        pass

    @abstractmethod
    def add_documents(self, docs: List[EvidenceDocument]) -> None:
        """Batch add documents."""
        pass

    @abstractmethod
    def get_document(self, doc_id: str) -> Optional[EvidenceDocument]:
        """Retrieve a document by ID."""
        pass

    @abstractmethod
    def get_chunk(self, chunk_id: str) -> Optional[EvidenceChunk]:
        """Retrieve a specific chunk by ID."""
        pass

    @abstractmethod
    def search(self, query: EvidenceQuery) -> List[EvidenceChunk]:
        """Search and rank chunks matching query criteria."""
        pass

    @abstractmethod
    def all_documents(self) -> List[EvidenceDocument]:
        """Retrieve all indexed documents."""
        pass

    @abstractmethod
    def count(self) -> int:
        """Total number of documents indexed."""
        pass


class InMemoryEvidenceStore(BaseEvidenceStore):
    """
    Deterministic In-Memory Evidence Store.
    Implements modified BM25/TF-IDF term frequency lexical scoring with
    authority weighting, tag matching, and metadata filtering.
    Requires ZERO external cloud dependencies or paid APIs.
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self._documents: Dict[str, EvidenceDocument] = {}
        self._chunks: Dict[str, EvidenceChunk] = {}
        self._chunk_tokens: Dict[str, List[str]] = {}
        self._doc_freqs: Dict[str, int] = {}
        self._total_chunks: int = 0
        self._avg_chunk_length: float = 0.0

    def add_document(self, doc: EvidenceDocument) -> None:
        """Ingest document, segment into chunks, and update lexical index."""
        self._documents[doc.id] = doc

        # Chunk content by sentences or paragraphs (approx 80-120 words per chunk)
        paragraphs = [p.strip() for p in doc.content.split("\n\n") if p.strip()]
        if not paragraphs:
            paragraphs = [doc.content.strip()]

        for idx, p in enumerate(paragraphs):
            chunk_id = f"{doc.id}#c{idx + 1}"
            chunk = EvidenceChunk(
                document_id=doc.id,
                chunk_id=chunk_id,
                text=p,
                title=doc.title,
                source=doc.source,
                publisher=doc.publisher,
                authority_level=doc.authority_level,
                evidence_type=doc.source_type,
                language=doc.language,
                reference=doc.reference,
                score=0.0,
                metadata={
                    "tags": doc.tags,
                    "published_at": doc.published_at,
                    "retrieved_at": doc.retrieved_at,
                },
            )
            self._chunks[chunk_id] = chunk

        self._rebuild_index()

    def add_documents(self, docs: List[EvidenceDocument]) -> None:
        """Batch ingest documents."""
        for d in docs:
            self.add_document(d)

    def get_document(self, doc_id: str) -> Optional[EvidenceDocument]:
        return self._documents.get(doc_id)

    def get_chunk(self, chunk_id: str) -> Optional[EvidenceChunk]:
        return self._chunks.get(chunk_id)

    def all_documents(self) -> List[EvidenceDocument]:
        return list(self._documents.values())

    def count(self) -> int:
        return len(self._documents)

    def _rebuild_index(self) -> None:
        """Update inverted document frequency index across chunks."""
        self._chunk_tokens.clear()
        self._doc_freqs.clear()
        self._total_chunks = len(self._chunks)
        if self._total_chunks == 0:
            self._avg_chunk_length = 0.0
            return

        total_tokens = 0
        for chunk_id, chunk in self._chunks.items():
            # Include title and tags in token stream with repetition for weighting
            combined_text = f"{chunk.title} {chunk.title} {' '.join(chunk.metadata.get('tags', []))} {chunk.text}"
            tokens = tokenize(combined_text)
            self._chunk_tokens[chunk_id] = tokens
            total_tokens += len(tokens)

            unique_tokens = set(tokens)
            for t in unique_tokens:
                self._doc_freqs[t] = self._doc_freqs.get(t, 0) + 1

        self._avg_chunk_length = total_tokens / self._total_chunks

    def search(self, query: EvidenceQuery) -> List[EvidenceChunk]:
        """
        Search indexed chunks using deterministic BM25 scoring combined with
        source authority multipliers and filter constraints.
        """
        if not self._chunks:
            return []

        query_tokens = tokenize(query.query)
        if not query_tokens:
            return []

        min_authority = query.filters.get("min_authority")
        allowed_types = query.filters.get("evidence_types")
        required_tags = query.filters.get("tags")

        candidates: List[EvidenceChunk] = []

        for chunk_id, chunk in self._chunks.items():
            # 1. Authority filtering
            if min_authority:
                try:
                    req_idx = AUTHORITY_HIERARCHY.index(SourceAuthority(min_authority))
                    chunk_idx = AUTHORITY_HIERARCHY.index(chunk.authority_level)
                    if chunk_idx < req_idx:
                        continue
                except ValueError:
                    pass

            # 2. Type filtering
            if allowed_types:
                if chunk.evidence_type.value not in allowed_types and chunk.evidence_type not in allowed_types:
                    continue

            # 3. Tag filtering
            if required_tags:
                chunk_tags: Set[str] = set(chunk.metadata.get("tags", []))
                if not any(rt in chunk_tags for rt in required_tags):
                    continue

            # 4. Compute BM25 Lexical Score
            tokens = self._chunk_tokens.get(chunk_id, [])
            if not tokens:
                continue

            score = 0.0
            doc_len = len(tokens)
            token_counts: Dict[str, int] = {}
            for t in tokens:
                token_counts[t] = token_counts.get(t, 0) + 1

            for qt in query_tokens:
                if qt in token_counts:
                    tf = token_counts[qt]
                    df = self._doc_freqs.get(qt, 1)
                    # Standard BM25 IDF formulation
                    idf = math.log(1.0 + (self._total_chunks - df + 0.5) / (df + 0.5))
                    numerator = tf * (self.k1 + 1.0)
                    denominator = tf + self.k1 * (1.0 - self.b + self.b * (doc_len / (self._avg_chunk_length or 1.0)))
                    score += idf * (numerator / denominator)

            if score > 0.0:
                # 5. Apply Authority Weight Multiplier
                weight = AUTHORITY_WEIGHTS.get(chunk.authority_level, 1.0)
                final_score = round(score * weight, 4)

                # Clone chunk with calculated score
                ranked_chunk = chunk.model_copy()
                ranked_chunk.score = final_score
                candidates.append(ranked_chunk)

        # Sort deterministically: score descending, then chunk_id ascending
        candidates.sort(key=lambda c: (-c.score, c.chunk_id))
        return candidates[: query.max_results]
