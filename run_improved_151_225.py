"""
Run 75 improved iterations (runs 151-225) with:
1. Higher max_iter values
2. Auto-retry for short outputs
3. 75 unique, diverse queries
"""

import os
import time
import json
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables FIRST
load_dotenv()

from crewai import Crew, Agent
from textwrap import dedent
from langchain_openai import ChatOpenAI

# 75 UNIQUE QUERIES - diverse destinations, durations, and interests
UNIQUE_QUERIES = [
    # European Cities
    "5-day trip to Paris from New York for 2 adults. Budget $4000. Eiffel Tower, Louvre, French cuisine. May 15-20, 2025.",
    "4-day trip to Rome from Chicago for couple. Budget $3500. Colosseum, Vatican, pasta. June 1-5, 2025.",
    "6-day trip to Prague from Boston for 2. Budget $2800. Old Town, beer, castles. April 20-26, 2025.",
    "3-day trip to Vienna from LA for 2 adults. Budget $3200. Opera, coffee houses, Schonbrunn. May 5-8, 2025.",
    "7-day trip to Greece from Miami for 4. Budget $6000. Santorini, Athens, beaches. July 10-17, 2025.",
    "5-day trip to Lisbon from Seattle for couple. Budget $2500. Tram 28, Belem, Fado. Sept 5-10, 2025.",
    "4-day trip to Budapest from Dallas for 2. Budget $2200. Thermal baths, ruin bars. Oct 1-5, 2025.",
    "6-day trip to Copenhagen from Denver for 2 adults. Budget $4500. Tivoli, Nyhavn, design. Aug 15-21, 2025.",
    "5-day trip to Dublin from Phoenix for 2. Budget $2800. Guinness, Trinity, pubs. March 14-19, 2025.",
    "4-day trip to Edinburgh from Atlanta for couple. Budget $2600. Castle, Royal Mile, whisky. April 5-9, 2025.",
    
    # Asian Destinations
    "7-day trip to Tokyo from San Francisco for 2. Budget $5500. Shibuya, temples, sushi. April 1-8, 2025.",
    "10-day trip to Thailand from NYC for 2. Budget $4000. Bangkok, Phuket, temples. Nov 1-11, 2025.",
    "6-day trip to Bali from LA for couple. Budget $3500. Ubud, beaches, temples. May 20-26, 2025.",
    "5-day trip to Seoul from Seattle for 2 adults. Budget $3800. K-pop, palaces, food. June 10-15, 2025.",
    "8-day trip to Vietnam from Chicago for 2. Budget $3200. Hanoi, Ha Long Bay, pho. Oct 5-13, 2025.",
    "4-day trip to Hong Kong from Boston for 2. Budget $4200. Victoria Peak, dim sum. Sept 1-5, 2025.",
    "7-day trip to India from Dallas for 2. Budget $3000. Taj Mahal, Delhi, Jaipur. Feb 10-17, 2025.",
    "5-day trip to Philippines from Denver for couple. Budget $2800. Palawan, beaches. March 5-10, 2025.",
    "6-day trip to Malaysia from Miami for 2. Budget $2500. KL, Langkawi, food. April 15-21, 2025.",
    "9-day trip to Japan (Kyoto + Osaka) from Portland for 2. Budget $5000. Temples, food, gardens. May 1-10, 2025.",
    
    # Americas
    "5-day trip to Mexico City from Houston for 2. Budget $1800. Pyramids, tacos, museums. March 20-25, 2025.",
    "7-day trip to Costa Rica from Atlanta for 4. Budget $4500. Rainforest, beaches, zip-lining. June 15-22, 2025.",
    "4-day trip to Cancun from Chicago for couple. Budget $2200. Beach, ruins, snorkeling. July 5-9, 2025.",
    "6-day trip to Peru from NYC for 2. Budget $3800. Machu Picchu, Lima, ceviche. Aug 10-16, 2025.",
    "5-day trip to Argentina from LA for 2 adults. Budget $3500. Buenos Aires, tango, steak. Sept 20-25, 2025.",
    "8-day trip to Brazil from Miami for 2. Budget $4200. Rio, beaches, carnival. Feb 20-28, 2025.",
    "4-day trip to Colombia from Houston for couple. Budget $2000. Cartagena, coffee, salsa. April 10-14, 2025.",
    "7-day trip to Chile from SF for 2. Budget $4000. Santiago, wine, Patagonia. Nov 5-12, 2025.",
    "5-day trip to Cuba from Atlanta for 2. Budget $2500. Havana, music, classic cars. March 1-6, 2025.",
    "6-day trip to Ecuador from Denver for 2. Budget $2800. Quito, Galapagos, Amazon. May 15-21, 2025.",
    
    # Middle East & Africa
    "5-day trip to Dubai from NYC for 2 adults. Budget $5000. Burj Khalifa, desert safari. April 5-10, 2025.",
    "7-day trip to Morocco from Boston for couple. Budget $3000. Marrakech, desert, medina. Oct 10-17, 2025.",
    "6-day trip to Egypt from Chicago for 2. Budget $3500. Pyramids, Nile cruise, Cairo. Nov 15-21, 2025.",
    "4-day trip to Jordan from LA for 2. Budget $3200. Petra, Dead Sea, Wadi Rum. Sept 5-9, 2025.",
    "8-day trip to South Africa from Miami for 2. Budget $5500. Cape Town, safari, wine. Aug 1-9, 2025.",
    "5-day trip to Israel from Dallas for 2 adults. Budget $4000. Jerusalem, Tel Aviv, Dead Sea. May 10-15, 2025.",
    "7-day trip to Tanzania from Seattle for 2. Budget $6500. Safari, Serengeti, Zanzibar. July 20-27, 2025.",
    "4-day trip to Abu Dhabi from Phoenix for couple. Budget $3800. Sheikh Zayed Mosque, Ferrari World. March 10-14, 2025.",
    "6-day trip to Kenya from Denver for 2. Budget $5000. Safari, Nairobi, Masai Mara. June 5-11, 2025.",
    "5-day trip to Qatar from Atlanta for 2. Budget $4500. Doha, museums, desert. Feb 15-20, 2025.",
    
    # Australia & Pacific
    "10-day trip to Australia from LA for 2. Budget $7000. Sydney, Great Barrier Reef, Melbourne. Sept 1-11, 2025.",
    "7-day trip to New Zealand from SF for couple. Budget $5500. Auckland, Queenstown, Hobbiton. Nov 20-27, 2025.",
    "5-day trip to Fiji from Seattle for 2. Budget $4000. Beach resort, snorkeling, culture. Aug 5-10, 2025.",
    "8-day trip to Tahiti from LA for honeymoon. Budget $8000. Overwater bungalow, Bora Bora. June 1-9, 2025.",
    "6-day trip to Hawaii from Denver for 4. Budget $5500. Maui, beaches, volcano. July 4-10, 2025.",
    
    # Caribbean
    "5-day trip to Jamaica from NYC for 2. Budget $2800. Beaches, reggae, jerk chicken. March 15-20, 2025.",
    "4-day trip to Bahamas from Miami for couple. Budget $2500. Nassau, beaches, swimming pigs. April 1-5, 2025.",
    "6-day trip to Aruba from Boston for 2. Budget $3200. Beach, flamingos, casinos. May 20-26, 2025.",
    "7-day trip to St. Lucia from Atlanta for honeymoon. Budget $5000. Pitons, spa, romance. June 10-17, 2025.",
    "5-day trip to Turks and Caicos from Chicago for 2. Budget $4500. Beaches, snorkeling. July 1-6, 2025.",
    
    # Special Interest Trips
    "7-day food tour of Italy for 2 foodies. Budget $5000. Rome, Bologna, Florence. Sept 15-22, 2025.",
    "5-day photography trip to Iceland for 2. Budget $4000. Northern lights, waterfalls. Feb 1-6, 2025.",
    "10-day wine tour of France for couple. Budget $6000. Bordeaux, Champagne, Burgundy. Oct 1-11, 2025.",
    "6-day wellness retreat in Bali for 2. Budget $3500. Yoga, spa, meditation. March 10-16, 2025.",
    "4-day art tour of Amsterdam for 2 adults. Budget $2800. Van Gogh, Rijksmuseum, galleries. April 15-19, 2025.",
    "8-day history tour of Greece for 2. Budget $4500. Acropolis, Delphi, Olympia. May 5-13, 2025.",
    "5-day adventure trip to New Zealand for 2. Budget $5000. Bungee, hiking, rafting. Nov 1-6, 2025.",
    "7-day safari in Tanzania for couple. Budget $7500. Big Five, Serengeti, Ngorongoro. Aug 20-27, 2025.",
    "6-day beach hopper in Thailand for 2. Budget $2500. Phuket, Phi Phi, Krabi. Dec 1-7, 2025.",
    "4-day Christmas markets tour in Germany for 2. Budget $3000. Munich, Nuremberg. Dec 15-19, 2025.",
    
    # Family Trips
    "7-day Disney World trip for family of 4. Budget $6000. Magic Kingdom, Epcot, Hollywood Studios. June 20-27, 2025.",
    "5-day London trip for family of 5. Budget $5500. Harry Potter, Tower, Big Ben. July 15-20, 2025.",
    "10-day California road trip for 4. Budget $5000. LA, San Diego, San Francisco. Aug 1-11, 2025.",
    "6-day cruise to Caribbean for family of 4. Budget $4500. Multiple islands, all-inclusive. March 5-11, 2025.",
    "8-day Japan trip for family with kids. Budget $7000. Tokyo Disneyland, Kyoto temples. April 10-18, 2025.",
    
    # Business Mixed with Leisure
    "5-day business trip to Singapore with weekend leisure. Budget $4500. Conference + Marina Bay, Gardens. Sept 1-6, 2025.",
    "4-day conference in Las Vegas with entertainment. Budget $2500. CES, shows, Grand Canyon day trip. Jan 8-12, 2025.",
    "6-day business trip to London with sightseeing. Budget $4000. Meetings, West End, pubs. Oct 5-11, 2025.",
    "3-day tech conference in Berlin with culture. Budget $2000. Conference, museums, nightlife. May 20-23, 2025.",
    "5-day trade show in Dubai with desert safari. Budget $5500. Exhibition, Burj, souks. Nov 10-15, 2025.",
    
    # Budget Trips
    "5-day budget trip to Portugal for 2. Budget $1500. Lisbon, Porto, beaches. April 1-6, 2025.",
    "4-day cheap getaway to Krakow for couple. Budget $1000. Old town, Auschwitz, salt mines. March 10-14, 2025.",
    "7-day backpacking in Southeast Asia for 2. Budget $2000. Bangkok, Chiang Mai, beaches. May 1-8, 2025.",
    "3-day budget weekend in Montreal for 2. Budget $800. Old Montreal, poutine, bagels. June 5-8, 2025.",
    "5-day affordable trip to Guatemala for 2. Budget $1200. Antigua, Lake Atitlan, ruins. Feb 10-15, 2025."
]


