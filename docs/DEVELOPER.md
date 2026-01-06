# Developer Guide

Technical documentation for Trip Planner development and extension.

## Architecture Overview

```
User Input → Conversational Agent → Preferences Extractor
                                           ↓
              ┌─────────────────┬─────────────────┐
              ↓                 ↓                 ↓
       Flight Agent      Hotel Agent      Attraction Agent
              ↓                 ↓                 ↓
              └─────────────────┴─────────────────┘
                                ↓
                    Itinerary Coordinator → Output
```

## Adding New Agents

1. **Define agent card** in `agent_cards.py`
2. **Create agent method** in `agents.py`
3. **Create task method** in `tasks.py`
4. **Register in workflow** in `main.py`

## Adding New Tools

1. **Create tool function** in `tools/` directory
2. **Register with `@tool` decorator**
3. **Add to agent's tools list** in `agents.py`

## Utility Modules

### api_resilience.py
```python
from utils.api_resilience import retry_with_backoff, FallbackChain

@retry_with_backoff(max_retries=3, exceptions=(RequestException,))
def call_api():
    ...

chain = FallbackChain(primary_api, backup_api, cached_data)
result = chain.execute(params)
```

### cache_manager.py
```python
from utils.cache_manager import get_cache

cache = get_cache(ttl_seconds=3600)
result = cache.get("flights", {"origin": "NYC"})
if result is None:
    result = api_call()
    cache.set("flights", {"origin": "NYC"}, result)
```

### itinerary_validator.py
```python
from utils.itinerary_validator import validate_day_count

is_valid, count, days = validate_day_count(itinerary, expected_days=7)
```

## Running Tests

```bash
python -m pytest tests/ -v
```

## Token Optimization Tips

1. Keep agent backstories under 200 words
2. Request "top 3-5 options" not "all options"
3. Use structured outputs (tables, JSON)
4. Cache repeated queries
