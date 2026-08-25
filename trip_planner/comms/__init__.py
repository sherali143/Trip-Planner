"""
The message protocol between components.

`protocol` holds the message envelope and its queue; `registry` holds the
agent cards that declare who is allowed to send what to whom.
"""

from trip_planner.comms.protocol import A2AProtocol, A2AMessage, MessageType, MessagePriority, MessageQueue, AgentExecutor, create_message
from trip_planner.comms.registry import AgentCard, AgentCapability, AGENT_REGISTRY, get_agent_card, validate_communication

__all__ = [
    "A2AProtocol", "A2AMessage", "MessageType", "MessagePriority",
    "MessageQueue", "AgentExecutor", "create_message",
    "AgentCard", "AgentCapability", "AGENT_REGISTRY",
    "get_agent_card", "validate_communication",
]
