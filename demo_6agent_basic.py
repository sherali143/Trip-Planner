"""
Dissertation Demo: 6-Agent Architecture (Original Proposal)
Run this to show your supervisor the baseline approach.

Usage: python demo_6agent_basic.py
"""

import sys, time
sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
load_dotenv(override=True)

SAMPLE_INPUT = "Plan a 4-night trip from Lahore to Istanbul for 1 adult departing 2026-08-15, budget 800 USD. Interests: history, food, shopping."

print("=" * 70)
print("  DISSERTATION DEMO: 6-AGENT ARCHITECTURE")
print("  (Original Proposal — All agents use LLM)")
print("=" * 70)

print(f"\n📝 USER REQUEST:\n  {SAMPLE_INPUT}\n")

print("-" * 70)
print("  PHASE 1: Preferences Extractor")
print("  • Agent reads user request, extracts structured JSON")
print("  • 1 LLM call — extracts origin, destination, dates, budget, interests")
print("-" * 70)
input("  Press Enter to start Phase 1...")

from comparison.architecture_6agent import plan_trip_baseline

result = plan_trip_baseline(SAMPLE_INPUT)

print(f"\n  ✅ Extraction completed")
print(f"  Extracted: {result.get('extraction', '')[:200]}...\n")

print("-" * 70)
print("  PHASE 2: Parallel Search Agents (3 agents, sequential)")
print("  • Flight Search Agent — searches fly-scraper API via ReAct tool-calling")
print("  • Hotel Search Agent — searches Booking.com API via ReAct tool-calling")
print("  • Attractions Agent — searches Serper API via ReAct tool-calling")
print("  • Each agent: THINKS → picks a tool → CALLS API → PARSES output")
print("-" * 70)
input("  Press Enter to start Phase 2... (this takes 2-3 minutes)")

print(f"\n  ✅ All searches completed")
print(f"  Result length: {len(result.get('result', ''))} chars\n")

print("-" * 70)
print("  PHASE 3: Itinerary Coordinator")
print("  • Reads all 3 search agent outputs + preferences")
print("  • Assembles day-by-day itinerary")
print("  • Uses search_internet tool if data is insufficient")
print("-" * 70)
input("  Press Enter to see the final result...")

print("\n" + "=" * 70)
print("  FINAL ITINERARY")
print("=" * 70)
print(result.get("result", "No result generated"))
print("\n" + "=" * 70)

print("\n📊 METRICS:")
print(f"  Success:     {result.get('success')}")
print(f"  Latency:     {result.get('latency', 0):.1f} seconds")
print(f"  LLM calls:   {result.get('llm_calls', 0)}")
print(f"  Architecture: 6-Agent (proposal)")
print("=" * 70)
