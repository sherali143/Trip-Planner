"""
A2A (Agent-to-Agent) Communication Protocol

This module implements the A2A protocol for structured communication between agents,
including message formatting, routing, validation, and agent execution management.
"""

import json
import uuid
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, asdict
from queue import Queue
import logging

from agent_cards import get_agent_card, validate_communication


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MessageType(Enum):
    """Types of A2A messages"""
    REQUEST = "request"
    RESPONSE = "response"
    QUERY = "query"
    INFO = "info"
    ERROR = "error"
    ACK = "acknowledgment"


class MessagePriority(Enum):
    """Message priority levels"""
    HIGH = 1
    MEDIUM = 2
    LOW = 3


@dataclass
class A2AMessage:
    """
    Standard message format for agent-to-agent communication
    following A2A protocol specification
    """
    sender: str
    receiver: str
    message_type: MessageType
    content: Dict[str, Any]
    conversation_id: str
    message_id: Optional[str] = None
    timestamp: Optional[str] = None
    priority: MessagePriority = MessagePriority.MEDIUM
    requires_ack: bool = False
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.message_id is None:
            self.message_id = str(uuid.uuid4())
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()
        if self.metadata is None:
            self.metadata = {}
    
    def to_json(self) -> str:
        """Serialize message to JSON"""
        data = asdict(self)
        data['message_type'] = self.message_type.value
        data['priority'] = self.priority.value
        return json.dumps(data)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'A2AMessage':
        """Deserialize message from JSON"""
        data = json.loads(json_str)
        data['message_type'] = MessageType(data['message_type'])
        data['priority'] = MessagePriority(data['priority'])
        return cls(**data)
    
    def validate(self) -> bool:
        """Validate message structure and permissions"""
        try:
            # Check if communication is allowed
            if not validate_communication(self.sender, self.receiver):
                logger.error(f"Communication not allowed: {self.sender} -> {self.receiver}")
                return False
            
            # Validate sender agent exists
            sender_card = get_agent_card(self.sender)
            
            # Validate receiver agent exists
            receiver_card = get_agent_card(self.receiver)
            
            # Validate content against receiver's input schema (simplified)
            if not self.content:
                logger.error("Message content is empty")
                return False
            
            return True
        except Exception as e:
            logger.error(f"Message validation failed: {e}")
            return False


class MessageQueue:
    """Thread-safe message queue for A2A communication"""
    
    def __init__(self):
        self.queue = Queue()
        self.processed_messages: List[str] = []
    
    def enqueue(self, message: A2AMessage) -> bool:
        """Add message to queue"""
        if message.validate():
            self.queue.put(message)
            logger.info(f"Message enqueued: {message.message_id} from {message.sender} to {message.receiver}")
            return True
        return False
    
    def dequeue(self) -> Optional[A2AMessage]:
        """Get next message from queue"""
        if not self.queue.empty():
            message = self.queue.get()
            self.processed_messages.append(message.message_id)
            return message
        return None
    
    def is_empty(self) -> bool:
        """Check if queue is empty"""
        return self.queue.empty()


