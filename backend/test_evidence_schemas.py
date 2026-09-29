"""
ORCA Phase 6 — Test Evidence Schemas
Verifies contract validation, enum behaviors, authority rankings, and serialization.
"""

import unittest
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


class TestEvidenceSchemas(unittest.TestCase):
    def test_enums(self):
        """Verify SourceAuthority, EvidenceClassification, and RetrievalStatus enums."""
        self.assertEqual(SourceAuthority.OFFICIAL_GOVERNMENT.value, "OFFICIAL_GOVERNMENT")
        self.assertEqual(SourceAuthority.OFFICIAL_RESEARCH.value, "OFFICIAL_RESEARCH")
        self.assertEqual(SourceAuthority.VERIFIED_REFERENCE.value, "VERIFIED_REFERENCE")
        self.assertEqual(SourceAuthority.UNKNOWN.value, "UNKNOWN")

        self.assertEqual(EvidenceClassification.REGULATORY.value, "REGULATORY")
        self.assertEqual(EvidenceClassification.OPERATIONAL_GUIDANCE.value, "OPERATIONAL_GUIDANCE")
        self.assertEqual(EvidenceClassification.TECHNICAL_REFERENCE.value, "TECHNICAL_REFERENCE")
        self.assertEqual(EvidenceClassification.CONTEXTUAL.value, "CONTEXTUAL")

        self.assertEqual(RetrievalStatus.SUCCESS.value, "SUCCESS")
        self.assertEqual(RetrievalStatus.EMPTY.value, "EMPTY")
        self.assertEqual(RetrievalStatus.UNAVAILABLE.value, "UNAVAILABLE")
        self.assertEqual(RetrievalStatus.ERROR.value, "ERROR")

    def test_evidence_document(self):
        """Verify EvidenceDocument creation, defaults, and serialization."""
        doc = EvidenceDocument(
            id="doc_test_1",
            title="Marine Safety Manual",
            content="Always inspect lifejackets and communication equipment before sailing.",
            source="Naval Safety Board",
            source_type=EvidenceClassification.OPERATIONAL_GUIDANCE,
            publisher="Maritime Authority",
            authority_level=SourceAuthority.OFFICIAL_GOVERNMENT,
            tags=["safety", "lifejackets"],
            reference="https://example.com/safety.pdf",
        )
        self.assertEqual(doc.id, "doc_test_1")
        self.assertEqual(doc.authority_level, SourceAuthority.OFFICIAL_GOVERNMENT)
        self.assertIn("safety", doc.tags)
        self.assertTrue(doc.retrieved_at)

        data = doc.model_dump()
        self.assertEqual(data["title"], "Marine Safety Manual")

    def test_evidence_chunk_and_citation(self):
        """Verify EvidenceChunk and EvidenceCitation creation."""
        chunk = EvidenceChunk(
            document_id="doc_test_1",
            chunk_id="doc_test_1#c1",
            text="Lifejacket protocol excerpt.",
            title="Marine Safety Manual",
            source="Naval Safety Board",
            publisher="Maritime Authority",
            authority_level=SourceAuthority.OFFICIAL_GOVERNMENT,
            evidence_type=EvidenceClassification.OPERATIONAL_GUIDANCE,
            score=2.85,
        )
        self.assertEqual(chunk.score, 2.85)

        citation = EvidenceCitation(
            document_id=chunk.document_id,
            title=chunk.title,
            source=chunk.source,
            publisher=chunk.publisher,
            authority_level=chunk.authority_level,
            reference="https://example.com/safety.pdf",
            retrieved_at="2024-01-01T00:00:00Z",
            relevant_chunk=chunk.text,
        )
        self.assertEqual(citation.publisher, "Maritime Authority")

    def test_query_and_result_schemas(self):
        """Verify EvidenceQuery, EvidenceResult, and EvidenceContext."""
        query = EvidenceQuery(query="monsoon fishing ban rules", max_results=5)
        self.assertEqual(query.max_results, 5)

        result = EvidenceResult(
            query=query.query,
            source_count=1,
            retrieval_status=RetrievalStatus.SUCCESS,
        )
        self.assertEqual(result.retrieval_status, RetrievalStatus.SUCCESS)

        ctx = EvidenceContext(
            query=query.query,
            retrieval_status=RetrievalStatus.EMPTY,
            uncertainties=["No documents found."],
        )
        self.assertEqual(len(ctx.uncertainties), 1)


if __name__ == "__main__":
    unittest.main()
