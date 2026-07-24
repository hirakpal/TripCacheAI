from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AgentStatus(str, Enum):
    SUCCESS = "SUCCESS"
    NEED_MORE_INFO = "NEED_MORE_INFO"
    ERROR = "ERROR"


class NextAction(str, Enum):
    WAIT_FOR_USER = "WAIT_FOR_USER"  # Render UI message & wait for user input
    CALL_AGENT = "CALL_AGENT"        # Auto-handoff to next_agent in graph
    COMPLETE = "COMPLETE"            # Trip workflow finalized


class AgentResponse(BaseModel):
    agent_name: str = Field(
        description="Name of the responding agent (e.g., traveler_profile_expert, itinerary_expert)"
    )
    status: AgentStatus = Field(
        default=AgentStatus.SUCCESS,
        description="Execution status of the agent turn"
    )
    next_action: NextAction = Field(
        description="Control flow signal for LangGraph supervisor"
    )
    next_agent: Optional[str] = Field(
        default=None,
        description="Target node name if next_action is CALL_AGENT"
    )
    message: str = Field(
        description="Natural language response text to display in chat or UI"
    )
    suggestions: List[str] = Field(
        default_factory=list,
        description="4 to 6 contextual suggestion strings for Streamlit UI buttons"
    )
    confidence: float = Field(
        default=1.0,
        description="Model confidence level (0.0 to 1.0) for extraction/reasoning"
    )
    requires_human: bool = Field(
        default=False,
        description="Triggers Human-In-The-Loop approval state in UI"
    )
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Flexible payload container for agent-specific state updates"
    )