def create_improved_agents():
    """Create agents with higher max_iter for better reliability."""
    llm_conversation = ChatOpenAI(model="gpt-4", temperature=0.7)
    llm_standard = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
    llm_coordinator = ChatOpenAI(model="gpt-4o", temperature=0.3)
    
    from tools.mcp_tools import (
        search_comprehensive_flights, search_round_trip_flights,
        search_hotels_comprehensive, search_hotel_destination,
        search_hotels_by_dest_id, get_hotel_reviews,
        search_internet, search_attractions, search_restaurants, calculate
    )
    
    conv_agent = Agent(
        role="Travel Assistant",
        goal="Collect travel requirements through friendly conversation",
        backstory="Friendly travel assistant. Collect: origin, destination, dates, travelers, budget, interests.",
        verbose=False, allow_delegation=False, llm=llm_conversation,
        tools=[], max_iter=7  # Increased from 5
    )
    
    pref_agent = Agent(
        role="Preferences Extractor",
        goal="Extract structured JSON from conversation",
        backstory="Extract preferences into JSON: origin, destination, dates, travelers, budget, interests.",
        verbose=False, allow_delegation=False, llm=llm_standard,
        tools=[], max_iter=5  # Increased from 3
    )
    
    flight_agent = Agent(
        role="Flight Specialist",
        goal="Find flights within budget using city names",
        backstory="Search flights via Booking.com API. Use city names, exact dates. Return top 5 options.",
        verbose=False, allow_delegation=False, llm=llm_standard,
        tools=[search_comprehensive_flights, search_round_trip_flights, search_internet, calculate],
        max_iter=6  # Increased from 4
    )
    
    hotel_agent = Agent(
        role="Hotel Specialist",
        goal="Find hotels within budget",
        backstory="Search hotels via Booking.com API. Get dest_id first, then search with dates. Return top 5.",
        verbose=False, allow_delegation=False, llm=llm_standard,
        tools=[search_hotels_comprehensive, search_hotel_destination, search_hotels_by_dest_id, 
               get_hotel_reviews, search_internet, calculate],
        max_iter=7  # Increased from 5
    )
    
    attr_agent = Agent(
        role="Attractions Specialist",
        goal="Find attractions matching interests",
        backstory="Find attractions and restaurants matching user interests. Provide details and costs.",
        verbose=False, allow_delegation=False, llm=llm_standard,
        tools=[search_attractions, search_restaurants, search_internet, calculate],
        max_iter=6  # Increased from 4
    )
    
    coord_agent = Agent(
        role="Itinerary Coordinator",
        goal="Create comprehensive day-by-day itinerary",
        backstory="Compile all info into complete itinerary with flights, hotels, daily activities, and budget.",
        verbose=False, allow_delegation=False, llm=llm_coordinator,
        tools=[calculate],
        max_iter=10  # Increased from 5 - most critical for output quality
    )
    
    return conv_agent, pref_agent, flight_agent, hotel_agent, attr_agent, coord_agent


