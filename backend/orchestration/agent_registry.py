"""
ORCA Agent Registry — Phase 4
Central registry of available domain agents, capabilities, and interface requirements.
Supports dependency injection for deterministic testing and dynamic capability extension.
"""

from typing import Dict, List, Optional, Type
from pydantic import BaseModel, Field, ConfigDict

from agents.base_agent import BaseAgent
from agents.weather_agent import WeatherAgent
from agents.marine_agent import MarineAgent
from agents.chlorophyll_agent import ChlorophyllAgent
from agents.pfz_agent import PFZAgent
from agents.hazard_agent import HazardAgent
from agents.gis_agent import GISAgent
from agents.route_agent import RouteAgent


class AgentMetadata(BaseModel):
    """
    Standardized capability definition and input contract for a registered agent.
    Provides clear grounding for LLM planner reasoning.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = Field(..., description="Unique canonical name of the agent (e.g. 'weather', 'pfz')")
    agent: BaseAgent = Field(..., description="Domain agent instance adhering to BaseAgent contract")
    capability_description: str = Field(..., description="Human and LLM-readable description of domain capabilities")
    required_inputs: List[str] = Field(default_factory=list, description="Mandatory parameter names required for execution")
    optional_inputs: List[str] = Field(default_factory=list, description="Optional parameter names supported by the agent")


class AgentRegistry:
    """
    Central repository for ORCA domain agents.
    Enforces that the orchestrator calls domain agents exclusively and never bypasses
    them to directly call underlying tools or external services.
    """

    def __init__(self, agents: Optional[Dict[str, BaseAgent]] = None):
        """
        Initialize the registry.
        If custom agent instances are provided, they are registered (dependency injection).
        Otherwise, default instances of all standard domain agents are initialized.
        """
        self._registry: Dict[str, AgentMetadata] = {}

        if agents is not None:
            # Register provided agent instances (dependency injection for testing or custom mocks)
            for name, agent_instance in agents.items():
                self._register_default_agent_by_name(name, agent_instance)
        else:
            # Initialize standard domain agents
            self._init_standard_agents()

    def _init_standard_agents(self) -> None:
        """Register the 7 canonical ORCA domain agents."""
        self.register(
            name="weather",
            agent=WeatherAgent(),
            capability_description=(
                "Retrieves atmospheric conditions: temperature, wind speed, wind gusts, "
                "wind direction, relative humidity, and precipitation forecasts."
            ),
            required_inputs=["latitude", "longitude"],
            optional_inputs=["timestamp", "query"],
        )

        self.register(
            name="marine",
            agent=MarineAgent(),
            capability_description=(
                "Retrieves oceanographic conditions: significant wave height, dominant wave period, "
                "swell wave height, swell wave direction, and sea surface temperature (SST)."
            ),
            required_inputs=["latitude", "longitude"],
            optional_inputs=["timestamp", "query"],
        )

        self.register(
            name="chlorophyll",
            agent=ChlorophyllAgent(),
            capability_description=(
                "Retrieves satellite ocean-color chlorophyll-a concentrations (MODIS-Aqua / NASA Earthdata) "
                "and verifies satellite data availability without fabricating missing values."
            ),
            required_inputs=["latitude", "longitude"],
            optional_inputs=["timestamp", "query"],
        )

        self.register(
            name="pfz",
            agent=PFZAgent(),
            capability_description=(
                "Retrieves official INCOIS Potential Fishing Zone (PFZ) advisories, landing center "
                "bearings/distances, ocean thermal frontal lines, and historical reference validity."
            ),
            required_inputs=["latitude", "longitude"],
            optional_inputs=["radius_km", "query"],
        )

        self.register(
            name="hazard",
            agent=HazardAgent(),
            capability_description=(
                "Evaluates real-time marine safety hazards, severe squalls, gale warnings, "
                "extreme wave conditions, and active meteorological alerts."
            ),
            required_inputs=["latitude", "longitude"],
            optional_inputs=["query"],
        )

        self.register(
            name="gis",
            agent=GISAgent(),
            capability_description=(
                "Performs spatial GIS reasoning: point-in-polygon checks, official maritime boundary "
                "geofence queries, coastal security corridors, and marine protected area clearance."
            ),
            required_inputs=["latitude", "longitude"],
            optional_inputs=["radius_km", "operation", "route_coords", "override_zones"],
        )

        self.register(
            name="route",
            agent=RouteAgent(),
            capability_description=(
                "Generates candidate marine navigation corridors, computes environmental risk scores, "
                "evaluates geofence clearance, and produces explainable passage recommendations."
            ),
            required_inputs=["latitude", "longitude", "destination_latitude", "destination_longitude"],
            optional_inputs=["destination_name", "time_window", "override_zones"],
        )

    def _register_default_agent_by_name(self, name: str, agent: BaseAgent) -> None:
        """Helper to register an injected agent instance under its standard name."""
        meta_defaults = {
            "weather": (
                "Retrieves atmospheric conditions (wind, gusts, temperature, precipitation).",
                ["latitude", "longitude"],
                ["timestamp", "query"],
            ),
            "marine": (
                "Retrieves oceanographic conditions (wave height, period, swell, SST).",
                ["latitude", "longitude"],
                ["timestamp", "query"],
            ),
            "chlorophyll": (
                "Retrieves satellite ocean-color chlorophyll-a concentrations.",
                ["latitude", "longitude"],
                ["timestamp", "query"],
            ),
            "pfz": (
                "Retrieves INCOIS Potential Fishing Zones (PFZ) advisories and landing center references.",
                ["latitude", "longitude"],
                ["radius_km", "query"],
            ),
            "hazard": (
                "Evaluates marine hazards and active weather/ocean alerts.",
                ["latitude", "longitude"],
                ["query"],
            ),
            "gis": (
                "Performs spatial reasoning and maritime geofence restriction checks.",
                ["latitude", "longitude"],
                ["radius_km", "operation", "route_coords", "override_zones"],
            ),
            "route": (
                "Generates candidate marine navigation corridors and evaluates passage risk.",
                ["latitude", "longitude", "destination_latitude", "destination_longitude"],
                ["destination_name", "time_window", "override_zones"],
            ),
        }

        desc, req_in, opt_in = meta_defaults.get(
            name,
            (agent.description or f"Custom agent {name}", ["latitude", "longitude"], []),
        )
        self.register(
            name=name,
            agent=agent,
            capability_description=desc,
            required_inputs=req_in,
            optional_inputs=opt_in,
        )

    def register(
        self,
        name: str,
        agent: BaseAgent,
        capability_description: str,
        required_inputs: Optional[List[str]] = None,
        optional_inputs: Optional[List[str]] = None,
    ) -> None:
        """Register a domain agent with metadata."""
        if not isinstance(agent, BaseAgent):
            raise TypeError(f"Agent '{name}' must inherit from BaseAgent, got {type(agent)}")

        canonical_name = name.strip().lower()
        self._registry[canonical_name] = AgentMetadata(
            name=canonical_name,
            agent=agent,
            capability_description=capability_description.strip(),
            required_inputs=required_inputs or [],
            optional_inputs=optional_inputs or [],
        )

    def get(self, agent_name: str) -> BaseAgent:
        """
        Retrieve the agent instance by canonical name.
        Raises KeyError if the agent is unknown.
        """
        canonical_name = agent_name.strip().lower()
        if canonical_name not in self._registry:
            raise KeyError(
                f"Unknown agent '{agent_name}'. Registered agents: {list(self._registry.keys())}"
            )
        return self._registry[canonical_name].agent

    def get_metadata(self, agent_name: str) -> AgentMetadata:
        """
        Retrieve agent metadata by canonical name.
        Raises KeyError if the agent is unknown.
        """
        canonical_name = agent_name.strip().lower()
        if canonical_name not in self._registry:
            raise KeyError(
                f"Unknown agent '{agent_name}'. Registered agents: {list(self._registry.keys())}"
            )
        return self._registry[canonical_name]

    def has(self, agent_name: str) -> bool:
        """Check if an agent is registered."""
        return agent_name.strip().lower() in self._registry

    def list_agents(self) -> List[str]:
        """Return list of canonical names for all registered agents."""
        return list(self._registry.keys())

    def list_capabilities(self) -> Dict[str, AgentMetadata]:
        """Return shallow copy of all registered agent metadata."""
        return dict(self._registry)

    def describe_capabilities_prompt(self) -> str:
        """
        Produce a concise, structured prompt summary of registered agent capabilities,
        used by the Planner to determine necessary capabilities without hallucinations.
        """
        lines = ["Available ORCA Domain Agents:"]
        for name, meta in self._registry.items():
            req_str = ", ".join(meta.required_inputs)
            opt_str = ", ".join(meta.optional_inputs) if meta.optional_inputs else "none"
            lines.append(
                f"- **{name}**: {meta.capability_description}\n"
                f"  Required Inputs: [{req_str}] | Optional Inputs: [{opt_str}]"
            )
        return "\n".join(lines)


# Singleton factory helper
_default_registry: Optional[AgentRegistry] = None


def get_default_registry() -> AgentRegistry:
    """Return or initialize the singleton default AgentRegistry."""
    global _default_registry
    if _default_registry is None:
        _default_registry = AgentRegistry()
    return _default_registry
