"""
Agent Cards for A2A Protocol Communication

This module defines the agent cards that describe each agent's capabilities,
interfaces, and communication protocols following the A2A standard.
"""

from typing import Dict, List, Any
from dataclasses import dataclass, field
from enum import Enum


class AgentCapability(Enum):
    """Defines agent capabilities"""
    CONVERSATION = "conversation"
    DATA_EXTRACTION = "data_extraction"
    FLIGHT_SEARCH = "flight_search"
    HOTEL_SEARCH = "hotel_search"
    ATTRACTION_SEARCH = "attraction_search"
    COORDINATION = "coordination"
    BUDGET_CALCULATION = "budget_calculation"


@dataclass
class AgentCard:
    """
    Agent Card defines the metadata and capabilities of an agent
    for A2A protocol communication
    """
    agent_id: str
    agent_name: str
    role: str
    capabilities: List[AgentCapability]
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    communication_protocol: str = "A2A"
    version: str = "1.0"
    description: str = ""
    can_receive_from: List[str] = field(default_factory=list)
    can_send_to: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert agent card to dictionary"""
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "role": self.role,
            "capabilities": [cap.value for cap in self.capabilities],
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "communication_protocol": self.communication_protocol,
            "version": self.version,
            "description": self.description,
            "can_receive_from": self.can_receive_from,
            "can_send_to": self.can_send_to
        }


# ============================================
# AGENT CARD DEFINITIONS
# ============================================

CONVERSATIONAL_AGENT_CARD = AgentCard(
    agent_id="conversational_agent",
    agent_name="Travel Conversation Assistant",
    role="User interaction and information gathering",
    capabilities=[AgentCapability.CONVERSATION],
    description="""Engages users in natural conversation to understand travel needs.
    Collects information about destination, dates, budget, interests, and special requirements.""",
    input_schema={
        "type": "object",
        "properties": {
            "user_message": {"type": "string"},
            "conversation_id": {"type": "string"}
        },
        "required": ["user_message", "conversation_id"]
    },
    output_schema={
        "type": "object",
        "properties": {
            "conversation_transcript": {"type": "string"},
            "confidence_level": {"type": "string", "enum": ["high", "medium", "low"]},
            "collected_info": {"type": "object"}
        }
    },
    can_receive_from=["user", "preferences_extractor"],
    can_send_to=["preferences_extractor"]
)

PREFERENCES_EXTRACTOR_CARD = AgentCard(
    agent_id="preferences_extractor",
    agent_name="Travel Preferences Extractor",
    role="Data extraction and structuring",
    capabilities=[AgentCapability.DATA_EXTRACTION],
    description="""Receives conversation data and extracts structured travel preferences.
    Validates completeness and flags missing information.""",
    input_schema={
        "type": "object",
        "properties": {
            "conversation_transcript": {"type": "string"},
            "conversation_id": {"type": "string"}
        }
    },
    output_schema={
        "type": "object",
        "properties": {
            "origin": {"type": "string"},
            "destination": {"type": "string"},
            "departure_date": {"type": "string"},
            "return_date": {"type": "string"},
            "total_budget": {"type": "number"},
            "budget_breakdown": {"type": "object"},
            "interests": {"type": "array"},
            "travel_style": {"type": "string"},
            "special_requirements": {"type": "array"},
            "missing_info": {"type": "array"}
        }
    },
    can_receive_from=["conversational_agent"],
    can_send_to=["flight_search_agent", "hotel_agent", "attraction_agent", "conversational_agent"]
)

FLIGHT_SEARCH_AGENT_CARD = AgentCard(
    agent_id="flight_search_agent",
    agent_name="Flight Search Specialist",
    role="Flight search and recommendation",
    capabilities=[AgentCapability.FLIGHT_SEARCH],
    description="""Queries MCP Flight Search Server to find optimal flight options.
    Filters and ranks results based on budget, timing, and preferences.""",
    input_schema={
        "type": "object",
        "properties": {
            "origin": {"type": "string"},
            "destination": {"type": "string"},
            "departure_date": {"type": "string"},
            "return_date": {"type": "string"},
            "budget": {"type": "number"},
            "preferences": {"type": "object"}
        }
    },
    output_schema={
        "type": "object",
        "properties": {
            "flights": {"type": "array"},
            "recommendation": {"type": "string"},
            "reasoning": {"type": "string"},
            "total_cost": {"type": "number"}
        }
    },
    can_receive_from=["preferences_extractor"],
    can_send_to=["itinerary_coordinator"]
)

HOTEL_AGENT_CARD = AgentCard(
    agent_id="hotel_agent",
    agent_name="Hotel Search Specialist",
    role="Accommodation search and recommendation",
    capabilities=[AgentCapability.HOTEL_SEARCH],
    description="""Queries MCP Accommodation Server to find suitable hotels.
    Matches hotels to budget and preferences.""",
    input_schema={
        "type": "object",
        "properties": {
            "destination": {"type": "string"},
            "checkin_date": {"type": "string"},
            "checkout_date": {"type": "string"},
            "budget": {"type": "number"},
            "preferences": {"type": "object"}
        }
    },
    output_schema={
        "type": "object",
        "properties": {
            "hotels": {"type": "array"},
            "recommendation": {"type": "string"},
            "total_cost": {"type": "number"}
        }
    },
    can_receive_from=["preferences_extractor"],
    can_send_to=["itinerary_coordinator"]
)

ATTRACTION_AGENT_CARD = AgentCard(
    agent_id="attraction_agent",
    agent_name="Attractions & Activities Specialist",
    role="Attraction and experience discovery",
    capabilities=[AgentCapability.ATTRACTION_SEARCH],
    description="""Queries MCP Attractions Server to discover activities and experiences.
    Categorizes by day and matches to user interests.""",
    input_schema={
        "type": "object",
        "properties": {
            "destination": {"type": "string"},
            "interests": {"type": "array"},
            "activity_level": {"type": "string"},
            "trip_duration": {"type": "number"}
        }
    },
    output_schema={
        "type": "object",
        "properties": {
            "attractions": {"type": "array"},
            "daily_categories": {"type": "object"},
            "estimated_costs": {"type": "object"}
        }
    },
    can_receive_from=["preferences_extractor"],
    can_send_to=["itinerary_coordinator"]
)

ITINERARY_COORDINATOR_CARD = AgentCard(
    agent_id="itinerary_coordinator",
    agent_name="Itinerary Coordinator & Optimizer",
    role="Itinerary synthesis and optimization",
    capabilities=[AgentCapability.COORDINATION, AgentCapability.BUDGET_CALCULATION],
    description="""Receives all planning data from search agents and synthesizes into
    an optimized itinerary. Ensures budget adherence, timing optimization, and flow.""",
    input_schema={
        "type": "object",
        "properties": {
            "flight_data": {"type": "object"},
            "hotel_data": {"type": "object"},
            "attraction_data": {"type": "object"},
            "user_preferences": {"type": "object"}
        }
    },
    output_schema={
        "type": "object",
        "properties": {
            "itinerary": {"type": "object"},
            "daily_schedule": {"type": "array"},
            "total_cost": {"type": "number"},
            "cost_breakdown": {"type": "object"},
            "booking_links": {"type": "object"},
            "tips": {"type": "array"}
        }
    },
    can_receive_from=["flight_search_agent", "hotel_agent", "attraction_agent"],
    can_send_to=["user"]
)


# ============================================
# AGENT REGISTRY
# ============================================

AGENT_REGISTRY: Dict[str, AgentCard] = {
    "conversational_agent": CONVERSATIONAL_AGENT_CARD,
    "preferences_extractor": PREFERENCES_EXTRACTOR_CARD,
    "flight_search_agent": FLIGHT_SEARCH_AGENT_CARD,
    "hotel_agent": HOTEL_AGENT_CARD,
    "attraction_agent": ATTRACTION_AGENT_CARD,
    "itinerary_coordinator": ITINERARY_COORDINATOR_CARD
}


def get_agent_card(agent_id: str) -> AgentCard:
    """Get agent card by ID"""
    if agent_id not in AGENT_REGISTRY:
        raise ValueError(f"Agent {agent_id} not found in registry")
    return AGENT_REGISTRY[agent_id]


def validate_communication(sender_id: str, receiver_id: str) -> bool:
    """Validate if communication is allowed between two agents"""
    sender_card = get_agent_card(sender_id)
    return receiver_id in sender_card.can_send_to
