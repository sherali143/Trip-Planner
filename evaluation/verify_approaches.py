"""
WHAT THIS FILE DOES
===================
Shows, on one screen, that every part of this project really exists and really
responds: the agents in all four approaches, the MCP tool server, and the A2A
protocol layer.

    python -m evaluation.verify_approaches

Why this exists
---------------
"The six-agent design works" is a claim. A demonstration that runs one approach
end to end proves that one approach. This walks all four and prints what each is
actually made of — how many agents, how many tools each agent holds, how many
loop steps it is allowed — so the difference between the naive and tuned versions
of the proposal's design is a number on the screen rather than an assertion.

It also makes a real JSON-RPC round trip to the tool server, including a request
the server is supposed to refuse, so "the MCP server works" is demonstrated
rather than asserted.

WHAT THIS COSTS: nothing. Constructing a CrewAI agent does not call the model —
only kickoff() does, and this never calls it. The one network-shaped action is a
tool call to our own local server, which does arithmetic. No API key is spent, so
this is safe to run repeatedly, including in front of someone.

Note on agent counts: approaches B and C build FIVE agents, not six. The
conversational agent of the six-agent design is deliberately left out so every
approach receives the identical request string. They are a five-agent ablation of
a six-agent design, and Section 3.4 of the dissertation says so.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

os.environ["TRIP_PLANNER_API_MODE"] = "replay"
from dotenv import load_dotenv

load_dotenv(override=True)
import trip_planner  # noqa: F401  side effect: logging defaults


def show(label, obj):
    """Call every *_agent() factory on obj and report what it produced."""
    names = [n for n in dir(obj)
             if n.endswith("_agent") and not n.startswith("_")
             and callable(getattr(obj, n))]
    print(f"\n{label} -- {len(names)} agent factories:")
    total_tools = 0
    for name in sorted(names):
        agent = getattr(obj, name)()
        total_tools += len(agent.tools)
        print(f"   {name:<30} tools={len(agent.tools):<3} "
              f"max_iter={getattr(agent, 'max_iter', '-'):<4} "
              f"role={agent.role[:30]}")
    print(f"   {'':<30} {total_tools} tool slots in total")
    return len(names), total_tools


print("=" * 78)
print("  VERIFYING EVERY APPROACH -- no model calls, no quota spent")
print("=" * 78)

print("\n--- THE PROPOSAL'S DESIGN (approaches B and C) ---")

from evaluation.arm_b_six_agent_naive import BaselineAgents

b_agents, b_tools = show("APPROACH B  six agents, as first built", BaselineAgents())

from evaluation.arm_c_six_agent_tuned import OptimizedAgents

c_agents, c_tools = show("APPROACH C  the same six, tuned", OptimizedAgents())

print("\n--- THE SHIPPED PRODUCT (approach D) ---")
from trip_planner.agents import TripPlannerAgents

d_agents, d_tools = show("APPROACH D  three agents, direct retrieval",
                         TripPlannerAgents())

print("\n--- APPROACH A (the control) ---")
import evaluation.arm_a_single_llm as arm_a

has_agents = any(n.endswith("_agent") for n in dir(arm_a))
print(f"   defines no agents and no tools: {not has_agents}  (this is the point)")

print("\n" + "=" * 78)
print("  MCP TOOL SERVER")
print("=" * 78)
import re

server_src = open(os.path.join(ROOT, "trip_planner", "server",
                              "mcp_server.py"), encoding="utf-8").read()
declared = re.findall(r'Tool\(\s*name="([^"]+)"', server_src)
print(f"\n  {len(declared)} tools declared with an input schema:")
for i in range(0, len(declared), 3):
    print("    " + "  ".join(f"{t:<32}" for t in declared[i:i + 3]))

from trip_planner.tools.mcp_client import mcp_client, run_async_tool

print("\n  live JSON-RPC round trip through the server:")
ok = run_async_tool(mcp_client.call_tool("calculate", {"operation": "(450+320)*2"}))
print(f"    calculate((450+320)*2)  -> {ok}")
guard = run_async_tool(mcp_client.call_tool("calculate", {"operation": "9**9**9"}))
print(f"    calculate(9**9**9)      -> {guard}")

print("\n" + "=" * 78)
print("  A2A PROTOCOL LAYER")
print("=" * 78)
from trip_planner.comms.protocol import MessageType
from trip_planner.comms.registry import AGENT_REGISTRY

print(f"\n  {len(AGENT_REGISTRY)} agent cards registered:")
for agent_id in sorted(AGENT_REGISTRY):
    card = AGENT_REGISTRY[agent_id]
    send = len(getattr(card, "can_send_to", []) or [])
    recv = len(getattr(card, "can_receive_from", []) or [])
    print(f"    {agent_id:<26} can_send_to={send:<3} can_receive_from={recv}")
types = [m.name for m in MessageType]
print(f"\n  {len(types)} message types: {', '.join(types)}")

print("\n" + "=" * 78)
print("  SUMMARY")
print("=" * 78)
print(f"""
  Approach A   no agents, no tools                       (the control)
  Approach B   {b_agents} agents, {b_tools:>2} tool slots   the proposal, as first built
  Approach C   {c_agents} agents, {c_tools:>2} tool slots   the proposal, tuned
  Approach D   {d_agents} agents, {d_tools:>2} tool slots   what ships
  MCP server   {len(declared)} tools over JSON-RPC, responding
  A2A layer    {len(AGENT_REGISTRY)} agent cards, {len(types)} message types
""")
