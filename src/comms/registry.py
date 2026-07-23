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
            "preferences": {"type": "object"},
            "flight_data": {"type": "object"},
            "hotel_data": {"type": "object"},
            "attraction_data": {"type": "object"},
            "restaurant_data": {"type": "object"}
        }
    },
    output_schema={
        "type": "object",
        "properties": {
            "itinerary": {"type": "object"},
            "daily_schedule": {"type": "array"},
            "total_cost": {"type": "number"},
            "cost_breakdown": {"type": "object"},
            "tips": {"type": "array"}
        }
    },
    can_receive_from=["preferences_extractor", "flight_data_provider", "hotel_data_provider", "attraction_data_provider", "restaurant_data_provider"],
    can_send_to=["user"]
)

FLIGHT_DATA_PROVIDER_CARD = AgentCard(
    agent_id="flight_data_provider",
    agent_name="Flight Data Provider",
    role="Real-time flight search via fly-scraper API",
    capabilities=[AgentCapability.DATA_EXTRACTION],
    description="""Queries the fly-scraper API for real-time flight data.
    Returns available flights with pricing, airlines, and schedules within budget.""",
    input_schema={
        "type": "object",
        "properties": {
            "origin": {"type": "string"},
            "destination": {"type": "string"},
            "departure_date": {"type": "string"},
            "return_date": {"type": "string"},
            "adults": {"type": "integer"},
            "budget": {"type": "number"}
        }
    },
    output_schema={
        "type": "object",
        "properties": {
            "flights": {"type": "array"},
            "search_summary": {"type": "object"}
        }
    },
    can_receive_from=["preferences_extractor"],
    can_send_to=["itinerary_coordinator"]
)

HOTEL_DATA_PROVIDER_CARD = AgentCard(
    agent_id="hotel_data_provider",
    agent_name="Hotel Data Provider",
    role="Real-time hotel search via Booking.com API",
    capabilities=[AgentCapability.DATA_EXTRACTION],
    description="""Queries Booking.com API for real-time hotel availability.
    Returns hotels with pricing, reviews, ratings, and nearby attractions.""",
    input_schema={
        "type": "object",
        "properties": {
            "destination": {"type": "string"},
            "checkin_date": {"type": "string"},
            "checkout_date": {"type": "string"},
            "budget_per_night": {"type": "number"},
            "adults": {"type": "integer"},
            "rooms": {"type": "integer"}
        }
    },
    output_schema={
        "type": "object",
        "properties": {
            "hotels": {"type": "array"},
            "search_summary": {"type": "object"}
        }
    },
    can_receive_from=["preferences_extractor"],
    can_send_to=["itinerary_coordinator"]
)

ATTRACTION_DATA_PROVIDER_CARD = AgentCard(
    agent_id="attraction_data_provider",
    agent_name="Attraction Data Provider",
    role="Attraction and activity search via Serper API",
    capabilities=[AgentCapability.DATA_EXTRACTION],
    description="""Searches for tourist attractions, activities, and points of interest
    using Serper web search API based on user interests and destination.""",
    input_schema={
        "type": "object",
        "properties": {
            "destination": {"type": "string"},
            "interests": {"type": "array"},
            "duration_days": {"type": "integer"}
        }
    },
    output_schema={
        "type": "object",
        "properties": {
            "attractions": {"type": "array"},
            "daily_suggestions": {"type": "array"}
        }
    },
    can_receive_from=["preferences_extractor"],
    can_send_to=["itinerary_coordinator"]
)

RESTAURANT_DATA_PROVIDER_CARD = AgentCard(
    agent_id="restaurant_data_provider",
    agent_name="Restaurant Data Provider",
    role="Restaurant search via Serper API",
    capabilities=[AgentCapability.DATA_EXTRACTION],
    description="""Searches for restaurants and dining options using Serper web search API.
    Returns restaurant recommendations with cuisine types and price ranges.""",
    input_schema={
        "type": "object",
        "properties": {
            "destination": {"type": "string"},
            "cuisine_types": {"type": "string"},
            "budget_per_meal": {"type": "number"}
        }
    },
    output_schema={
        "type": "object",
        "properties": {
            "restaurants": {"type": "array"},
            "recommendations": {"type": "array"}
        }
    },
    can_receive_from=["preferences_extractor"],
    can_send_to=["itinerary_coordinator"]
)


USER_CARD = AgentCard(
    agent_id="user",
    agent_name="End User",
    role="Human user receiving the final itinerary",
    capabilities=[],
    description="The human user who initiated the trip planning request.",
    input_schema={"type": "object", "properties": {}},
    output_schema={"type": "object", "properties": {}},
    can_receive_from=["itinerary_coordinator"],
    can_send_to=["conversational_agent"]
)

AGENT_REGISTRY: Dict[str, AgentCard] = {
    "conversational_agent": CONVERSATIONAL_AGENT_CARD,
    "preferences_extractor": PREFERENCES_EXTRACTOR_CARD,
    "itinerary_coordinator": ITINERARY_COORDINATOR_CARD,
    "flight_data_provider": FLIGHT_DATA_PROVIDER_CARD,
    "hotel_data_provider": HOTEL_DATA_PROVIDER_CARD,
    "attraction_data_provider": ATTRACTION_DATA_PROVIDER_CARD,
    "restaurant_data_provider": RESTAURANT_DATA_PROVIDER_CARD,
    "user": USER_CARD
}


def get_agent_card(agent_id: str) -> AgentCard:
    """Get agent card by ID"""
    if agent_id not in AGENT_REGISTRY:
        raise ValueError(f"Agent {agent_id} not found in registry")
    return AGENT_REGISTRY[agent_id]


def validate_communication(sender_id: str, receiver_id: str) -> bool:
    """Validate if communication is allowed between two agents"""
    try:
        sender_card = get_agent_card(sender_id)
        return receiver_id in sender_card.can_send_to
    except ValueError:
        return False
