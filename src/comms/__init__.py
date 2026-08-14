"""
Agent-to-Agent (A2A) protocol.

Typed, permission-validated messages between agents, so no component passes
free text to another. Every architecture in this project uses this layer
unchanged — which is what lets the evaluation attribute differences to the
data-retrieval strategy rather than to how components talk.

`protocol` carries the envelope and priority queue; `registry` holds the agent
cards that declare who may send what to whom.
"""

from src.comms.protocol import A2AProtocol, A2AMessage, MessageType, MessagePriority, MessageQueue, AgentExecutor, create_message
from src.comms.registry import AgentCard, AgentCapability, AGENT_REGISTRY, get_agent_card, validate_communication

__all__ = [
    "A2AProtocol", "A2AMessage", "MessageType", "MessagePriority",
    "MessageQueue", "AgentExecutor", "create_message",
    "AgentCard", "AgentCapability", "AGENT_REGISTRY",
    "get_agent_card", "validate_communication",
]
