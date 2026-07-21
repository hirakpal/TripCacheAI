from __future__ import annotations

import hashlib
from typing import List, Dict, Any
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from langgraph_supervisor import create_supervisor
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore


# -----------------------------
# Simple in-memory "vector cache"
# -----------------------------

class CacheEntry(BaseModel):
    query: str
    query_embedding: List[float]
    result: Dict[str, Any]
    destination: str


class SimpleVectorCache:
    def __init__(self, similarity_threshold: float = 0.9):
        self.entries: List[CacheEntry] = []
        self.threshold = similarity_threshold

    def _embed(self, text: str) -> List[float]:
        h = hashlib.md5(text.encode()).digest()
        return list(h)

    def _cosine_sim(self, a: List[float], b: List[float]) -> float:
        dot = sum(x*y for x, y in zip(a, b))
        na = sum(x*x for x in a) ** 0.5
        nb = sum(x*x for x in b) ** 0.5
        if na == 0 or nb == 0:
            return 0.0
        return dot / (na * nb)

    def search(self, query: str, destination: str):
        emb = self._embed(f"{destination} {query}")
        best = None
        best_score = 0.0
        for e in self.entries:
            score = self._cosine_sim(emb, e.query_embedding)
            if score > best_score and score >= self.threshold:
                best_score = score
                best = e
        return best, best_score

    def store(self, query: str, result: Dict[str, Any], destination: str):
        emb = self._embed(f"{destination} {query}")
        self.entries.append(
            CacheEntry(
                query=query,
                query_embedding=emb,
                result=result,
                destination=destination,
            )
        )


cache = SimpleVectorCache()


# -----------------------------
# Shared state for supervisor
# -----------------------------

class TripState(BaseModel):
    destination: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    budget_range: str | None = None
    hotel_results: List[Dict[str, Any]] = Field(default_factory=list)
    draft_plan: Dict[str, Any] | None = None
    validation_errors: List[str] = Field(default_factory=list)
    approval_decision: str | None = None
    approval_feedback: str | None = None


# -----------------------------
# Tools
# -----------------------------

@tool
def search_hotels(
    destination: str,
    start_date: str,
    end_date: str,
    budget_range: str,
) -> Dict[str, Any]:
    """
    Search hotels for a destination, dates, and budget.
    Uses a simple cache first, then a fake live API call.
    """
    query = f"{destination} hotels from {start_date} to {end_date} budget {budget_range}"
    hit, score = cache.search(query, destination)
    if hit:
        return {"hotels": hit.result.get("hotels", []), "cache_hit": True}

    hotels = [
        {"name": "Hotel A", "price_per_night": 3000, "rating": 4.2},
        {"name": "Hotel B", "price_per_night": 5000, "rating": 4.6},
    ]
    result = {"hotels": hotels}
    cache.store(query, result, destination)
    return {"hotels": hotels, "cache_hit": False}


# -----------------------------
# Agents built with create_react_agent
# -----------------------------

model = ChatOpenAI(model="gpt-4o-mini", temperature=0)

front_desk_prompt = """
You are the front desk agent for a travel planner.

Goals:
- Collect destination, rough dates, and budget from the user.
- Ask one short question at a time.
- When destination, start_date, end_date, and budget_range are known,
  summarize them briefly and stop.
"""

front_desk_agent = create_react_agent(
    model=model,
    tools=[],
    name="front_desk",
    prompt=front_desk_prompt,
)


hotel_agent_prompt = """
You are a hotel search specialist.

Goals:
- Given destination, dates, and budget, use the search_hotels tool.
- Return a concise list of hotel options with price and rating.
- Do not build a full itinerary.
"""

hotel_agent = create_react_agent(
    model=model,
    tools=[search_hotels],
    name="hotel",
    prompt=hotel_agent_prompt,
)


planner_validator_prompt = """
You are a planner + validator.

Given:
- destination,
- dates,
- budget,
- hotel options,

Tasks:
- Create a very short draft plan (1–3 lines), picking 1–2 hotels.
- Check basic feasibility (dates are present, budget is plausible).
- If something seems off, add a brief validation error list.
"""

planner_validator_agent = create_react_agent(
    model=model,
    tools=[],
    name="planner_validator",
    prompt=planner_validator_prompt,
)


# -----------------------------
# Supervisor workflow
# -----------------------------

supervisor_prompt = """
You are the supervisor of a travel planning team.

Team members:
- front_desk: collects destination, dates, budget.
- hotel: searches hotels with the search_hotels tool.
- planner_validator: creates a draft plan and validates it.

Flow:
1. Use front_desk until destination, dates, and budget are clearly known.
2. Then use hotel to get hotel options.
3. Then use planner_validator to create a draft plan and validation.
Stop when a reasonable draft plan and validation have been produced.
"""

workflow = create_supervisor(
    [front_desk_agent, hotel_agent, planner_validator_agent],
    model=model,
    supervisor_name="supervisor",
    prompt=supervisor_prompt,
)


# -----------------------------
# Compile with memory
# -----------------------------

checkpointer = InMemorySaver()
store = InMemoryStore()

app = workflow.compile(checkpointer=checkpointer, store=store)
