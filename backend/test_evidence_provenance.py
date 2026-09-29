"""
ORCA Phase 6 — Test Evidence Provenance & Telemetry Isolation
Verifies strict separation between RAG contextual evidence and live marine telemetry.
"""

import unittest
from core.schemas import AgentResult, AgentStatus, Evidence, DataStatus
from evidence.schemas import (
    EvidenceResult,
    EvidenceCitation,
    SourceAuthority,
    RetrievalStatus,
)
from evidence.provenance import verify_telemetry_isolation, format_citations_block


class TestEvidenceProvenance(unittest.TestCase):
    def test_clean_telemetry_isolation(self):
        """Verify normal numerical agent results pass isolation audit."""
        agent_results = {
            "marine": AgentResult(
                agent="marine",
                status=AgentStatus.SUCCESS,
                data={
                    "current": {
                        "wave_height_m": 0.82,
                        "dominant_wave_period_s": 7.4,
                    }
                },
                evidence=Evidence(
                    source="open-meteo-marine",
                    source_type="api",
                    data_status=DataStatus.LIVE,
                ),
            ),
            "weather": AgentResult(
                agent="weather",
                status=AgentStatus.SUCCESS,
                data={
                    "current": {
                        "wind_speed_knots": 8.5,
                    }
                },
                evidence=Evidence(
                    source="open-meteo-weather",
                    source_type="api",
                    data_status=DataStatus.LIVE,
                ),
            ),
        }

        ev_result = EvidenceResult(
            query="wave height",
            retrieval_status=RetrievalStatus.SUCCESS,
        )

        is_isolated = verify_telemetry_isolation(ev_result, agent_results)
        self.assertTrue(is_isolated)

    def test_telemetry_pollution_detected(self):
        """Verify that injecting RAG text into numerical telemetry triggers an immediate exception."""
        polluted_results = {
            "marine": AgentResult(
                agent="marine",
                status=AgentStatus.SUCCESS,
                data={
                    "wave_height": "According to a RAG document, wave height is 0.9 m",
                },
                evidence=Evidence(
                    source="open-meteo-marine",
                    source_type="api",
                    data_status=DataStatus.LIVE,
                ),
            ),
        }

        ev_result = EvidenceResult(query="test", retrieval_status=RetrievalStatus.SUCCESS)
        with self.assertRaises(ValueError) as ctx:
            verify_telemetry_isolation(ev_result, polluted_results)
        self.assertIn("Telemetry pollution detected", str(ctx.exception))

    def test_format_citations_block(self):
        """Verify citation block generation for natural-language markdown."""
        citations = [
            EvidenceCitation(
                document_id="doc_monsoon_fishing_ban",
                title="Uniform Monsoon Fishing Ban Guidelines",
                source="Maritime Fisheries Conservation",
                publisher="Ministry of Fisheries",
                authority_level=SourceAuthority.OFFICIAL_GOVERNMENT,
                reference="http://dof.gov.in/ban",
                retrieved_at="2024-01-01T00:00:00Z",
                relevant_chunk="Monsoon ban spans 61 days on the West Coast.",
            )
        ]

        markdown = format_citations_block(citations)
        self.assertIn("Authoritative References & Guidance", markdown)
        self.assertIn("Uniform Monsoon Fishing Ban Guidelines", markdown)
        self.assertIn("Ministry of Fisheries", markdown)
        self.assertIn("http://dof.gov.in/ban", markdown)

    def test_empty_citations_block(self):
        """Verify empty citation list returns empty string without fabricating text."""
        markdown = format_citations_block([])
        self.assertEqual(markdown, "")


if __name__ == "__main__":
    unittest.main()
