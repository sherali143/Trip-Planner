"""
Experiment: protocol conformance (A2A and MCP).

Why this experiment exists
--------------------------
The proposal set two protocol targets (S3.10): an MCP schema pass rate of 100%
and an A2A error rate below 1%. Neither had ever been measured. Both are
measurable without a network call, an API key or an LLM request, so there is no
excuse for asserting them.

The experiment is designed to be able to FAIL. It checks the protocol layer
against what the proposal and the code's own documentation claim about it,
rather than checking that the code does what it does. Three of the five checks
did in fact fail on first run, and those failures are reported rather than
removed.

What is checked
---------------
A2A
  A1  every declared can_send_to edge is mirrored by can_receive_from
      (asymmetry proves one direction is decorative)
  A2  priority ordering is honoured: a HIGH message enqueued after a LOW one
      is delivered first
  A3  the message sequence the production orchestrator actually emits is
      permitted by the registry
  A4  an undeclared edge and an empty payload are both rejected
  A5  a message polled by the wrong recipient is not destroyed

MCP
  M1  every tool named in list_tools() can be dispatched by call_tool()
  M2  every parameter the implementation accepts is declared in inputSchema
      (an undeclared parameter cannot be set by an agent, so it silently
      takes its default)
  M3  what the implementation treats as mandatory matches schema.required
  M4  the API provider named in a tool's description is the provider the
      dispatcher actually calls

Results are written to evaluation/results/protocol_conformance.json so the
report and its figures regenerate from measured data with no re-run.

    python -m evaluation.exp_protocol
"""

from __future__ import annotations

import asyncio
import inspect
import json
import logging
import os
import re
import sys
from typing import Any, Dict, List

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

RESULTS_PATH = os.path.join(
    os.path.dirname(__file__), "results", "protocol_conformance.json"
)

# The registry logs an ERROR for every deliberately-rejected message. Those
# rejections are the expected result of checks A4/A5, so silence the noise
# rather than have the transcript imply something went wrong.
logging.getLogger("src.comms.protocol").setLevel(logging.CRITICAL)

# The message sequence trip_planner/orchestrator.py emits for one trip, in order. Kept
# here as data so the check is against the shipped path, not a hypothetical one.
PRODUCTION_SEQUENCE = [
    ("preferences_extractor", "itinerary_coordinator"),
    ("flight_data_provider", "itinerary_coordinator"),
    ("hotel_data_provider", "itinerary_coordinator"),
    ("attraction_data_provider", "itinerary_coordinator"),
    ("restaurant_data_provider", "itinerary_coordinator"),
    ("itinerary_coordinator", "user"),
]


def _check(check_id: str, claim: str, passed: bool, detail: str,
           observed: Any = None) -> Dict[str, Any]:
    return {
        "id": check_id,
        "claim": claim,
        "passed": bool(passed),
        "detail": detail,
        "observed": observed,
    }


