"""
ORCA Base Tool Interface
Standardized interface for domain tools adapting existing backend services.
Preserves real service data, provenance grounding, and status without fabrication.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict

from core.schemas import Evidence, DataStatus, AgentStatus


class ToolResult(BaseModel):
    """
    Standardized result contract returned by all ORCA domain tools.
    Encapsulates service payload, grounding evidence, status, and error details.
    """
    model_config = ConfigDict(extra="ignore")

    tool: str = Field(..., description="Unique name of the tool (e.g., 'weather_tool')")
    status: AgentStatus = Field(..., description="Execution status: SUCCESS, PARTIAL, or FAILED")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Actual data returned by underlying service")
    evidence: Optional[Evidence] = Field(default=None, description="Provenance and grounding metadata")
    errors: List[str] = Field(default_factory=list, description="Error messages encountered during execution")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Operational metadata (e.g. execution duration, cache hit)")


class BaseTool(ABC):
    """
    Abstract base class for all ORCA tools.
    Enforces standardized execution and provenance preservation.
    """

    name: str = "base_tool"
    description: str = "Base tool interface for ORCA services"

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """
        Execute the tool by calling the underlying existing service.

        Returns:
            Standardized ToolResult containing the service response and evidence.
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
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ToolResult:
        """Helper to create a failed ToolResult gracefully without unhandled exceptions."""
        all_errors = list(errors or [])
        if error_message not in all_errors:
            all_errors.append(error_message)

        return ToolResult(
            tool=self.name,
            status=AgentStatus.FAILED,
            data=None,
            evidence=evidence,
            errors=all_errors,
            metadata=metadata or {},
        )
