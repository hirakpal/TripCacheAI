import requests
import streamlit as st
from langchain_core.tools import tool

@tool
def search_attractions(city: str, interests: str = "top tourist attractions") -> str:
    """Search for real activities, landmarks, and attractions in a city using Google Places."""
    
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
            "places.userRatingCount,places.primaryType"
        ),
    }
    
    body = {
        "textQuery": f"{interests} in {city}",
    }
    
    try:
        r = requests.post(url, headers=headers, json=body, timeout=20)
        r.raise_for_status()
        places = r.json().get("places", [])
        
        def score(place):
            rating = place.get("rating", 0) or 0
            count = place.get("userRatingCount", 0) or 0
            return (rating * 10) + min(count / 100, 10)
            
        top = sorted(places, key=score, reverse=True)[:8] # Grab up to 8 places for a full itinerary
        
        lines = []
        for p in top:
            name = p.get("displayName", {}).get("text", "Unknown")
            addr = p.get("formattedAddress", "N/A")
            rating = p.get("rating", "N/A")
            lines.append(f"{name} | {addr} | rating: {rating}")
            
        return "\n".join(lines) if lines else f"No attractions found in {city}."
    
    except Exception as e:
        return f"An error occurred while searching attractions: {str(e)}"
