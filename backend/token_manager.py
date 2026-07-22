# backend/token_manager.py
from langchain_core.messages import trim_messages, BaseMessage
from typing import List, Tuple

def get_trimmed_messages(messages: List[BaseMessage], max_tokens: int = 1500) -> List[BaseMessage]:
    """
    Trims the message history to keep context within strict token budgets.
    Saves the system prompt and the most recent turns.
    """
    return trim_messages(
        messages,
        max_tokens=max_tokens,
        strategy="last",
        # Fast character heuristic (~4 chars per token) to avoid unnecessary API calls
        token_counter=lambda msgs: sum(len(m.content) // 4 for m in msgs),
        include_system=True,
        allow_partial=False,
        start_on="human",
    )

def calculate_token_savings(untrimmed_messages: List[BaseMessage], trimmed_messages: List[BaseMessage]) -> Tuple[int, int, float]:
    """
    Calculates estimated untrimmed baseline vs. actual trimmed input tokens.
    """
    # Estimate baseline input tokens if we sent everything
    baseline_tokens = sum(len(m.content) // 4 for m in untrimmed_messages)
    
    # Estimate actual tokens sent
    actual_tokens = sum(len(m.content) // 4 for m in trimmed_messages)
    
    # Calculate savings
    tokens_saved = max(0, baseline_tokens - actual_tokens)
    perc_saved = (tokens_saved / baseline_tokens * 100) if baseline_tokens > 0 else 0.0
    
    return actual_tokens, tokens_saved, round(perc_saved, 1)
