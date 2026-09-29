"""
ORCA Core Schemas — Foundation & Contract Layer
Defines standardized interfaces, status enums, evidence records, and agent contracts.
"""

from enum import Enum
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict


class DataStatus(str, Enum):
    """Authoritative operational state of underlying telemetry or data source."""
    LIVE = "LIVE"
    CACHED = "CACHED"
    STALE = "STALE"
    UNAVAILABLE = "UNAVAILABLE"
    ERROR = "ERROR"


class AgentStatus(str, Enum):
    """Execution status returned by an ORCA agent."""
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class Evidence(BaseModel):
    """
    Provenance and grounding metadata for any observation or calculation.
    Ensures complete transparency without fabricated telemetry.
    """
    model_config = ConfigDict(extra="ignore")

    source: str = Field(..., description="Name of the authoritative upstream source (e.g., 'Open-Meteo', 'INCOIS GeoServer')")
    source_type: str = Field(..., description="Data ingestion type: 'api', 'ogc_wfs', 'satellite', 'rule_engine', 'cache'")
    retrieved_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 timestamp when the data was retrieved by ORCA"
    )
    observed_at: Optional[str] = Field(
        default=None,
        description="ISO 8601 timestamp when the underlying measurement was taken or model-simulated"
    )
    data_status: DataStatus = Field(
        default=DataStatus.LIVE,
        description="Freshness and viability status of the telemetry"
    )
    reference: Optional[str] = Field(
        default=None,
        description="URL, WFS layer identifier, citation, or reference documentation"
    )


class AgentRequest(BaseModel):
    """
    Standardized request contract passed to all ORCA domain agents.
    Provides spatial coordinates, routing endpoints, temporal context, and user intent.
    """
    model_config = ConfigDict(extra="ignore")

    query: Optional[str] = Field(default=None, description="Raw user query if invoked during conversational reasoning")
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Target origin latitude in decimal degrees")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Target origin longitude in decimal degrees")
    destination_latitude: Optional[float] = Field(default=None, ge=-90.0, le=90.0, description="Target destination latitude")
    destination_longitude: Optional[float] = Field(default=None, ge=-180.0, le=180.0, description="Target destination longitude")
    timestamp: Optional[str] = Field(default=None, description="Target observation or forecast time window (e.g., 'now', 'tomorrow_morning')")
    context: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary conversational or pipeline state")


class AgentResult(BaseModel):
    """
    Standardized result contract returned by all ORCA domain agents.
    Carries domain-specific data, evidence provenance, confidence score, and error details.
    """
    model_config = ConfigDict(extra="ignore")

    agent: str = Field(..., description="Unique identifier of the agent providing this result (e.g., 'weather_agent')")
    status: AgentStatus = Field(..., description="Execution status: SUCCESS, PARTIAL, or FAILED")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Domain payload produced by the agent")
    evidence: Optional[Evidence] = Field(default=None, description="Grounded provenance metadata for this agent result")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")
    message: Optional[str] = Field(default=None, description="Human-readable summary or explanation of the agent's outcome")
    errors: List[str] = Field(default_factory=list, description="List of error messages if agent encountered issues")
