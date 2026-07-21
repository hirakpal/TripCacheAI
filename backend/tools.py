from langchain_core.tools import tool

@tool
def search_hotels(location: str, budget: str, check_in_date: str, check_out_date: str) -> dict:
    """
    Searches for hotels based on location, budget, and dates.
    ALL parameters (location, budget, check_in_date, check_out_date) are mandatory.
    Dates must be provided in YYYY-MM-DD format.
    """
    
    # 1. The Mock Database
    mock_database = {
        "bengaluru": [
            {"name": "The Taj West End", "price_per_night": 15000, "currency": "INR", "rating": 4.8, "amenities": ["Pool", "Spa"]},
            {"name": "ITC Gardenia", "price_per_night": 12000, "currency": "INR", "rating": 4.7, "amenities": ["Eco-friendly", "Gym"]},
            {"name": "Holiday Inn Express", "price_per_night": 4000, "currency": "INR", "rating": 4.1, "amenities": ["Free WiFi", "Budget"]}
        ]
    }

    city_key = location.lower().strip()
    
    # 2. Fetch results (Mocking availability for the provided dates)
    results = mock_database.get(city_key, [
        {"name": f"The Grand {location} Plaza", "price_per_night": 8000, "currency": "INR", "rating": 4.2, "amenities": ["Pool", "WiFi"]}
    ])

    # 3. Return the payload, reflecting the requested dates back to the agent
    return {
        "search_parameters": {
            "location": location,
            "check_in": check_in_date,
            "check_out": check_out_date,
            "budget": budget
        },
        "available_hotels": results
    }
