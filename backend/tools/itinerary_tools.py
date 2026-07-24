import requests
import streamlit as st
from typing import Optional, Union, List
from langchain_core.tools import tool

@tool
def search_attractions(
    destination: str,
    interests: Optional[Union[str, List[str]]] = "top tourist attractions",
    category: Optional[str] = None,
) -> str:
    """
    Search for real activities, landmarks, historical sites, and attractions in a city 
    using Google Places API v1 to support day-wise itinerary building.

    Args:
        destination: Target city or area (e.g., "Kolkata", "Old Delhi").
        interests: Specific interest terms, keywords, or list of preferences (e.g., "historical sites", "shopping", "food").
        category: Optional specific category filter (e.g., "museum", "park", "restaurant", "market").
    """
    # Fetch API Key safely from Streamlit secrets
    try:
        api_key = st.secrets["GOOGLE_PLACES_API_KEY"]
    except KeyError:
        return "Error: GOOGLE_PLACES_API_KEY is missing from Streamlit secrets."

    url = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": (
            "places.displayName,places.formattedAddress,places.rating,"
            "places.userRatingCount,places.primaryType,places.editorialSummary"
        ),
    }

    # Format interests if provided as a list
    if isinstance(interests, list):
        interests_str = ", ".join(interests)
    else:
        interests_str = interests or "top tourist attractions"

    # Build search query
    query_parts = [interests_str]
    if category:
        query_parts.append(category)
    query_parts.append(f"in {destination}")
    
    query = " ".join(query_parts)

    body = {
        "textQuery": query,
    }

    try:
        r = requests.post(url, headers=headers, json=body, timeout=20)
        r.raise_for_status()
        places = r.json().get("places", [])

        if not places:
            return f"No attraction results found for query '{query}'."

        # Weighted scoring based on ratings and review count
        def score(place):
            rating = place.get("rating", 0) or 0
            count = place.get("userRatingCount", 0) or 0
            return (rating * 10) + min(count / 100, 10)

        # Grab top 8 places for full multi-day planning
        top_places = sorted(places, key=score, reverse=True)[:8]

        lines = []
        for p in top_places:
            name = p.get("displayName", {}).get("text", "Unknown Landmark")
            addr = p.get("formattedAddress", "Address N/A")
            rating = p.get("rating", "N/A")
            reviews = p.get("userRatingCount", "N/A")
            p_type = p.get("primaryType", "attraction").replace("_", " ").title()

            lines.append(f"• Name: {name} | Type: {p_type} | Location: {addr} | Rating: {rating} ({reviews} reviews)")

        return "\n".join(lines)

    except Exception as e:
        return f"An error occurred while searching Google Places for attractions: {str(e)}"
