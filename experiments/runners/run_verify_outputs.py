import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
"""
Run 4 verification tests to validate complete multi-day itinerary outputs.
Focuses on capturing full outputs rather than metrics.
"""

import os
import time
import json
from datetime import datetime
from crewai import Crew

# 4 Test Scenarios (diverse multi-day trips)
TEST_QUERIES = [
    {
        "id": "VERIFY_01",
        "query": "5-day trip to Barcelona from London for 2 adults. Budget $3000. Beach, Gaudi architecture, tapas. Departure April 10, 2025.",
        "expected_days": 5
    },
    {
        "id": "VERIFY_02", 
        "query": "3-day weekend getaway to Amsterdam for a couple. Budget $1500. Museums, canals, local food. May 2-5, 2025.",
        "expected_days": 3
    },
    {
        "id": "VERIFY_03",
        "query": "5-day cultural trip to Istanbul for 2 adults. Budget $2500. Hagia Sophia, Blue Mosque, bazaars, Turkish food. Oct 5-10, 2025.",
        "expected_days": 5
    },
    {
        "id": "VERIFY_04",
        "query": "4-day ski trip to Swiss Alps (Zermatt) for 3 adults. Budget $6000. Skiing, spa, fondue. Jan 15-19, 2026.",
        "expected_days": 4
    }
]


def run_verification():
    print(f"🚀 RUNNING 4 OUTPUT VERIFICATION TESTS")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 60)
    
    results = {"runs": [], "timestamp": datetime.now().isoformat()}
    
    try:
        from agents_optimized import TripPlannerAgentsOptimized
        from tasks import TripPlannerTasks
    except ImportError as e:
        print(f"Import Error: {e}")
        return

    for i, case in enumerate(TEST_QUERIES):
        print(f"\n[{i+1}/4] Running: {case['id']} ({case['expected_days']} days)")
        print(f"Query: {case['query']}")
        print("-" * 40)
        start_time = time.time()
        
        try:
            # Initialize optimized agents
            agents = TripPlannerAgentsOptimized(use_mini_models=True)
            tasks = TripPlannerTasks()
            cid = f"VERIFY_{case['id']}_{int(time.time())}"
            
            # Create agents
            conv_agent = agents.conversational_agent()
            pref_agent = agents.preferences_extractor_agent()
            flight_agent = agents.flight_search_agent()
            hotel_agent = agents.hotel_agent()
            attr_agent = agents.attraction_agent()
            coord_agent = agents.itinerary_coordinator_agent()
            
            # Create tasks
            t_conv = tasks.conversation_task(conv_agent, case['query'], cid)
            t_extract = tasks.extraction_task(pref_agent, cid, t_conv)
            t_flight = tasks.flight_search_task(flight_agent, cid, t_extract)
            t_hotel = tasks.hotel_search_task(hotel_agent, cid, t_extract)
            t_attr = tasks.attraction_search_task(attr_agent, cid, t_extract)
            t_coord = tasks.coordination_task(coord_agent, cid, t_extract, t_flight, t_hotel, t_attr)
            
            crew = Crew(
                agents=[conv_agent, pref_agent, flight_agent, hotel_agent, attr_agent, coord_agent],
                tasks=[t_conv, t_extract, t_flight, t_hotel, t_attr, t_coord],
                verbose=False
            )
            
            result = crew.kickoff()
            latency = time.time() - start_time
            
            # Get full output
            output_text = str(result.raw if hasattr(result, 'raw') else result)
            
            # Count days in output
            import re
            day_count = len(re.findall(r'(?:^|\n)\s*(?:#{1,4}\s*)?(?:\*{1,2})?(?:Day|DAY|day)\s*\d+', output_text))
            
            run_data = {
                "id": case['id'],
                "query": case['query'],
                "expected_days": case['expected_days'],
                "found_days": day_count,
                "latency_seconds": round(latency, 1),
                "output_length": len(output_text),
                "full_output": output_text  # Save complete output
            }
            results["runs"].append(run_data)
            
            print(f"✅ DONE | Latency: {latency:.1f}s | Days found: {day_count}/{case['expected_days']}")
            print(f"Output length: {len(output_text)} chars")

            # Save incrementally
            with open("verification_outputs.json", "w", encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
                
            # Also save individual output files for easy reading
            with open(f"output_{case['id']}.txt", "w", encoding='utf-8') as f:
                f.write(f"Query: {case['query']}\n")
                f.write(f"Expected Days: {case['expected_days']}\n")
                f.write("=" * 60 + "\n\n")
                f.write(output_text)

        except Exception as e:
            latency = time.time() - start_time
            print(f"❌ FAILED: {e}")
            results["runs"].append({
                "id": case['id'],
                "error": str(e),
                "latency_seconds": round(latency, 1)
            })
            
            with open("verification_outputs.json", "w", encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
    
    print("\n" + "=" * 60)
    print("📊 VERIFICATION COMPLETE")
    print(f"Results saved to: verification_outputs.json")
    print(f"Individual outputs: output_VERIFY_01.txt, etc.")


if __name__ == "__main__":
    run_verification()

