"""
ORCA Phase 6 — Test Evidence Store
Verifies document ingestion, chunking, BM25 scoring, authority weighting, and filtering.
"""

import unittest
from evidence.schemas import (
    EvidenceDocument,
    EvidenceQuery,
    SourceAuthority,
    EvidenceClassification,
)
from evidence.store import InMemoryEvidenceStore
from evidence.corpus import SEED_EVIDENCE_DOCUMENTS


class TestEvidenceStore(unittest.TestCase):
    def setUp(self):
        self.store = InMemoryEvidenceStore()
        self.store.add_documents(SEED_EVIDENCE_DOCUMENTS)

    def test_store_initialization(self):
        """Verify all seed documents are indexed and segmented into chunks."""
        self.assertEqual(self.store.count(), len(SEED_EVIDENCE_DOCUMENTS))
        doc = self.store.get_document("doc_monsoon_fishing_ban")
        self.assertIsNotNone(doc)
        self.assertEqual(doc.authority_level, SourceAuthority.GENERAL_REFERENCE)

        chunk = self.store.get_chunk("doc_monsoon_fishing_ban#c1")
        self.assertIsNotNone(chunk)
        self.assertIn("West Coast", chunk.text)

    def test_deterministic_lexical_search(self):
        """Verify that relevant queries retrieve top matching chunks deterministically."""
        query = EvidenceQuery(query="monsoon fishing ban dates", max_results=3)
        results = self.store.search(query)

        self.assertGreater(len(results), 0)
        top_result = results[0]
        self.assertEqual(top_result.document_id, "doc_monsoon_fishing_ban")
        self.assertGreater(top_result.score, 0.0)

    def test_authority_weighting(self):
        """Verify that official government documents receive authority score boost."""
        custom_store = InMemoryEvidenceStore()

        # Add two documents with the exact same content, but different authorities
        doc_gov = EvidenceDocument(
            id="doc_gov",
            title="Lifejacket Regulation",
            content="Lifejackets are strictly mandatory for all coastal fishermen.",
            source="Coast Guard Notice",
            publisher="Coast Guard",
            authority_level=SourceAuthority.OFFICIAL_GOVERNMENT,
        )
        doc_unverified = EvidenceDocument(
            id="doc_unverified",
            title="Lifejacket Discussion",
            content="Lifejackets are strictly mandatory for all coastal fishermen.",
            source="Blog Post",
            publisher="Anonymous",
            authority_level=SourceAuthority.UNKNOWN,
        )

        custom_store.add_document(doc_unverified)
        custom_store.add_document(doc_gov)

        query = EvidenceQuery(query="Lifejackets mandatory", max_results=2)
        results = custom_store.search(query)

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].document_id, "doc_gov")
        self.assertGreater(results[0].score, results[1].score)

    def test_filter_by_tags_and_type(self):
        """Verify search filtering by tags and evidence classifications."""
        query = EvidenceQuery(
            query="coastal regulations",
            filters={"evidence_types": [EvidenceClassification.REGULATORY.value]},
            max_results=5,
        )
        results = self.store.search(query)

        for chunk in results:
            self.assertEqual(chunk.evidence_type, EvidenceClassification.REGULATORY)

    def test_empty_search_query(self):
        """Verify non-matching or irrelevant queries return empty results."""
        query = EvidenceQuery(query="xylophone quantum entanglement", max_results=5)
        results = self.store.search(query)
        self.assertEqual(len(results), 0)


if __name__ == "__main__":
    unittest.main()
