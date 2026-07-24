import requests
import streamlit as st
from typing import Optional
from langchain_core.tools import tool

@tool
def search_hotels(
    location: str,
    budget: Optional[str] = "mid",
    check_in_date: Optional[str] = None,
    check_out_date: Optional[str] = None,
    purpose: Optional[str] = "leisure"
) -> str:
    """
    Search for real hotels in a location using Google Places API and return a ranked shortlist.
    
    Args:
        location: Target city or area (e.g., "Kolkata", "Park Street, Kolkata").
        budget: Budget description or tier (e.g., "low", "mid", "high", "5000 INR per night").
        check_in_date: Optional check-in date string (e.g., "2026-08-10").
        check_out_date: Optional check-out date string (e.g., "2026-08-15").
        purpose: Travel purpose or style (e.g., "family", "business", "couple", "solo").
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
            "places.userRatingCount,places.location,places.primaryType"
        ),
    }
    
    # Construct a natural text query for Google Places API
    query = f"best {budget} hotels for {purpose} trip in {location}"
    
    body = {
        "textQuery": query,
        "includedType": "lodging",
    }
    
    try:
        r = requests.post(url, headers=headers, json=body, timeout=20)
        r.raise_for_status()
        places = r.json().get("places", [])
        
        if not places:
            return f"No hotel results found for query '{query}'."
        
        # Weighted ranking score calculation
        def score(place):
            rating = place.get("rating", 0) or 0
            count = place.get("userRatingCount", 0) or 0
            return (rating * 10) + min(count / 100, 10)
            
        top_places = sorted(places, key=score, reverse=True)[:5]
        
        lines = []
        for p in top_places:
            name = p.get("displayName", {}).get("text", "Unknown Hotel")
            addr = p.get("formattedAddress", "Address N/A")
            rating = p.get("rating", "N/A")
            reviews = p.get("userRatingCount", "N/A")
            
            # Formatted line matching expected card parsing terms
            lines.append(f"Hotel Name: {name} | Location: {addr} | Price: {budget} | Rating: {rating} ({reviews} reviews)")
            
        return "\n".join(lines)
    
    except Exception as e:
        return f"An error occurred while searching Google Places: {str(e)}"
