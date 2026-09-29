"""
ORCA Base Agent Interface
Standardized interface for all specialized domain agents in ORCA.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from core.schemas import AgentRequest, AgentResult, AgentStatus, Evidence, DataStatus


class BaseAgent(ABC):
    """
    Abstract base class for all ORCA domain agents.
    Enforces the standardized contract: execute(AgentRequest) -> AgentResult.
    """

    name: str = "base_agent"
    description: str = "Base agent interface for ORCA"

    @abstractmethod
    async def execute(self, request: AgentRequest) -> AgentResult:
        """
        Execute domain-specific reasoning or data retrieval.

        Args:
            request: Standardized AgentRequest with coordinates, context, and query.

        Returns:
            Standardized AgentResult with status, data, evidence, and confidence.
        """
        pass

    def create_evidence(
        self,
        source: str,
        source_type: str,
        observed_at: Optional[str] = None,
        data_status: DataStatus = DataStatus.LIVE,
        reference: Optional[str] = None,
    ) -> Evidence:
        """Helper to create standardized grounded evidence records."""
        return Evidence(
            source=source,
            source_type=source_type,
            retrieved_at=datetime.now(timezone.utc).isoformat(),
            observed_at=observed_at,
            data_status=data_status,
            reference=reference,
        )

    def create_error_result(
        self,
        error_message: str,
        errors: Optional[List[str]] = None,
        evidence: Optional[Evidence] = None,
    ) -> AgentResult:
        """Helper to create a standardized failed AgentResult without crashing."""
        all_errors = list(errors or [])
        if error_message not in all_errors:
            all_errors.append(error_message)

        return AgentResult(
            agent=self.name,
            status=AgentStatus.FAILED,
            data=None,
            evidence=evidence,
            confidence=0.0,
            message=error_message,
            errors=all_errors,
        )
