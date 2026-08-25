"""
Shows the message protocol working, one message at a time.

Sends real messages, shows one being refused because the pair was never
declared, and prints the conversation at the end. No model, no network, under
a second.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import logging

import trip_planner  # noqa: F401  side effect: logging defaults
from trip_planner.comms.protocol import A2AMessage, A2AProtocol, MessageType
from trip_planner.comms.registry import AGENT_REGISTRY

# The protocol logs every enqueue and every send at INFO. That is right for a real
# run, where the log is the audit trail. Here it would print each message twice —
# once as a log line and once in the narrative below — so the narrative is left to
# speak for itself.
logging.getLogger("trip_planner.comms.protocol").setLevel(logging.WARNING)

RULE = "=" * 78
CONVERSATION = "demo-conversation"

# The exchange the shipped path really performs when it plans a trip: the
# extractor tells the coordinator what the traveller asked for, each data
# provider reports what it found, and the coordinator returns the itinerary.
EXCHANGE = [
    ("preferences_extractor", "itinerary_coordinator", MessageType.REQUEST,
     {"destination": "Istanbul", "nights": 4, "budget": 800},
     "the traveller's request, structured"),
    ("flight_data_provider", "itinerary_coordinator", MessageType.RESPONSE,
     {"flights_found": 18, "cheapest_usd": 734},
     "what the flight API returned"),
    ("hotel_data_provider", "itinerary_coordinator", MessageType.RESPONSE,
     {"hotels_found": 10, "cheapest_per_night_usd": 33},
     "what the hotel API returned"),
    ("attraction_data_provider", "itinerary_coordinator", MessageType.RESPONSE,
     {"attractions_found": 12},
     "what the attractions search returned"),
    ("restaurant_data_provider", "itinerary_coordinator", MessageType.RESPONSE,
     {"restaurants_found": 9},
     "what the restaurant search returned"),
    ("itinerary_coordinator", "user", MessageType.RESPONSE,
     {"itinerary": "Day 1: Sultanahmet ..."},
     "the finished plan, back to the traveller"),
]


def _heading(text: str) -> None:
    print(f"\n{RULE}\n  {text}\n{RULE}")


def main() -> int:
    _heading("THE AGENTS, AND WHAT EACH IS ALLOWED TO SAY")
    print("\n  Every agent carries a card declaring who it may talk to. This is what")
    print("  makes an undeclared message a detectable mistake rather than a silent")
    print("  one.\n")
    print(f"  {'agent':<26}{'may send to':<26}may receive from")
    print(f"  {'-' * 74}")
    for agent_id in sorted(AGENT_REGISTRY):
        card = AGENT_REGISTRY[agent_id]
        send = ", ".join(getattr(card, "can_send_to", []) or []) or "-"
        recv = ", ".join(getattr(card, "can_receive_from", []) or []) or "-"
        print(f"  {agent_id:<26}{send[:24]:<26}{recv[:24]}")

    protocol = A2AProtocol()
    protocol.start_conversation(CONVERSATION, {"demo": True})

    _heading("SENDING THE MESSAGES A REAL TRIP SENDS")
    print()
    for sender, receiver, kind, payload, why in EXCHANGE:
        message = A2AMessage(sender=sender, receiver=receiver, message_type=kind,
                             content=payload, conversation_id=CONVERSATION)
        accepted = protocol.send_message(message)
        mark = "accepted" if accepted else "REFUSED"
        print(f"  [{mark:>8}]  {sender}  ->  {receiver}   ({kind.value})")
        print(f"              {why}")
        print(f"              payload: {payload}")
        print()

    _heading("WHAT HAPPENS TO A MESSAGE NOBODY DECLARED")
    print("\n  The registry never declared that the traveller may speak straight to")
    print("  the flight provider. Sending it anyway:\n")
    forbidden = A2AMessage(sender="user", receiver="flight_data_provider",
                           message_type=MessageType.REQUEST,
                           content={"find": "flights"},
                           conversation_id=CONVERSATION)
    accepted = protocol.send_message(forbidden)
    print(f"    user -> flight_data_provider :  "
          f"{'accepted (WRONG)' if accepted else 'REFUSED, as it should be'}")
    print("\n  It never reaches the queue and never enters the history, so an")
    print("  undeclared route cannot quietly become part of the system.")

    _heading("ROUTING: A MESSAGE GOES TO THE AGENT IT WAS ADDRESSED TO")
    delivered = []
    protocol.register_agent_executor(
        "itinerary_coordinator",
        lambda content, conversation_id: delivered.append(content) or {"ok": True})
    handled = protocol.process_next_message()
    print(f"\n  next message processed        : "
          f"{'yes' if handled else 'no'}")
    print(f"  delivered to the coordinator : {delivered[0] if delivered else 'nothing'}")
    print("\n  A message addressed to an agent with no executor registered is")
    print("  returned unhandled rather than given to whoever is available.")

    _heading("THE CONVERSATION, REPLAYED FROM ITS OWN HISTORY")
    history = protocol.get_conversation_history(CONVERSATION)
    print(f"\n  {len(history)} messages recorded under conversation "
          f"{CONVERSATION!r}:\n")
    for i, message in enumerate(history, 1):
        print(f"    [{i}] {message.sender} -> {message.receiver} "
              f"({message.message_type.value})")
    print("\n  Every message is serialisable, so this exchange could cross a")
    print("  process boundary rather than only living in one program's memory:")
    if history:
        sample = history[0].to_json()
        print(f"\n    {sample[:150]}...")

    _heading("WHAT THIS LAYER DOES NOT DO — REPORTED, NOT HIDDEN")
    print("""
  The conformance audit (python -m trip_planner.evaluation.exp_protocol) tests this layer
  against its own declarations and fails 3 of its 5 A2A checks:

    * message priority is declared but never honoured by the queue
    * an inbound permission (can_receive_from) is not checked on delivery
    * a message polled by the wrong recipient does not stay queued for the
      right one

  These are findings of the project, argued in Chapter 6 of the dissertation,
  not defects left unnoticed. In the shipped path the layer RECORDS the
  exchange and the orchestrator calls the agents directly, so none of the
  three affects a planned trip — but each would matter if the layer were
  used to dispatch, and saying so is the point of auditing your own work.
""")
    protocol.end_conversation(CONVERSATION)
    print(RULE)
    print("  No model was called. No API was called. No quota was spent.")
    print(RULE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
