"""
ORCA Evidence & RAG Schemas — Phase 6
Defines contracts for contextual knowledge documents, chunks, queries,
source authority levels, evidence classification, citations, and retrieval results.

CRITICAL INVARIANT:
RAG evidence is contextual and regulatory; it NEVER substitutes or overrides live marine telemetry.
"""

from enum import Enum
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict


class SourceAuthority(str, Enum):
    """
    Authoritative trustworthiness level of an evidence document.
    Ensures that official statutory rules are distinguished from unverified references.
    """
    OFFICIAL_GOVERNMENT = "OFFICIAL_GOVERNMENT"        # Coast Guard, Ministry of Fisheries, INCOIS, IMD
    OFFICIAL_RESEARCH = "OFFICIAL_RESEARCH"            # Peer-reviewed oceanographic & marine biology institutes
    OFFICIAL_DOCUMENTATION = "OFFICIAL_DOCUMENTATION"  # Official data provider specifications & manuals
    VERIFIED_REFERENCE = "VERIFIED_REFERENCE"          # Curated, verified maritime textbooks and training manuals
    GENERAL_REFERENCE = "GENERAL_REFERENCE"            # General knowledge encyclopedic references
    UNKNOWN = "UNKNOWN"                                # Unverified external text (heavily discounted)


class EvidenceClassification(str, Enum):
    """Functional purpose and operational relevance of the evidence."""
    CONTEXTUAL = "CONTEXTUAL"                      # Background maritime and oceanographic knowledge
    OPERATIONAL_GUIDANCE = "OPERATIONAL_GUIDANCE"  # Seamanship protocols, vessel limits, distress actions
    REGULATORY = "REGULATORY"                      # Statutory fishing bans, territorial boundary rules
    TECHNICAL_REFERENCE = "TECHNICAL_REFERENCE"    # Remote sensing, sensor mechanics, SST/Chlorophyll science


class RetrievalStatus(str, Enum):
    """Deterministic status of an evidence retrieval query."""
    SUCCESS = "SUCCESS"          # Relevant evidence found and retrieved
    EMPTY = "EMPTY"              # Query yielded no relevant knowledge documents
    UNAVAILABLE = "UNAVAILABLE"  # Knowledge store is offline or deactivated
    ERROR = "ERROR"              # Retrieval failed due to processing error


class EvidenceDocument(BaseModel):
    """
    A single authoritative document in the ORCA marine knowledge base.
    """
    model_config = ConfigDict(extra="ignore")

    id: str = Field(..., description="Unique document identifier (e.g. 'doc_monsoon_ban_2024')")
    title: str = Field(..., description="Human-readable title of document")
    content: str = Field(..., description="Full text content of document")
    source: str = Field(..., description="Source name (e.g. 'Ministry of Fisheries Guidelines')")
    source_type: EvidenceClassification = Field(
        default=EvidenceClassification.CONTEXTUAL,
        description="Classification category of this document"
    )
    publisher: str = Field(..., description="Publishing body or organization")
    published_at: Optional[str] = Field(default=None, description="ISO timestamp or date of publication")
    retrieved_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO timestamp when document was ingested into ORCA"
    )
    authority_level: SourceAuthority = Field(
        default=SourceAuthority.VERIFIED_REFERENCE,
        description="Authoritative weight of the source"
    )
    language: str = Field(default="en", description="Primary language of original document (e.g. 'en')")
    tags: List[str] = Field(default_factory=list, description="Descriptive semantic tags")
    reference: Optional[str] = Field(default=None, description="Official URL, citation, or Gazette number")


class EvidenceChunk(BaseModel):
    """
    A discrete semantic chunk extracted from an EvidenceDocument for granular retrieval.
    """
    model_config = ConfigDict(extra="ignore")

    document_id: str = Field(..., description="Parent document identifier")
    chunk_id: str = Field(..., description="Unique chunk identifier (e.g. 'doc_monsoon_ban_2024#c1')")
    text: str = Field(..., description="Text segment of the chunk")
    title: str = Field(..., description="Document title")
    source: str = Field(..., description="Source name")
    publisher: str = Field(..., description="Publishing body")
    authority_level: SourceAuthority = Field(..., description="Authoritative level")
    evidence_type: EvidenceClassification = Field(..., description="Classification category")
    language: str = Field(default="en", description="Language of chunk")
    reference: Optional[str] = Field(default=None, description="Official citation link or reference")
    score: float = Field(default=0.0, ge=0.0, description="Relevance ranking score")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Auxiliary chunk metadata")


class EvidenceCitation(BaseModel):
    """
    Transparent citation surfaced alongside synthesized natural-language answers.
    Gives mariners direct provenance to regulations, manuals, and oceanographic science.
    """
    model_config = ConfigDict(extra="ignore")

    document_id: str = Field(..., description="Cited document identifier")
    title: str = Field(..., description="Document title")
    source: str = Field(..., description="Source name")
    publisher: str = Field(..., description="Publishing organization")
    authority_level: SourceAuthority = Field(..., description="Authority level")
    reference: Optional[str] = Field(default=None, description="Official reference citation or URL")
    retrieved_at: str = Field(..., description="Ingestion / verification timestamp")
    relevant_chunk: str = Field(..., description="Relevant text excerpt supporting the explanation")


class EvidenceQuery(BaseModel):
    """
    Structured retrieval request passed to the EvidenceRetriever.
    """
    model_config = ConfigDict(extra="ignore")

    query: str = Field(..., min_length=1, description="Natural-language question or search query")
    language: str = Field(default="en", description="Query language code ('en', 'hi', 'mr')")
    filters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Optional filters (e.g. {'min_authority': 'VERIFIED_REFERENCE', 'type': 'REGULATORY'})"
    )
    max_results: int = Field(default=3, ge=1, le=10, description="Maximum number of chunks to return")


class EvidenceResult(BaseModel):
    """
    Structured outcome of an evidence retrieval operation.
    """
    model_config = ConfigDict(extra="ignore")

    query: str = Field(..., description="Input query")
    chunks: List[EvidenceChunk] = Field(default_factory=list, description="Ranked relevant evidence chunks")
    source_count: int = Field(default=0, ge=0, description="Number of distinct source documents retrieved")
    retrieval_status: RetrievalStatus = Field(
        default=RetrievalStatus.EMPTY,
        description="Status: SUCCESS, EMPTY, UNAVAILABLE, or ERROR"
    )
    citations: List[EvidenceCitation] = Field(
        default_factory=list,
        description="Structured citations derived from retrieved chunks"
    )
    errors: List[str] = Field(default_factory=list, description="Retrieval errors encountered, if any")


class EvidenceContext(BaseModel):
    """
    Contextual knowledge container passed to the Reasoning Engine and Synthesizer.
    Complements live numerical telemetry without altering it.
    """
    model_config = ConfigDict(extra="ignore")

    query: str = Field(..., description="User query associated with this context")
    retrieved_evidence: List[EvidenceChunk] = Field(default_factory=list, description="Retrieved chunks")
    source_count: int = Field(default=0, ge=0, description="Count of unique sources")
    retrieval_status: RetrievalStatus = Field(default=RetrievalStatus.EMPTY, description="Retrieval status")
    uncertainties: List[str] = Field(default_factory=list, description="Surfaced knowledge caveats or gaps")
    citations: List[EvidenceCitation] = Field(default_factory=list, description="Formatted citations")
