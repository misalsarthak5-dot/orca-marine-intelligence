"""
ORCA Evidence Retriever — Phase 6
Coordinates structured document retrieval, multilingual query expansion (EN/HI/MR),
prompt-injection defense on retrieved text, and citation formatting.
"""

import re
from typing import Dict, List, Optional, Set
from evidence.schemas import (
    EvidenceQuery,
    EvidenceResult,
    EvidenceChunk,
    EvidenceCitation,
    RetrievalStatus,
    SourceAuthority,
)
from evidence.store import BaseEvidenceStore

# Cross-lingual term mapping to enable Hindi and Marathi queries to retrieve authoritative English reference corpus
MULTILINGUAL_CONCEPT_MAP: Dict[str, List[str]] = {
    # Weather & Ocean Conditions
    "मौसम": ["weather", "meteorological", "wind", "monsoon"],
    "हवामान": ["weather", "meteorological", "wind", "monsoon"],
    "लहर": ["wave", "swell", "sea", "rough"],
    "तरंग": ["wave", "swell", "sea"],
    "लाटा": ["wave", "swell", "sea"],
    "लाट": ["wave", "swell", "sea"],
    "वारा": ["wind", "gust", "breeze"],
    "हवा": ["wind", "gust", "weather"],
    "समुद्र": ["sea", "ocean", "marine", "coastal"],
    "किनारा": ["coastal", "shore", "harbor"],
    "तट": ["coastal", "shore", "harbor"],

    # Fishing & PFZ
    "मछली": ["fishing", "fish", "fishery", "pelagic"],
    "मत्स्य": ["fishing", "fish", "fishery", "pelagic", "pfz"],
    "मासेमारी": ["fishing", "fish", "fishery", "pelagic", "pfz"],
    "मासे": ["fish", "fishing", "pelagic"],
    "शिकार": ["fishing", "catch"],
    "झोन": ["zone", "pfz", "area"],
    "क्षेत्र": ["zone", "area", "boundary", "eez"],

    # Safety & Emergency
    "सुरक्षा": ["safety", "vessel_limits", "seamanship", "safe"],
    "सुरक्षित": ["safe", "safety", "vessel_limits"],
    "आपातकाल": ["emergency", "distress", "vhf16", "mayday", "rescue"],
    "संकट": ["emergency", "distress", "vhf16", "mayday", "rescue"],
    "मदत": ["rescue", "sar", "assistance", "emergency"],
    "मदद": ["rescue", "sar", "assistance", "emergency"],
    "जीवनरक्षक": ["lifejacket", "pfd", "safety"],

    # Regulations & Bans
    "प्रतिबंध": ["ban", "prohibition", "restriction", "regulation"],
    "बंदी": ["ban", "monsoon_ban", "prohibition", "conservation"],
    "नियम": ["regulation", "rules", "compliance", "territorial_waters"],
    "कायदे": ["regulation", "law", "compliance"],
    "सीमा": ["boundary", "imbl", "geofence", "territorial_waters"],
    "बोटी": ["boat", "vessel", "craft"],
    "नाव": ["boat", "canoe", "craft"],
    "जहाज": ["vessel", "trawler", "ship"],
}

# Prompt injection signatures to neutralize in retrieved or query text
INJECTION_PATTERNS = re.compile(
    r"(ignore\s+(all\s+)?previous\s+instructions|system\s*:|developer\s+mode|"
    r"__import__|eval\(|exec\(|os\.system|subprocess|<script|javascript:|drop\s+table)",
    re.IGNORECASE,
)


def sanitize_untrusted_text(text: str) -> str:
    """
    Sanitize untrusted text retrieved from documents or external inputs.
    Replaces executable tokens and prompt injection directives with passive placeholders.
    """
    if not text:
        return ""
    # Strip script tags
    sanitized = re.sub(r"<\s*script[^>]*>.*?<\s*/\s*script\s*>", "[SCRIPTA_REMOVED]", text, flags=re.DOTALL | re.IGNORECASE)
    # Neutralize prompt injection directives
    sanitized = INJECTION_PATTERNS.sub("[DIRECTIVE_NEUTRALIZED]", sanitized)
    return sanitized.strip()


