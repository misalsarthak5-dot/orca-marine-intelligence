"""
ORCA Phase 4 — AgentRegistry Verification Suite
Tests:
1. All 7 expected agents registered by default (weather, marine, chlorophyll, pfz, hazard, gis, route)
2. Unknown agent retrieval rejected cleanly with KeyError
3. Metadata inspection (capability descriptions, required/optional inputs)
4. Dependency injection works with custom/mock agents
5. Non-BaseAgent injection rejected with TypeError
"""

import asyncio
from core.schemas import AgentRequest, AgentResult, AgentStatus
from agents.base_agent import BaseAgent
from orchestration.agent_registry import AgentRegistry, AgentMetadata, get_default_registry
from agents.weather_agent import WeatherAgent
from agents.marine_agent import MarineAgent
from agents.chlorophyll_agent import ChlorophyllAgent
from agents.pfz_agent import PFZAgent
from agents.hazard_agent import HazardAgent
from agents.gis_agent import GISAgent
from agents.route_agent import RouteAgent


class DummyCustomAgent(BaseAgent):
    name = "dummy_agent"
    description = "A dummy agent for testing dependency injection"

    async def execute(self, request: AgentRequest) -> AgentResult:
        return AgentResult(
            agent=self.name,
            status=AgentStatus.SUCCESS,
            data={"test": True},
            confidence=1.0,
        )


def test_registry_default_agents():
    print("\n[TEST 1] Standard Registry Agents Verification...")
    registry = AgentRegistry()

    expected_agents = ["weather", "marine", "chlorophyll", "pfz", "hazard", "gis", "route"]
    registered = registry.list_agents()

    for agent_name in expected_agents:
        assert agent_name in registered, f"Missing registered agent: {agent_name}"
        assert registry.has(agent_name), f"registry.has('{agent_name}') returned False"
        agent_instance = registry.get(agent_name)
        assert isinstance(agent_instance, BaseAgent), f"Agent '{agent_name}' does not inherit BaseAgent"

    assert len(registered) == 7
    print("  [PASS] All 7 canonical ORCA domain agents registered successfully.")


def test_registry_unknown_agent_rejected():
    print("\n[TEST 2] Unknown Agent Rejection...")
    registry = AgentRegistry()

    unknowns = ["unknown_agent", "arbitrary_code", "python_exec", ""]
    for unk in unknowns:
        try:
            registry.get(unk)
            assert False, f"Expected KeyError for unknown agent '{unk}'"
        except KeyError as e:
            assert unk.strip().lower() in str(e) or "Unknown agent" in str(e)
            print(f"  [PASS] Rejected unknown agent '{unk}': {e}")


def test_registry_metadata_and_inputs():
    print("\n[TEST 3] Agent Metadata and Input Contracts...")
    registry = AgentRegistry()

    # Route agent requires both origin and destination coordinates
    route_meta = registry.get_metadata("route")
    assert "latitude" in route_meta.required_inputs
    assert "longitude" in route_meta.required_inputs
    assert "destination_latitude" in route_meta.required_inputs
    assert "destination_longitude" in route_meta.required_inputs

    # Weather agent requires origin coordinates
    weather_meta = registry.get_metadata("weather")
    assert "latitude" in weather_meta.required_inputs
    assert "longitude" in weather_meta.required_inputs
    assert "destination_latitude" not in weather_meta.required_inputs

    # Describe capabilities prompt
    prompt_str = registry.describe_capabilities_prompt()
    assert "Available ORCA Domain Agents:" in prompt_str
    assert "route" in prompt_str
    assert "chlorophyll" in prompt_str
    print("  [PASS] Metadata and input contracts verified.")


def test_registry_dependency_injection():
    print("\n[TEST 4] Dependency Injection Verification...")
    custom_agent = DummyCustomAgent()
    injected_registry = AgentRegistry(agents={"custom_test": custom_agent})

    assert injected_registry.has("custom_test")
    assert injected_registry.get("custom_test") is custom_agent
    assert "custom_test" in injected_registry.list_agents()

    # Verify custom metadata
    meta = injected_registry.get_metadata("custom_test")
    assert meta.name == "custom_test"
    print("  [PASS] Dependency injection correctly accepts and registers custom agents.")


def test_registry_invalid_agent_type_rejected():
    print("\n[TEST 5] Non-BaseAgent Rejection...")
    registry = AgentRegistry()

    class NotAnAgent:
        pass

    try:
        registry.register("invalid", NotAnAgent(), "Not a real agent")  # type: ignore
        assert False, "Expected TypeError when registering non-BaseAgent"
    except TypeError as e:
        print(f"  [PASS] Rejected non-BaseAgent: {e}")


def main():
    print("=" * 65)
    print("ORCA PHASE 4 — AGENT REGISTRY VERIFICATION SUITE")
    print("=" * 65)

    test_registry_default_agents()
    test_registry_unknown_agent_rejected()
    test_registry_metadata_and_inputs()
    test_registry_dependency_injection()
    test_registry_invalid_agent_type_rejected()

    print("\n" + "=" * 65)
    print("ALL AGENT REGISTRY TESTS PASSED SUCCESSFULLY!")
    print("=" * 65)


if __name__ == "__main__":
    main()