class A2AProtocol:
    """
    Main A2A Protocol manager that handles message routing,
    validation, and agent execution
    """
    
    def __init__(self):
        self.message_queue = MessageQueue()
        self.conversation_histories: Dict[str, List[A2AMessage]] = {}
        self.agent_executors: Dict[str, Callable] = {}
        self.active_conversations: Dict[str, Dict[str, Any]] = {}
    
    def register_agent_executor(self, agent_id: str, executor: Callable):
        """Register an agent's execution function"""
        self.agent_executors[agent_id] = executor
        logger.info(f"Registered executor for agent: {agent_id}")
    
    def send_message(self, message: A2AMessage) -> bool:
        """Send a message through the protocol"""
        if message.validate():
            self.message_queue.enqueue(message)
            
            # Store in conversation history
            conv_id = message.conversation_id
            if conv_id not in self.conversation_histories:
                self.conversation_histories[conv_id] = []
            self.conversation_histories[conv_id].append(message)
            
            logger.info(f"Message sent: {message.sender} -> {message.receiver}")
            return True
        else:
            logger.error("Message validation failed, not sent")
            return False
    
    def receive_message(self, agent_id: str) -> Optional[A2AMessage]:
        """Receive next message for specific agent"""
        message = self.message_queue.dequeue()
        if message and message.receiver == agent_id:
            return message
        return None
    
    def process_next_message(self) -> Optional[Dict[str, Any]]:
        """Process the next message in the queue"""
        message = self.message_queue.dequeue()
        if message is None:
            return None
        
        logger.info(f"Processing message: {message.message_id}")
        
        # Get executor for receiver agent
        executor = self.agent_executors.get(message.receiver)
        if executor is None:
            logger.error(f"No executor registered for agent: {message.receiver}")
            return None
        
        try:
            # Execute agent with message content
            result = executor(message.content, message.conversation_id)
            
            # Send acknowledgment if required
            if message.requires_ack:
                ack_message = A2AMessage(
                    sender=message.receiver,
                    receiver=message.sender,
                    message_type=MessageType.ACK,
                    content={"message_id": message.message_id, "status": "received"},
                    conversation_id=message.conversation_id
                )
                self.send_message(ack_message)
            
            return result
        except Exception as e:
            logger.error(f"Error executing agent {message.receiver}: {e}")
            
            # Send error message
            error_message = A2AMessage(
                sender=message.receiver,
                receiver=message.sender,
                message_type=MessageType.ERROR,
                content={"error": str(e), "message_id": message.message_id},
                conversation_id=message.conversation_id
            )
            self.send_message(error_message)
            return None
    
    def get_conversation_history(self, conversation_id: str) -> List[A2AMessage]:
        """Get all messages for a conversation"""
        return self.conversation_histories.get(conversation_id, [])
    
    def start_conversation(self, conversation_id: str, initial_data: Dict[str, Any]):
        """Start a new conversation"""
        self.active_conversations[conversation_id] = {
            "started_at": datetime.utcnow().isoformat(),
            "status": "active",
            "initial_data": initial_data
        }
        logger.info(f"Started conversation: {conversation_id}")
    
    def end_conversation(self, conversation_id: str):
        """End a conversation"""
        if conversation_id in self.active_conversations:
            self.active_conversations[conversation_id]["status"] = "completed"
            self.active_conversations[conversation_id]["ended_at"] = datetime.utcnow().isoformat()
            logger.info(f"Ended conversation: {conversation_id}")


class AgentExecutor:
    """
    Agent Executor handles the execution flow for individual agents
    within the A2A protocol
    """
    
    def __init__(self, agent_id: str, agent_function: Callable, protocol: A2AProtocol):
        self.agent_id = agent_id
        self.agent_function = agent_function
        self.protocol = protocol
        self.agent_card = get_agent_card(agent_id)
    
    def execute(self, input_data: Dict[str, Any], conversation_id: str) -> Dict[str, Any]:
        """Execute agent with input data"""
        logger.info(f"Executing agent: {self.agent_id}")
        
        try:
            # Execute agent function
            result = self.agent_function(input_data)
            
            logger.info(f"Agent {self.agent_id} execution completed")
            return result
        except Exception as e:
            logger.error(f"Agent {self.agent_id} execution failed: {e}")
            raise
    
    def send_to_agent(self, receiver_id: str, content: Dict[str, Any], 
                     conversation_id: str, message_type: MessageType = MessageType.INFO):
        """Send message to another agent"""
        message = A2AMessage(
            sender=self.agent_id,
            receiver=receiver_id,
            message_type=message_type,
            content=content,
            conversation_id=conversation_id
        )
        self.protocol.send_message(message)


def create_message(sender: str, receiver: str, content: Dict[str, Any], 
                  conversation_id: str, message_type: MessageType = MessageType.INFO) -> A2AMessage:
    """Helper function to create A2A messages"""
    return A2AMessage(
        sender=sender,
        receiver=receiver,
        message_type=message_type,
        content=content,
        conversation_id=conversation_id
    )
