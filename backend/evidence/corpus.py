"""
ORCA Marine Knowledge Corpus — Phase 6 Seed Reference Base
Contains curated maritime safety, oceanographic science, and coastal navigation reference documents.

CRITICAL ARCHITECTURAL POLICY:
- All documents strictly reflect demonstrable provenance: general reference notes are labeled GENERAL_REFERENCE.
- Only verified documentation with genuine, accessible technical sources is labeled VERIFIED_REFERENCE.
- No synthetic publishers or placeholder URLs are represented as official government or research bodies.
- Contextual reference material NEVER substitutes or overrides live numerical marine telemetry.
"""

from typing import List
from evidence.schemas import EvidenceDocument, SourceAuthority, EvidenceClassification


SEED_EVIDENCE_DOCUMENTS: List[EvidenceDocument] = [
    EvidenceDocument(
        id="doc_safety_vessel_thresholds",
        title="Coastal Fishing Vessel Operational Wave & Wind Guidelines",
        source="Maritime Seamanship Reference Notes",
        source_type=EvidenceClassification.OPERATIONAL_GUIDANCE,
        publisher="Public Maritime Safety Reference",
        published_at=None,
        retrieved_at="2024-01-15T00:00:00Z",
        authority_level=SourceAuthority.GENERAL_REFERENCE,
        language="en",
        tags=["safety", "vessel_limits", "wind", "wave", "seamanship", "guidance"],
        reference=None,
        content=(
            "Operational safety at sea depends fundamentally on vessel class, hull design, and prevailing meteorological "
            "and oceanographic conditions. In general coastal seamanship practice, traditional non-motorized artisanal canoes "
            "and catamarans (kattumarams) typically operate within significant wave heights below 0.8 meters and wind speeds "
            "under 12 knots (Beaufort Force 3). For motorized outboard fiber-reinforced plastic (FRP) craft (8–10 meters in length), "
            "sea conditions are commonly considered challenging when wave heights exceed 1.5 meters or wind speeds exceed 18 knots "
            "(Beaufort Force 5), particularly when short wave periods (< 5 seconds) generate steep chop. Larger mechanized fishing "
            "vessels (12–25 meters) can typically handle higher sea states, though operations require increased vigilance when wave "
            "heights exceed 2.5 meters or wind gusts exceed 25 knots. Standard seamanship guidelines advise wearing life jackets (PFDs) "
            "during bar-crossings, harbor transit, and night operations, and maintaining a listening watch on VHF Marine Channel 16. "
            "These figures represent general seamanship guidelines rather than statutory vessel limits."
        ),
    ),
    EvidenceDocument(
        id="doc_pfz_oceanography",
        title="Understanding Potential Fishing Zones (PFZ) & Thermal-Chlorophyll Fronts",
        source="Ocean Remote Sensing Educational Reference",
        source_type=EvidenceClassification.TECHNICAL_REFERENCE,
        publisher="Public Oceanographic Science Reference",
        published_at=None,
        retrieved_at="2023-11-20T00:00:00Z",
        authority_level=SourceAuthority.GENERAL_REFERENCE,
        language="en",
        tags=["pfz", "oceanography", "sst", "chlorophyll", "fishery", "remote_sensing"],
        reference=None,
        content=(
            "Potential Fishing Zone (PFZ) advisories identify ocean surface features where pelagic fish species, such as "
            "sardines, mackerel, and tuna, are prone to aggregate. These patterns are typically identified by analyzing Sea "
            "Surface Temperature (SST) gradients from satellite thermal infrared sensors and ocean color chlorophyll-a fronts "
            "from optical sensors. Thermal fronts and chlorophyll gradients mark areas of coastal upwelling and eddy circulation, "
            "where nutrient-rich cooler waters ascend toward the surface, supporting phytoplankton growth. Zooplankton feeds on "
            "phytoplankton, attracting schools of small pelagics followed by larger predatory species. PFZ advisory lines represent "
            "dynamic boundary fronts rather than static fish locations. In general oceanographic context, frontal features remain "
            "observable for 2 to 3 days under calm conditions, but rapid wind-driven mixing or seasonal depressions can dissipate "
            "the frontal structure earlier."
        ),
    ),
    EvidenceDocument(
        id="doc_monsoon_fishing_ban",
        title="General Overview of Annual Monsoon Fishing Ban Periods in India",
        source="Indian Coastal Fisheries Reference Overview",
        source_type=EvidenceClassification.REGULATORY,
        publisher="Public Maritime Fisheries Reference",
        published_at=None,
        retrieved_at="2023-04-01T00:00:00Z",
        authority_level=SourceAuthority.GENERAL_REFERENCE,
        language="en",
        tags=["regulation", "monsoon_ban", "conservation", "eez", "trawling_prohibition", "compliance"],
        reference=None,
        content=(
            "In Indian coastal fisheries management, annual uniform fishing bans are established during monsoon periods to "
            "conserve marine fish stocks during breeding seasons and promote maritime safety during rough weather. Historically, "
            "the 61-day ban on the West Coast (covering Gujarat, Maharashtra, Goa, Karnataka, Kerala, Daman & Diu, and Lakshadweep) "
            "is observed from June 1 to July 31. On the East Coast (covering Tamil Nadu, Andhra Pradesh, Odisha, West Bengal, "
            "Puducherry, and Andaman & Nicobar Islands), the 61-day period is observed from April 15 to June 14. During these "
            "periods, seasonal conservation closures apply to mechanized fishing vessels and motorized craft, while non-motorized "
            "traditional artisanal crafts typically remain exempt for artisanal sustenance subject to local weather safety. Mariners "
            "should consult their coastal state fisheries department or local port officer for the current season's official gazette "
            "notification, as exact ban dates and exemptions are governed by annual statutory orders."
        ),
    ),
    EvidenceDocument(
        id="doc_maritime_zones_india",
        title="Maritime Zones of India & Coastal Navigation Guidelines",
        source="Coastal Navigation & Maritime Zones Reference",
        source_type=EvidenceClassification.REGULATORY,
        publisher="Public Maritime Navigation Reference",
        published_at=None,
        retrieved_at="2023-08-10T00:00:00Z",
        authority_level=SourceAuthority.GENERAL_REFERENCE,
        language="en",
        tags=["geofence", "territorial_waters", "imbl", "security", "regulations", "coast_guard"],
        reference=None,
        content=(
            "Under standard maritime zone conventions applicable to India, territorial waters extend up to 12 nautical miles "
            "(approximately 22.2 kilometers) from baseline baselines, with coastal state jurisdiction generally applying within "
            "this belt, while the Exclusive Economic Zone (EEZ) extends from 12 up to 200 nautical miles. Fishing vessels operating "
            "offshore are expected under coastal security guidelines to carry valid vessel registration, approved communication "
            "or distress alert transponders, and biometric fishermen identification cards. Navigational safety guidance advises "
            "strictly avoiding designated naval exercise areas, defense exclusion zones, commercial shipping traffic separation "
            "schemes (TSS), marine protected areas, and staying well clear of the International Maritime Boundary Line (IMBL). "
            "These statements provide general geographic context and do not constitute legal advice or replace official navigational "
            "notices (NOTAM/NOTMAR)."
        ),
    ),
    EvidenceDocument(
        id="doc_marine_distress_vhf",
        title="Standard Marine Emergency & Distress Communication Protocol (VHF Ch 16)",
        source="Standard Marine Distress Calling Reference",
        source_type=EvidenceClassification.OPERATIONAL_GUIDANCE,
        publisher="Public Seamanship Reference",
        published_at=None,
        retrieved_at="2023-09-01T00:00:00Z",
        authority_level=SourceAuthority.GENERAL_REFERENCE,
        language="en",
        tags=["emergency", "distress", "vhf16", "mayday", "panpan", "sar", "coast_guard"],
        reference=None,
        content=(
            "In maritime emergencies involving grave distress or vessel immobilization, international seamanship protocols "
            "designate VHF Marine Channel 16 (156.8 MHz) as the primary distress, safety, and calling frequency. For life-threatening "
            "emergencies involving immediate danger (such as fire, flooding, capsizing, or vessel abandonment), standard radiotelephony "
            "procedure is to broadcast the distress signal: 'MAYDAY, MAYDAY, MAYDAY', followed by vessel name, GPS coordinates, "
            "nature of distress, number of persons on board, and assistance needed. For urgent situations not involving immediate "
            "grave danger (such as engine disablement in manageable seas), the urgency signal is 'PAN-PAN, PAN-PAN, PAN-PAN'. "
            "Vessels equipped with satellite emergency beacons (such as EPIRB or Distress Alert Transmitters) should activate them "
            "in emergency situations to alert regional maritime search and rescue coordination authorities. This summary provides "
            "general emergency reference guidance."
        ),
    ),
    EvidenceDocument(
        id="doc_chlorophyll_satellite_interpretation",
        title="Satellite Ocean Color & Chlorophyll-a Interpretation in Marine Fisheries",
        source="NASA Ocean Color Algorithm Theoretical Basis Documentation (OCx)",
        source_type=EvidenceClassification.TECHNICAL_REFERENCE,
        publisher="NASA Ocean Biology Processing Group (OBPG)",
        published_at="2022-01-01T00:00:00Z",
        retrieved_at="2023-12-05T00:00:00Z",
        authority_level=SourceAuthority.VERIFIED_REFERENCE,
        language="en",
        tags=["chlorophyll", "ocean_color", "phytoplankton", "remote_sensing", "modis", "sentinel"],
        reference="https://oceancolor.gsfc.nasa.gov/atbd/chlor_a/",
        content=(
            "Chlorophyll-a concentration serves as the primary bio-optical proxy for phytoplankton biomass and upper-ocean primary "
            "productivity. In marine ecological context, coastal waters exhibiting chlorophyll-a concentrations between 0.2 and "
            "2.0 mg/m³ generally indicate productive marine feeding habitats capable of sustaining pelagic baitfish. Ultra-oligotrophic "
            "open ocean waters typically register below 0.05 mg/m³, while eutrophic coastal lagoons or algal bloom zones can exceed "
            "10.0 mg/m³. Spaceborne optical radiometers estimate chlorophyll by measuring spectral reflectance ratios in the blue "
            "and green bands (such as 443 nm vs 555 nm). A recognized physical constraint of satellite optical radiometry is cloud "
            "obscuration: sensors cannot penetrate clouds, heavy fog, or thick atmospheric aerosols. When satellite swaths are "
            "overcast, chlorophyll values cannot be retrieved and are categorized as UNAVAILABLE. Missing satellite observations "
            "indicate cloud coverage or lack of valid retrieval, not zero biological productivity."
        ),
    ),
]
