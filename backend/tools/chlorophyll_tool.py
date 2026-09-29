"""
ORCA Chlorophyll Tool
Thin adapter wrapping existing services.chlorophyll_service.get_chlorophyll_data.
Provides standardized ToolResult with NASA Ocean Color / INCOIS provenance.
Preserves LIVE / UNAVAILABLE / CACHED / STALE states honestly without fabricating data.
"""

from typing import Optional, Dict, Any
from tools.base_tool import BaseTool, ToolResult
from core.schemas import AgentStatus, DataStatus, Evidence
from services.chlorophyll_service import get_chlorophyll_data


class ChlorophyllTool(BaseTool):
    """
    Adapter for satellite chlorophyll-a ocean color data.
    Directly invokes services.chlorophyll_service.get_chlorophyll_data.
    """

    name: str = "chlorophyll_tool"
    description: str = (
        "Retrieves satellite ocean-color chlorophyll-a concentration "
        "or transparent data-readiness status from NASA Ocean Color / MODIS-Aqua."
    )

    async def execute(self, lat: float, lon: float, **kwargs) -> ToolResult:
        """
        Execute chlorophyll telemetry retrieval.

        Args:
            lat: Latitude (-90 to 90)
            lon: Longitude (-180 to 180)

        Returns:
            ToolResult containing raw chlorophyll dictionary and Evidence grounding.
        """
        if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
            return self.create_error_result(
                error_message=f"Invalid coordinates: lat={lat}, lon={lon}",
                evidence=self.create_evidence(
                    source="NASA Ocean Color / MODIS-Aqua",
                    source_type="satellite",
                    data_status=DataStatus.ERROR,
                    reference="https://oceancolor.gsfc.nasa.gov",
                ),
            )

        try:
            raw_data = await get_chlorophyll_data(lat=lat, lon=lon)
        except Exception as e:
            return self.create_error_result(
                error_message=f"Chlorophyll service call failed: {str(e)}",
                errors=[str(e)],
                evidence=self.create_evidence(
                    source="NASA Ocean Color / MODIS-Aqua",
                    source_type="satellite",
                    data_status=DataStatus.ERROR,
                    reference="https://oceancolor.gsfc.nasa.gov",
                ),
            )

        # Resolve DataStatus honestly without converting UNAVAILABLE/STALE
        data_status: DataStatus
        if "data_status" in raw_data:
            ds = raw_data["data_status"]
            if isinstance(ds, DataStatus):
                data_status = ds
            elif isinstance(ds, str) and ds in DataStatus.__members__:
                data_status = DataStatus[ds]
            elif raw_data.get("available"):
                data_status = DataStatus.LIVE
            else:
                data_status = DataStatus.UNAVAILABLE
        elif raw_data.get("available"):
            data_status = DataStatus.LIVE
        else:
            data_status = DataStatus.UNAVAILABLE

        observed_at = raw_data.get("timestamp")
        source = raw_data.get("source", "NASA Ocean Color / MODIS-Aqua")
        provider = raw_data.get("provider", "NASA Earthdata / OB.DAAC")

        evidence = self.create_evidence(
            source=source,
            source_type="satellite",
            observed_at=observed_at,
            data_status=data_status,
            reference="https://oceancolor.gsfc.nasa.gov",
        )

        status = AgentStatus.SUCCESS if raw_data.get("available") else AgentStatus.PARTIAL

        confidence = (
            raw_data.get("confidence")
            if "confidence" in raw_data
            else (1.0 if raw_data.get("value") is not None else (0.8 if raw_data.get("available") else 0.5))
        )

        metadata = {
            "source": source,
            "provider": provider,
            "chlorophyll_status": raw_data.get("status"),
            "confidence": confidence,
        }

        return ToolResult(
            tool=self.name,
            status=status,
            data=raw_data,
            evidence=evidence,
            errors=[],
            metadata=metadata,
        )
