"""
Tests for the parts of the A2A library the shipped path never calls.

The dissertation is honest that the shipped path RECORDS A2A messages rather than
dispatching them, so a slice of this library is unexercised in production. That is
a design decision. It is not a reason to leave the code unverified: a dead-code
sweep found six functions here that nothing in the project referenced, which means
nothing had ever demonstrated they work.

Two of them matter more than the rest. `to_json`/`from_json` are the difference
between a protocol that can cross a process boundary and one that only exists
inside a single Python heap — and this project describes itself as implementing a
protocol. If they were broken, that description would be wrong.

Every test here is pure logic. No model, no network, no keys.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from trip_planner.comms.protocol import (A2AMessage, A2AProtocol, MessageType,
                                         create_message)
from trip_planner.comms.registry import AGENT_REGISTRY

# A pair the registry actually permits. Using a forbidden pair would make every
# test fail on permission validation rather than on the thing being tested.
SENDER, RECEIVER = "preferences_extractor", "itinerary_coordinator"
CONVERSATION = "test-conversation-1"


def _message(**overrides) -> A2AMessage:
    fields = dict(sender=SENDER, receiver=RECEIVER, message_type=MessageType.REQUEST,
                  content={"budget": 800, "destination": "Istanbul"},
                  conversation_id=CONVERSATION)
    fields.update(overrides)
    return A2AMessage(**fields)


# --------------------------------------------------------------- serialisation
def test_a_message_serialises_to_json_that_is_actually_json():
    text = _message().to_json()
    parsed = json.loads(text)          # would raise on a Python repr
    assert parsed["sender"] == SENDER
    assert parsed["receiver"] == RECEIVER


def test_enums_serialise_as_their_values_not_as_python_objects():
    """`MessageType.REQUEST` must not reach the wire as "MessageType.REQUEST"."""
    parsed = json.loads(_message().to_json())
    assert parsed["message_type"] == MessageType.REQUEST.value
    assert "MessageType." not in json.dumps(parsed)


def test_a_message_survives_a_round_trip():
    original = _message()
    restored = A2AMessage.from_json(original.to_json())
    assert restored.sender == original.sender
    assert restored.receiver == original.receiver
    assert restored.message_type == original.message_type
    assert restored.content == original.content
    assert restored.conversation_id == original.conversation_id
    assert restored.message_id == original.message_id


def test_every_message_type_survives_a_round_trip():
    for message_type in MessageType:
        restored = A2AMessage.from_json(_message(message_type=message_type).to_json())
        assert restored.message_type == message_type


def test_an_agent_card_serialises_to_primitives():
    """to_dict has to produce something JSON can encode, or it is not a card."""
    card = AGENT_REGISTRY[SENDER]
    data = card.to_dict()
    json.dumps(data)                   # the real assertion: it must encode
    assert data["agent_id"] == SENDER
    assert all(isinstance(c, str) for c in data["capabilities"]), (
        "capabilities must be values, not enum objects")


@pytest.mark.parametrize("agent_id", sorted(AGENT_REGISTRY))
def test_every_registered_card_serialises(agent_id):
    json.dumps(AGENT_REGISTRY[agent_id].to_dict())


# ------------------------------------------------------------------- dispatch
def test_a_registered_executor_receives_the_message_content():
    protocol = A2AProtocol()
    seen = {}

    def executor(content, conversation_id):
        seen["content"] = content
        seen["conversation_id"] = conversation_id
        return {"ok": True}

    protocol.register_agent_executor(RECEIVER, executor)
    protocol.send_message(_message())
    result = protocol.process_next_message()

    assert seen["content"] == {"budget": 800, "destination": "Istanbul"}
    assert seen["conversation_id"] == CONVERSATION
    assert result is not None, "processing a queued message returned nothing"


def test_processing_an_empty_queue_returns_none_rather_than_raising():
    assert A2AProtocol().process_next_message() is None


def test_a_message_for_an_agent_with_no_executor_is_not_silently_executed():
    """
    An unrouted message must not be handed to whatever executor is available.

    Returning None here is the documented behaviour. The test pins it because the
    alternative — delivering to the wrong agent — is the failure mode the
    conformance audit already reports for polling (check A5).
    """
    protocol = A2AProtocol()
    protocol.send_message(_message())
    assert protocol.process_next_message() is None


def test_send_to_agent_puts_a_well_formed_message_in_the_queue():
    from trip_planner.comms.protocol import AgentExecutor

    protocol = A2AProtocol()
    # The executor's own function is irrelevant here: send_to_agent is about
    # putting a message on the queue, not about running anything.
    agent = AgentExecutor(SENDER, lambda *_: None, protocol)
    agent.send_to_agent(RECEIVER, {"note": "hello"}, CONVERSATION,
                        MessageType.INFO)

    history = protocol.conversation_histories.get(CONVERSATION) or []
    assert len(history) == 1
    assert history[0].sender == SENDER
    assert history[0].receiver == RECEIVER
    assert history[0].content == {"note": "hello"}


def test_create_message_helper_matches_a_hand_built_message():
    helper = create_message(SENDER, RECEIVER, {"a": 1}, CONVERSATION)
    assert helper.sender == SENDER
    assert helper.receiver == RECEIVER
    assert helper.message_type == MessageType.INFO
    assert helper.conversation_id == CONVERSATION


# ----------------------------------------------------------------- permissions
def test_an_undeclared_sender_receiver_pair_is_refused():
    """The registry's declarations have to mean something at send time."""
    protocol = A2AProtocol()
    # user -> flight_data_provider is not a declared edge.
    forbidden = _message(sender="user", receiver="flight_data_provider")
    assert protocol.send_message(forbidden) is False
    assert not protocol.conversation_histories.get(CONVERSATION)
