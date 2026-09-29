"""
ORCA Evidence Provenance & Telemetry Isolation — Phase 6
Enforces strict architectural boundaries between RAG contextual evidence and
deterministic live marine telemetry.
"""

from typing import Dict, Any, List
from evidence.schemas import EvidenceResult, EvidenceCitation


def verify_telemetry_isolation(
    evidence_result: EvidenceResult,
    agent_results: Dict[str, Any],
) -> bool:
    """
    Enforces the critical architectural rule:
    RAG evidence MUST NOT replace, mutate, or fabricate live operational data.

    Returns True if telemetry remains strictly unpolluted by RAG text.
    Raises ValueError if live agent telemetry is found to originate from RAG text.
    """
    if not agent_results:
        return True

    # Check for forbidden substitution patterns
    for agent_name, agent_res in agent_results.items():
        # AgentResult should have its own tool-grounded evidence
        data = getattr(agent_res, "data", None)
        if isinstance(data, dict):
            # Verify telemetry fields are NOT RAG strings or citations
            for key in ["wave_height", "wind_speed", "sst", "chlorophyll", "risk_score"]:
                if key in data and isinstance(data[key], str):
                    val = data[key].lower()
                    if "according to" in val or "rag document" in val or "gazette" in val:
                        raise ValueError(
                            f"Telemetry pollution detected: {agent_name}.data[{key}] contains RAG text '{data[key]}'"
                        )

    return True


def format_citations_block(citations: List[EvidenceCitation]) -> str:
    """
    Format citations into a transparent reference block for synthesized natural-language explanations.
    """
    if not citations:
        return ""

    lines: List[str] = ["\n\n**Authoritative References & Guidance:**"]
    for idx, c in enumerate(citations, 1):
        ref_text = f" — [{c.reference}]" if c.reference else ""
        lines.append(
            f"{idx}. **{c.title}** ({c.publisher}, Authority: `{c.authority_level.value}`){ref_text}\n"
            f"   *Excerpt:* \"{c.relevant_chunk}\""
        )

    return "\n".join(lines)
