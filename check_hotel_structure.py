"""
Check the actual structure of hotel search response
"""
import requests
import json

RAPIDAPI_KEY = "d2578842a2msha6c9e88223eefdcp159694jsn7129dba33a80"
headers = {
    'x-rapidapi-host': 'booking-com15.p.rapidapi.com',
    'x-rapidapi-key': RAPIDAPI_KEY
}

# Get Paris dest_id
url = "https://booking-com15.p.rapidapi.com/api/v1/hotels/searchDestination"
response = requests.get(url, headers=headers, params={'query': 'Paris'}, timeout=30)
dest_id = response.json()['data'][0]['dest_id']

# Search hotels
url = "https://booking-com15.p.rapidapi.com/api/v1/hotels/searchHotels"
params = {
    'dest_id': dest_id,
    'search_type': 'CITY',
    'arrival_date': '2025-12-15',
    'departure_date': '2025-12-18',
    'adults': '2',
    'room_qty': '1',
    'page_number': '1',
    'units': 'metric',
    'temperature_unit': 'c',
    'languagecode': 'en-us',
    'currency_code': 'USD'
}

response = requests.get(url, headers=headers, params=params, timeout=30)
data = response.json()

print("Hotel Response Structure:")
print("="*70)
print(json.dumps(data, indent=2))
