"""
Dissertation Demo: Side-by-Side Comparison
Runs both architectures on the same input, shows metrics side-by-side.

Usage: python demo_comparison.py
"""

import sys, time
sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
load_dotenv(override=True)

SAMPLE_INPUT = "Plan a 4-night trip from Lahore to Istanbul for 1 adult departing 2026-08-15, budget 800 USD. Interests: history, food, shopping."

print("=" * 70)
print("  DISSERTATION DEMO: ARCHITECTURE COMPARISON")
print("  Same input · Two architectures · Side-by-side metrics")
print("=" * 70)

print(f"\n📝 INPUT:\n  {SAMPLE_INPUT}\n")

# ====== RUN 6-AGENT BASELINE ======
print("=" * 70)
print("  🔴 RUN 1: 6-AGENT BASELINE (proposal)")
print("=" * 70)
input("\n  Press Enter to start...")

t0 = time.time()
from comparison.architecture_6agent import plan_trip_baseline
r1 = plan_trip_baseline(SAMPLE_INPUT)
t1 = time.time()

print(f"\n  ✅ Completed in {r1.get('latency', 0):.1f}s")
print(f"     LLM calls: {r1.get('llm_calls', 0)}")

# ====== RUN 3-AGENT OPTIMIZED ======
print("\n" + "=" * 70)
print("  🟢 RUN 2: 3-AGENT + DIRECT API (optimized)")
print("=" * 70)
input("\n  Press Enter to start...")

from comparison.architecture_3agent import plan_trip_optimized
r2 = plan_trip_optimized(SAMPLE_INPUT)
t2 = time.time()

print(f"\n  ✅ Completed in {r2.get('latency', 0):.1f}s")
print(f"     LLM calls: {r2.get('llm_calls', 0)}")

# ====== COMPARISON TABLE ======
print("\n" + "=" * 70)
print("  📊 FINAL COMPARISON TABLE")
print("=" * 70)
print(f"  {'Metric':<35} {'6-Agent':<18} {'3-Agent':<18}")
print(f"  {'-'*35} {'-'*18} {'-'*18}")
print(f"  {'Architecture':<35} {'6 LLM Agents':<18} {'3 LLM + Direct API':<18}")
print(f"  {'LLM calls per trip':<35} {str(r1.get('llm_calls', '?')):<18} {str(r2.get('llm_calls', '?')):<18}")
print(f"  {'Total latency (s)':<35} {str(round(r1.get('latency', 0), 1)):<18} {str(round(r2.get('latency', 0), 1)):<18}")
print(f"  {'Success':<35} {str(r1.get('success')):<18} {str(r2.get('success')):<18}")
print(f"  {'Result length (chars)':<35} {str(len(r1.get('result', ''))):<18} {str(len(r2.get('result', ''))):<18}")

# Calculate improvements
if r1.get('latency') and r2.get('latency'):
    lat_imp = (1 - r2['latency'] / r1['latency']) * 100
    llm_imp = (1 - r2['llm_calls'] / r1['llm_calls']) * 100
    print(f"\n  🏆 IMPROVEMENTS:")
    print(f"     Latency:   {lat_imp:.0f}% faster ({r1.get('latency',0):.0f}s → {r2.get('latency',0):.0f}s)")
    print(f"     LLM calls: {llm_imp:.0f}% fewer ({r1.get('llm_calls',0)} → {r2.get('llm_calls',0)})")

print("=" * 70)
print("  💡 KEY INSIGHT FOR YOUR DISSERTATION:")
print("  The A2A protocol is IDENTICAL in both architectures.")
print("  Only the data-fetching layer changed: LLM agents → direct functions.")
print("  This proves the multi-agent protocol is decoupled from execution.")
print("=" * 70)