class EvidenceRetriever:
    """
    High-level Evidence Retrieval Engine.
    Executes multilingual query expansion, queries the evidence store, applies
    prompt injection sanitization, and produces structured citations.
    """

    def __init__(self, store: Optional[BaseEvidenceStore] = None):
        self.store = store
        self.is_active = True

    def set_store(self, store: BaseEvidenceStore) -> None:
        self.store = store

    def retrieve(self, query: EvidenceQuery) -> EvidenceResult:
        """
        Execute deterministic evidence retrieval for an EvidenceQuery.
        """
        if not self.is_active or self.store is None:
            return EvidenceResult(
                query=query.query,
                chunks=[],
                source_count=0,
                retrieval_status=RetrievalStatus.UNAVAILABLE,
                citations=[],
                errors=["Evidence store is unavailable or not configured."],
            )

        # 1. Sanitize incoming query text
        clean_query_str = sanitize_untrusted_text(query.query)
        if not clean_query_str:
            return EvidenceResult(
                query=query.query,
                chunks=[],
                source_count=0,
                retrieval_status=RetrievalStatus.EMPTY,
                citations=[],
                errors=[],
            )

        # 2. Multilingual query expansion
        expanded_query_str = self._expand_multilingual_query(clean_query_str)
        effective_query = query.model_copy(update={"query": expanded_query_str})

        try:
            # 3. Search store
            chunks = self.store.search(effective_query)

            if not chunks:
                return EvidenceResult(
                    query=query.query,
                    chunks=[],
                    source_count=0,
                    retrieval_status=RetrievalStatus.EMPTY,
                    citations=[],
                    errors=[],
                )

            # 4. Prompt injection defense on retrieved chunks
            sanitized_chunks: List[EvidenceChunk] = []
            distinct_docs: Set[str] = set()

            for chunk in chunks:
                sanitized_text = sanitize_untrusted_text(chunk.text)
                was_modified = sanitized_text != chunk.text

                safe_chunk = chunk.model_copy(
                    update={
                        "text": sanitized_text,
                        "metadata": {
                            **chunk.metadata,
                            "sanitized": was_modified,
                        },
                    }
                )
                sanitized_chunks.append(safe_chunk)
                distinct_docs.add(chunk.document_id)

            # 5. Build structured citations
            citations: List[EvidenceCitation] = []
            for chunk in sanitized_chunks:
                citation = EvidenceCitation(
                    document_id=chunk.document_id,
                    title=chunk.title,
                    source=chunk.source,
                    publisher=chunk.publisher,
                    authority_level=chunk.authority_level,
                    reference=chunk.reference,
                    retrieved_at=chunk.metadata.get("retrieved_at", "2024-01-01T00:00:00Z"),
                    relevant_chunk=chunk.text[:300] + ("..." if len(chunk.text) > 300 else ""),
                )
                citations.append(citation)

            return EvidenceResult(
                query=query.query,
                chunks=sanitized_chunks,
                source_count=len(distinct_docs),
                retrieval_status=RetrievalStatus.SUCCESS,
                citations=citations,
                errors=[],
            )

        except Exception as e:
            return EvidenceResult(
                query=query.query,
                chunks=[],
                source_count=0,
                retrieval_status=RetrievalStatus.ERROR,
                citations=[],
                errors=[f"Evidence retrieval error: {str(e)}"],
            )

    def _expand_multilingual_query(self, text: str) -> str:
        """
        Detect Hindi or Marathi terms and append their canonical English maritime concepts.
        Preserves original tokens while enhancing lexical recall against the English reference corpus.
        """
        expanded_tokens: List[str] = [text]
        lower_text = text.lower()

        for vernacular_term, english_equivalents in MULTILINGUAL_CONCEPT_MAP.items():
            if vernacular_term in lower_text:
                expanded_tokens.extend(english_equivalents)

        return " ".join(expanded_tokens)