def run_single_iteration(run_id: int, query: str, max_retries: int = 2):
    """Run a single iteration with retry logic for short outputs."""
    from tasks import TripPlannerTasks
    import re
    
    for attempt in range(max_retries):
        start_time = time.time()
        
        try:
            agents = create_improved_agents()
            tasks = TripPlannerTasks()
            cid = f"IMPROVED_RUN_{run_id}_{int(time.time())}"
            
            conv_agent, pref_agent, flight_agent, hotel_agent, attr_agent, coord_agent = agents
            
            t_conv = tasks.conversation_task(conv_agent, query, cid)
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
            
            output_text = str(result.raw if hasattr(result, 'raw') else result)
            
            # If output is too short, retry
            if len(output_text) < 1000 and attempt < max_retries - 1:
                print(f"   ⚠️ Short output ({len(output_text)} chars), retrying...")
                time.sleep(3)
                continue
            
            tokens = 0
            if hasattr(result, 'token_usage'):
                tokens = getattr(result.token_usage, 'total_tokens', 0)
            
            has_flights = 'flight' in output_text.lower()
            has_hotels = 'hotel' in output_text.lower()
            day_count = len(re.findall(r'(?:Day|DAY)\s*\d+', output_text))
            feasible = has_flights and has_hotels and day_count >= 1
            
            return {
                "run_id": run_id,
                "success": True,
                "feasible": feasible,
                "tokens": tokens,
                "latency": round(latency, 1),
                "output_length": len(output_text),
                "days_found": day_count,
                "attempts": attempt + 1
            }
            
        except Exception as e:
            latency = time.time() - start_time
            if attempt < max_retries - 1:
                print(f"   ⚠️ Error: {str(e)[:40]}, retrying...")
                time.sleep(5)
                continue
            return {
                "run_id": run_id,
                "success": False,
                "error": str(e),
                "latency": round(latency, 1),
                "attempts": attempt + 1
            }
    
    return {"run_id": run_id, "success": False, "error": "Max retries exceeded"}