# ---------------------------------------------------------------- A2A checks
def audit_a2a() -> List[Dict[str, Any]]:
    from trip_planner.comms.protocol import (A2AMessage, A2AProtocol, MessagePriority,
                                    MessageQueue, MessageType)
    from trip_planner.comms.registry import AGENT_REGISTRY, validate_communication

    checks: List[Dict[str, Any]] = []

    # A1 — is the permission matrix symmetric, or is one direction decorative?
    declared_edges = [(s, r) for s in AGENT_REGISTRY
                      for r in AGENT_REGISTRY[s].can_send_to]
    asymmetric = []
    for sender, card in AGENT_REGISTRY.items():
        for receiver in card.can_receive_from:
            if receiver in AGENT_REGISTRY and sender not in AGENT_REGISTRY[receiver].can_send_to:
                asymmetric.append(f"{receiver} -> {sender}")
    checks.append(_check(
        "A1",
        "every can_receive_from declaration is mirrored by the sender's can_send_to",
        not asymmetric,
        f"{len(asymmetric)} inbound declarations have no matching outbound "
        f"permission, so can_receive_from is never enforced: "
        f"validate_communication() consults only the sender's can_send_to.",
        {"declared_outbound_edges": len(declared_edges),
         "unmirrored_inbound_declarations": asymmetric},
    ))

    # A2 — priority ordering. Enqueue LOW then HIGH; HIGH must come out first.
    queue = MessageQueue()
    for tag, priority in (("low", MessagePriority.LOW), ("high", MessagePriority.HIGH)):
        queue.enqueue(A2AMessage(
            sender="preferences_extractor", receiver="itinerary_coordinator",
            message_type=MessageType.INFO, content={"tag": tag},
            conversation_id="conformance", priority=priority,
        ))
    delivered = []
    while not queue.is_empty():
        delivered.append(queue.dequeue().content["tag"])
    checks.append(_check(
        "A2",
        "the queue delivers HIGH priority before LOW (proposal Objective 2: 'priority queuing')",
        delivered[:1] == ["high"],
        f"MessageQueue wraps queue.{type(queue.queue).__name__}, which is FIFO. "
        f"The priority field is carried on every message and never read.",
        {"enqueued": ["low", "high"], "delivered": delivered,
         "container": type(queue.queue).__name__},
    ))

    # A3 — is the shipped message sequence actually permitted?
    permitted = [(s, r, validate_communication(s, r)) for s, r in PRODUCTION_SEQUENCE]
    n_ok = sum(1 for _, _, ok in permitted if ok)
    checks.append(_check(
        "A3",
        "every message the production orchestrator sends is permitted by the registry",
        n_ok == len(PRODUCTION_SEQUENCE),
        f"{n_ok}/{len(PRODUCTION_SEQUENCE)} messages in the shipped sequence pass "
        f"permission validation.",
        {"sequence": [{"from": s, "to": r, "permitted": ok} for s, r, ok in permitted],
         "permitted": n_ok, "total": len(PRODUCTION_SEQUENCE)},
    ))

    # A4 — does validation actually reject what it should?
    undeclared = A2AMessage(
        sender="flight_data_provider", receiver="hotel_data_provider",
        message_type=MessageType.INFO, content={"x": 1}, conversation_id="conformance",
    ).validate()
    empty = A2AMessage(
        sender="preferences_extractor", receiver="itinerary_coordinator",
        message_type=MessageType.INFO, content={}, conversation_id="conformance",
    ).validate()
    checks.append(_check(
        "A4",
        "an undeclared sender/receiver edge and an empty payload are both rejected",
        (not undeclared) and (not empty),
        "Permission validation and the empty-content guard both reject as designed.",
        {"undeclared_edge_accepted": undeclared, "empty_payload_accepted": empty},
    ))

    # A5 — does a wrong-recipient poll destroy the message?
    protocol = A2AProtocol()
    protocol.send_message(A2AMessage(
        sender="preferences_extractor", receiver="itinerary_coordinator",
        message_type=MessageType.INFO, content={"n": 1}, conversation_id="conformance",
    ))
    returned = protocol.receive_message("flight_data_provider")
    survived = not protocol.message_queue.is_empty()
    checks.append(_check(
        "A5",
        "a message polled by the wrong recipient stays queued for its real recipient",
        survived,
        "receive_message() dequeues before checking the recipient and discards the "
        "message when it does not match, so a single wrong poll destroys it. Not "
        "reached in production, which is why it never surfaced: the orchestrator "
        "uses the protocol as an audit log and never dequeues.",
        {"returned_to_wrong_recipient": returned,
         "message_survived_for_real_recipient": survived},
    ))
    return checks


# ---------------------------------------------------------------- MCP checks
def _dispatchable_tool_names(source: str) -> List[str]:
    """Tool names the call_tool dispatcher compares against, read from source."""
    return sorted(set(re.findall(r'name == "([a-z_]+)"', source)))


def _dispatch_targets(source: str) -> Dict[str, str]:
    """Map each dispatched tool name to the function the dispatcher calls."""
    targets: Dict[str, str] = {}
    blocks = re.split(r'(?:el)?if name == "([a-z_]+)":', source)
    for name, body in zip(blocks[1::2], blocks[2::2]):
        call = re.search(r"=\s*(?:await\s+)?([A-Za-z_][A-Za-z0-9_.]*)\(", body)
        if call:
            targets[name] = call.group(1)
    return targets


