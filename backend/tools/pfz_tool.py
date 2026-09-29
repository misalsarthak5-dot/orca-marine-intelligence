"""
ORCA PFZ Tool
Thin adapter wrapping existing services.pfz_service.get_pfz_assessment.
Provides standardized ToolResult with official INCOIS GeoServer WFS provenance.
"""

from typing import Optional
from tools.base_tool import BaseTool, ToolResult
from core.schemas import AgentStatus, DataStatus
from services.pfz_service import get_pfz_assessment


class PFZTool(BaseTool):
    """
    Adapter for Potential Fishing Zones (PFZ) intelligence.
    Directly invokes services.pfz_service.get_pfz_assessment.
    """

    name: str = "pfz_tool"
    description: str = (
        "Retrieves official INCOIS Potential Fishing Zones (PFZ) advisories, "
        "including nearest landing centre vectors, distance, bearing, depth ranges, "
        "and real MultiLineString satellite SST/chlorophyll frontal line geometries."
    )

    async def execute(
        self,
        lat: float,
        lon: float,
        radius_km: float = 250.0,
        **kwargs,
    ) -> ToolResult:
        """
        Execute INCOIS PFZ assessment.

        Args:
            lat: Latitude (-90 to 90)
            lon: Longitude (-180 to 180)
            radius_km: Search radius in km (default 250.0)

        Returns:
            ToolResult containing PFZ assessment payload and grounded INCOIS provenance.
        """
        if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
            return self.create_error_result(
                error_message=f"Invalid coordinates: lat={lat}, lon={lon}",
                evidence=self.create_evidence(
                    source="INCOIS WebGIS GeoServer WFS",
                    source_type="ogc_wfs",
                    data_status=DataStatus.ERROR,
                    reference="https://www.incois.gov.in",
                ),
            )

        try:
            raw_data = await get_pfz_assessment(lat=lat, lon=lon, max_radius_km=radius_km)
        except Exception as e:
            return self.create_error_result(
                error_message=f"PFZ service call failed: {str(e)}",
                errors=[str(e)],
                evidence=self.create_evidence(
                    source="INCOIS WebGIS GeoServer WFS",
                    source_type="ogc_wfs",
                    data_status=DataStatus.ERROR,
                    reference="https://www.incois.gov.in",
                ),
            )

        advisory_meta = raw_data.get("advisory_metadata", {})
        reference_date = advisory_meta.get("reference_layer_date")

        evidence = self.create_evidence(
            source="INCOIS WebGIS GeoServer WFS",
            source_type="ogc_wfs",
            observed_at=reference_date,
            data_status=DataStatus.LIVE if raw_data.get("available") else DataStatus.UNAVAILABLE,
            reference="https://www.incois.gov.in/geoserver/PFZ_Automation/ows",
        )

        return ToolResult(
            tool=self.name,
            status=AgentStatus.SUCCESS if raw_data.get("available") else AgentStatus.PARTIAL,
            data=raw_data,
            evidence=evidence,
            errors=[],
            metadata={
                "source": "INCOIS",
                "total_advisories": raw_data.get("total_active_advisories_found", 0),
                "total_regional_lines": raw_data.get("total_regional_lines", 0),
                "total_nationwide_lines": raw_data.get("total_nationwide_lines", 0),
            },
        )