def main():
    print("=" * 60)
    print("RUNNING 75 IMPROVED ITERATIONS (Runs 151-225)")
    print("Improvements: Higher max_iter, retry logic, 75 unique queries")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 60)
    
    results = {
        "runs": [],
        "summary": {},
        "timestamp": datetime.now().isoformat(),
        "total_runs": 75,
        "run_range": "151-225",
        "improvements": ["higher_max_iter", "retry_logic", "unique_queries"]
    }
    
    successful = 0
    feasible = 0
    total_tokens = 0
    total_latency = 0
    
    for i in range(75):
        run_id = 151 + i
        query = UNIQUE_QUERIES[i]  # Each run gets unique query
        print(f"\n[{i+1}/75] Run {run_id}...")
        print(f"   Query: {query[:60]}...")
        
        run_result = run_single_iteration(run_id, query)
        results["runs"].append(run_result)
        
        if run_result.get("success"):
            successful += 1
            total_latency += run_result.get("latency", 0)
            total_tokens += run_result.get("tokens", 0)
            if run_result.get("feasible"):
                feasible += 1
            print(f"   ✅ Tokens={run_result.get('tokens', 0):,} | Latency={run_result.get('latency', 0):.1f}s | Feasible={run_result.get('feasible')} | Attempts={run_result.get('attempts', 1)}")
        else:
            print(f"   ❌ FAILED - {run_result.get('error', 'Unknown')[:50]}")
        
        # Save incrementally
        with open("experiment_improved_151_225.json", "w", encoding='utf-8') as f:
            json.dump(results, f, indent=2)
    
    # Calculate summary
    results["summary"] = {
        "total_runs": 75,
        "successful": successful,
        "feasible": feasible,
        "success_rate": f"{(successful/75)*100:.1f}%",
        "feasibility_rate": f"{(feasible/successful)*100:.1f}%" if successful > 0 else "0%",
        "avg_tokens": round(total_tokens / successful) if successful > 0 else 0,
        "avg_latency": round(total_latency / successful, 1) if successful > 0 else 0,
        "total_tokens": total_tokens
    }
    
    with open("experiment_improved_151_225.json", "w", encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    
    print("\n" + "=" * 60)
    print("📊 IMPROVED BATCH COMPLETE (Runs 151-225)")
    print(f"Success: {successful}/75 ({results['summary']['success_rate']})")
    print(f"Feasible: {feasible}/{successful} ({results['summary']['feasibility_rate']})")
    print(f"Avg Tokens: {results['summary']['avg_tokens']:,}")
    print(f"Avg Latency: {results['summary']['avg_latency']}s")
    print(f"Results: experiment_improved_151_225.json")
    print("=" * 60)


if __name__ == "__main__":
    main()
