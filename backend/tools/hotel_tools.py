import requests
import streamlit as st
from typing import Literal
from langchain_core.tools import tool

@tool
def search_hotels(
    city: str,
    budget: Literal["low", "mid", "high"] = "mid",
    purpose: Literal["business", "family", "couple", "solo"] = "business",
) -> str:
    """Search for real hotels in a city using Google Places and return a ranked shortlist."""
    
    # Fetch from Streamlit secrets safely
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
    
    body = {
        "textQuery": f"best {budget} budget hotels for {purpose} trip in {city}",
        "includedType": "lodging",
    }
    
    try:
        r = requests.post(url, headers=headers, json=body, timeout=20)
        r.raise_for_status()
        places = r.json().get("places", [])
        
        def score(place):
            rating = place.get("rating", 0) or 0
            count = place.get("userRatingCount", 0) or 0
            return (rating * 10) + min(count / 100, 10)
            
        top = sorted(places, key=score, reverse=True)[:5]
        
        lines = []
        for p in top:
            name = p.get("displayName", {}).get("text", "Unknown")
            addr = p.get("formattedAddress", "N/A")
            rating = p.get("rating", "N/A")
            reviews = p.get("userRatingCount", "N/A")
            lines.append(f"{name} | {addr} | rating {rating} | reviews {reviews}")
            
        return "\n".join(lines) if lines else f"No hotel results found in {city}."
    
    except Exception as e:
        return f"An error occurred while searching: {str(e)}"