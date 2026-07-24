from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class AgentResponse(BaseModel):
    """Unified JSON response model for all TripCacheAI agents."""
    
    agent_name: str = Field(
        description="Name of the responding agent (e.g., traveler_profile_expert, itinerary_expert, hotel_expert)"
    )
    message: str = Field(
        description="The primary natural language response to display in chat or the itinerary pane"
    )
    suggestion_chips: List[str] = Field(
        default_factory=list,
        description="4 to 6 contextual suggestion strings for the frontend UI buttons"
    )
    profile_updates: Dict[str, Any] = Field(
        default_factory=dict,
        description="Extracted/updated traveler profile slots (destination, dates, budget, travelers, arrival_hub, sensitivities)"
    )
    profile_completeness: Optional[int] = Field(
        default=None,
        description="Estimated completion percentage (0-100) of mandatory trip context"
    )
    next_action: str = Field(
        default="CONTINUE",
        description="Routing signal: 'CONTINUE', 'PENDING_APPROVAL', 'HOTEL_EXPERT', or 'ITINERARY_EXPERT'"
    )