def audit_mcp() -> List[Dict[str, Any]]:
    import trip_planner.server.mcp_server as server

    checks: List[Dict[str, Any]] = []
    tools = asyncio.run(server.list_tools())
    source = inspect.getsource(server)
    dispatchable = _dispatchable_tool_names(source)
    targets = _dispatch_targets(source)

    # M1 — advertised vs dispatchable.
    advertised = sorted(t.name for t in tools)
    undispatchable = [n for n in advertised if n not in dispatchable]
    checks.append(_check(
        "M1",
        "every advertised tool can be dispatched",
        not undispatchable,
        f"{len(advertised)} tools advertised, {len(advertised) - len(undispatchable)} "
        f"dispatchable.",
        {"advertised": advertised, "undispatchable": undispatchable},
    ))

    # M2/M3 — schema against the implementation's real signature.
    per_tool = []
    undeclared_params = 0
    required_mismatches = 0
    for tool in tools:
        schema = tool.inputSchema or {}
        declared = set(schema.get("properties", {}))
        required = set(schema.get("required", []))
        target_name = targets.get(tool.name, tool.name)
        impl = getattr(server, target_name.split(".")[-1], None) or getattr(server, tool.name, None)

        row = {"tool": tool.name, "dispatches_to": target_name,
               "schema_params": sorted(declared)}
        if impl is None or not callable(impl):
            # Implemented inline in the dispatcher (or imported at call time);
            # the signature cannot be inspected, so record that honestly rather
            # than counting it as either a pass or a failure.
            row.update({"signature_inspectable": False,
                        "undeclared_params": [], "required_mismatch": []})
            per_tool.append(row)
            continue

        params = inspect.signature(impl).parameters
        mandatory = {n for n, p in params.items()
                     if p.default is inspect.Parameter.empty and n != "self"}
        undeclared = sorted(set(params) - declared)
        mismatch = sorted(mandatory - required)
        undeclared_params += len(undeclared)
        required_mismatches += len(mismatch)
        row.update({"signature_inspectable": True,
                    "undeclared_params": undeclared,
                    "required_mismatch": mismatch})
        per_tool.append(row)

    inspectable = [r for r in per_tool if r["signature_inspectable"]]
    clean = [r for r in inspectable if not r["undeclared_params"] and not r["required_mismatch"]]
    checks.append(_check(
        "M2",
        "every parameter the implementation accepts is declared in inputSchema "
        "(proposal S3.10 target: 100% schema pass rate)",
        undeclared_params == 0,
        f"{len(clean)}/{len(inspectable)} inspectable tools are clean. "
        f"{undeclared_params} implementation parameters are absent from their "
        f"schema, so an agent cannot set them and they silently take defaults.",
        {"tools": per_tool, "clean": len(clean), "inspectable": len(inspectable),
         "undeclared_parameter_count": undeclared_params},
    ))
    checks.append(_check(
        "M3",
        "what the implementation treats as mandatory matches schema.required",
        required_mismatches == 0,
        f"{required_mismatches} parameter(s) are mandatory in the implementation "
        f"but absent from schema.required.",
        {"mismatches": [{"tool": r["tool"], "params": r["required_mismatch"]}
                        for r in inspectable if r["required_mismatch"]]},
    ))

    # M4 — does the description name the provider the dispatcher calls?
    provider_words = {
        "fly-scraper": "fly-scraper", "booking.com": "booking", "booking": "booking",
        "serper": "serper",
    }
    provider_errors = []
    for tool in tools:
        described = {v for k, v in provider_words.items()
                     if k in (tool.description or "").lower()}
        target = targets.get(tool.name, "")
        actual = None
        if "booking" in target.lower():
            actual = "booking"
        elif "fly_scraper" in target.lower() or "fly-scraper" in target.lower():
            actual = "fly-scraper"
        elif "serper" in target.lower():
            actual = "serper"
        if described and actual and actual not in described:
            provider_errors.append({
                "tool": tool.name, "description_says": sorted(described),
                "dispatcher_calls": target, "actual_provider": actual,
            })
    checks.append(_check(
        "M4",
        "the API provider named in a tool's description is the provider the dispatcher calls",
        not provider_errors,
        f"{len(provider_errors)} tool(s) advertise one provider and call another. "
        f"An agent selecting a tool on its description gets a different backend.",
        {"mismatches": provider_errors},
    ))
    return checks


def run() -> Dict[str, Any]:
    a2a = audit_a2a()
    mcp = audit_mcp()
    checks = a2a + mcp
    failed = [c for c in checks if not c["passed"]]
    payload = {
        "experiment": "protocol_conformance",
        "cost": {"llm_requests": 0, "live_api_calls": 0, "usd": 0.0},
        "a2a_checks": a2a,
        "mcp_checks": mcp,
        "summary": {
            "total_checks": len(checks),
            "passed": len(checks) - len(failed),
            "failed": len(failed),
            "failed_ids": [c["id"] for c in failed],
        },
    }
    os.makedirs(os.path.dirname(RESULTS_PATH), exist_ok=True)
    with open(RESULTS_PATH, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, default=str)
    return payload


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    payload = run()
    print("\n" + "=" * 74)
    print("  PROTOCOL CONFORMANCE — A2A and MCP")
    print("  no network, no LLM, no API keys required")
    print("=" * 74)
    for group, label in (("a2a_checks", "A2A protocol"), ("mcp_checks", "MCP server")):
        print(f"\n  {label}")
        for c in payload[group]:
            print(f"    [{'PASS' if c['passed'] else 'FAIL'}] {c['id']}  {c['claim']}")
            if not c["passed"]:
                print(f"           {c['detail']}")
    s = payload["summary"]
    print("\n" + "=" * 74)
    print(f"  {s['passed']}/{s['total_checks']} checks pass. "
          f"Failed: {', '.join(s['failed_ids']) or 'none'}")
    print(f"  Written to {RESULTS_PATH}")
    print("=" * 74)


if __name__ == "__main__":
    main()
