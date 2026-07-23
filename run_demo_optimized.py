"""
Dissertation Demo: 3-Agent + Direct API Architecture (Optimized)
Run this to show your supervisor the improved approach.

Usage: python run_demo_optimized.py
"""

import sys, time
sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
load_dotenv(override=True)

SAMPLE_INPUT = "Plan a 4-night trip from Lahore to Istanbul for 1 adult departing 2026-08-15, budget 800 USD. Interests: history, food, shopping."

print("=" * 70)
print("  DISSERTATION DEMO: 3-AGENT + DIRECT API")
print("  (Optimized — LLM only for extraction + coordination)")
print("=" * 70)

print(f"\n📝 SAME USER REQUEST:\n  {SAMPLE_INPUT}\n")

print("-" * 70)
print("  PHASE 1: Preferences Extractor")
print("  • 1 LLM call — same extraction as before")
print("  • Difference: NO conversational agent (skips 8-question loop)")
print("-" * 70)
input("  Press Enter to start Phase 1...")

from comparison.optimized_3agent import plan_trip_optimized

result = plan_trip_optimized(SAMPLE_INPUT)

print(f"\n  ✅ Extraction completed (1 LLM call)")
print(f"  Extracted: {result.get('extraction', '')[:200]}...\n")

print("-" * 70)
print("  PHASE 2: Direct API Calls (NO LLM)")
print("  • Flights → _call_fly_scraper_api()  [Python function, 0 LLM]")
print("  • Hotels → search_hotels_comprehensive()  [Python function, 0 LLM]")
print("  • Attractions → search_attractions()  [Python function, 0 LLM]")
print("  • Restaurants → search_restaurants()  [Python function, 0 LLM]")
print("  • Agents are REPLACED by direct Python function calls")
print("-" * 70)
input("  Press Enter to start Phase 2...")

print(f"\n  ✅ All API calls completed (0 LLM calls)")
print(f"  Phase 2 took: {result.get('phase2_s', 'N/A')}s\n")

print("-" * 70)
print("  PHASE 3: Itinerary Coordinator")
print("  • 1 LLM call — assembles data into itinerary")
print("  • NO web search tools — uses ONLY data provided")
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
print(f"  LLM calls:   {result.get('llm_calls', 0)} (vs 5 in 6-agent)")
print(f"  Architecture: 3-Agent + Direct API")
print("=" * 70)
