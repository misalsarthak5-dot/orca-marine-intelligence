"""
ORCA Phase 6 — Test Evidence & RAG Integration
Verifies end-to-end integration across EvidenceService, OperationalReasoningEngine,
OrcaSynthesizer, and OrcaResponse contracts.
"""

import unittest
import asyncio
from core.schemas import AgentResult, AgentStatus, Evidence, DataStatus
from orchestration.schemas import PlannerRequest, ExecutionPlan, PlanStep, OrchestrationResult
from orchestration.synthesizer import OrcaSynthesizer
from reasoning.schemas import ReasoningContext
from reasoning.engine import OperationalReasoningEngine
from evidence.schemas import RetrievalStatus
from evidence.service import EvidenceService


class TestEvidenceIntegration(unittest.TestCase):
    def setUp(self):
        self.evidence_service = EvidenceService()
        self.reasoning_engine = OperationalReasoningEngine()
        self.synthesizer = OrcaSynthesizer(llm_client=None)

    def test_evidence_service_retrieve_context(self):
        """Verify EvidenceService returns a populated EvidenceContext with citations."""
        ctx = self.evidence_service.retrieve_context("What are the fishing ban rules?")
        self.assertEqual(ctx.retrieval_status, RetrievalStatus.SUCCESS)
        self.assertGreater(ctx.source_count, 0)
        self.assertGreater(len(ctx.citations), 0)
        self.assertIn("ban", ctx.citations[0].title.lower())

    def test_reasoning_preserves_evidence_context_without_altering_safety(self):
        """Verify ReasoningResult retains EvidenceContext while keeping safety deterministic."""
        ev_ctx = self.evidence_service.retrieve_context("What are safe wave limits for small boats?")

        agent_results = {
            "marine": AgentResult(
                agent="marine",
                status=AgentStatus.SUCCESS,
                data={
                    "current": {
                        "wave_height_m": 2.2,  # Rough wave state
                        "dominant_wave_period_s": 8.0,
                    }
                },
                evidence=Evidence(source="open-meteo-marine", source_type="api", data_status=DataStatus.LIVE),
            ),
            "weather": AgentResult(
                agent="weather",
                status=AgentStatus.SUCCESS,
                data={
                    "current": {
                        "wind_speed_knots": 22.0,  # High wind
                    }
                },
                evidence=Evidence(source="open-meteo-weather", source_type="api", data_status=DataStatus.LIVE),
            ),
            "hazard": AgentResult(
                agent="hazard",
                status=AgentStatus.SUCCESS,
                data={
                    "hazard_state": "CAUTION",
                    "alerts": [{"headline": "Rough Sea Alert"}],
                },
                evidence=Evidence(source="incois-hazard", source_type="api", data_status=DataStatus.LIVE),
            ),
        }

        plan = ExecutionPlan(
            plan_id="plan_test_rag_safety",
            intent="marine_safety",
            reasoning_summary="Evaluate marine safety conditions",
            user_query="Are conditions safe for small craft?",
            steps=[PlanStep(step_id="step_1", agent="marine", purpose="marine conditions")],
        )

        reasoning_ctx = ReasoningContext(
            query="Are conditions safe for small craft?",
            intent="marine_safety",
            agent_results=agent_results,
            evidence=[r.evidence for r in agent_results.values() if r.evidence],
            plan=plan,
            evidence_context=ev_ctx,
        )

        res = asyncio.run(self.reasoning_engine.reason(reasoning_ctx))

        # Check that evidence_context is preserved
        self.assertIsNotNone(res.evidence_context)
        self.assertEqual(res.evidence_context.retrieval_status, RetrievalStatus.SUCCESS)

        # Check that RAG didn't override the deterministic high waves / wind impact
        wave_factors = [f for f in res.decision_factors if "wave" in f.factor.lower()]
        self.assertTrue(len(wave_factors) > 0)
        self.assertEqual(wave_factors[0].value, "2.20 m")

        # Live wave height 2.2m should cause cautionary/restrictive impact, not overridden by text
        self.assertTrue(any(f.factor == "Marine Hazard State" and f.value == "CAUTION" for f in res.decision_factors))

    def test_stale_and_unavailable_data_remains_unaltered(self):
        """Verify RAG documents cannot turn UNAVAILABLE or STALE data into LIVE data."""
        # Querying chlorophyll concepts
        ev_ctx = self.evidence_service.retrieve_context("What is chlorophyll-a?")

        agent_results = {
            "chlorophyll": AgentResult(
                agent="chlorophyll",
                status=AgentStatus.SUCCESS,
                data={"available": False, "reason": "No satellite swath"},
                evidence=Evidence(source="nasa-modis", source_type="satellite", data_status=DataStatus.UNAVAILABLE),
            )
        }

        plan = ExecutionPlan(
            plan_id="plan_test_rag_chl",
            intent="chlorophyll_analysis",
            reasoning_summary="Analyze chlorophyll data",
            user_query="Show chlorophyll data",
            steps=[PlanStep(step_id="step_1", agent="chlorophyll", purpose="chlorophyll data")],
        )

        reasoning_ctx = ReasoningContext(
            query="Show chlorophyll data",
            intent="chlorophyll_analysis",
            agent_results=agent_results,
            evidence=[agent_results["chlorophyll"].evidence],
            plan=plan,
            evidence_context=ev_ctx,
        )

        res = asyncio.run(self.reasoning_engine.reason(reasoning_ctx))

        # Chlorophyll data status in reasoning must remain UNAVAILABLE in uncertainties
        uncertainties_str = " ".join(res.uncertainties)
        self.assertIn("unavailable", uncertainties_str.lower())

    def test_synthesizer_integrates_citations_cleanly(self):
        """Verify synthesizer incorporates citations into OrcaResponse and markdown."""
        ev_ctx = self.evidence_service.retrieve_context("VHF distress communication channel")

        agent_results = {
            "marine": AgentResult(
                agent="marine",
                status=AgentStatus.SUCCESS,
                data={"current": {"wave_height_m": 0.7}},
                evidence=Evidence(source="open-meteo-marine", source_type="api", data_status=DataStatus.LIVE),
            )
        }

        plan = ExecutionPlan(
            plan_id="plan_test_synth_rag",
            intent="emergency_guidance",
            reasoning_summary="Provide distress emergency guidance",
            user_query="How do I call distress on VHF?",
            steps=[PlanStep(step_id="step_1", agent="marine", purpose="marine conditions")],
        )

        orch_result = OrchestrationResult(
            query="How do I call distress on VHF?",
            plan=plan,
            agent_results=agent_results,
            evidence=[agent_results["marine"].evidence],
        )

        req = PlannerRequest(query="How do I call distress on VHF?", latitude=18.92, longitude=72.83)

        response = asyncio.run(self.synthesizer.synthesize(
            orch_result, req, evidence_context=ev_ctx
        ))

        # 1. OrcaResponse carries citations list
        self.assertEqual(len(response.citations), len(ev_ctx.citations))
        self.assertGreater(len(response.citations), 0)

        # 2. Synthesized answer contains References & Guidance block
        self.assertIn("Authoritative References & Guidance", response.answer)
        self.assertIn("VHF", response.answer)

    def test_synthesizer_empty_citations_when_retrieval_empty(self):
        """Verify that when no RAG documents match, no citations are fabricated."""
        ev_ctx = self.evidence_service.retrieve_context("xylophone medieval castle architecture")
        self.assertEqual(ev_ctx.retrieval_status, RetrievalStatus.EMPTY)

        plan = ExecutionPlan(
            plan_id="plan_empty_rag",
            intent="general",
            reasoning_summary="General query",
            user_query="xylophone",
            steps=[PlanStep(step_id="step_1", agent="weather", purpose="weather conditions")],
        )
        orch_result = OrchestrationResult(
            query="xylophone medieval castle architecture",
            plan=plan,
            agent_results={},
            evidence=[],
        )
        req = PlannerRequest(query="xylophone medieval castle architecture", latitude=19.0, longitude=72.8)

        response = asyncio.run(self.synthesizer.synthesize(orch_result, req, evidence_context=ev_ctx))

        self.assertEqual(len(response.citations), 0)
        self.assertNotIn("Authoritative References & Guidance", response.answer)


if __name__ == "__main__":
    unittest.main()
