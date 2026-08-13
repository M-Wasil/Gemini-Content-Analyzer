"""
Cost & Token Usage Tracker Utility
Tracks Gemini API token usage per request and session-wide, providing cost estimations.
"""

import streamlit as st

# Baseline commercial rates per million tokens (for Gemini Flash models)
COMMERCIAL_RATES = {
    "gemini-2.0-flash": {"input_per_m": 0.075, "output_per_m": 0.30},
    "gemini-1.5-flash": {"input_per_m": 0.075, "output_per_m": 0.30},
    "gemini-1.5-pro": {"input_per_m": 1.25, "output_per_m": 5.00},
    "default": {"input_per_m": 0.075, "output_per_m": 0.30},
}

def init_session_cost_tracker():
    """Initializes session state counters for total API requests and token metrics."""
    if "total_prompt_tokens" not in st.session_state:
        st.session_state.total_prompt_tokens = 0
    if "total_completion_tokens" not in st.session_state:
        st.session_state.total_completion_tokens = 0
    if "total_requests" not in st.session_state:
        st.session_state.total_requests = 0
    if "last_request_usage" not in st.session_state:
        st.session_state.last_request_usage = None

def record_token_usage(usage_metadata, model_name: str = "gemini-1.5-flash") -> dict:
    """
    Parses usage metadata from Gemini response object and updates session statistics.

    Args:
        usage_metadata: Response usage metadata object from google.generativeai
        model_name (str): The model used for generation.

    Returns:
        dict: Detailed breakdown of current request token usage and estimated cost.
    """
    init_session_cost_tracker()

    prompt_tokens = 0
    completion_tokens = 0
    total_tokens = 0

    if usage_metadata:
        prompt_tokens = getattr(usage_metadata, "prompt_token_count", 0) or 0
        completion_tokens = getattr(usage_metadata, "candidates_token_count", 0) or 0
        total_tokens = getattr(usage_metadata, "total_token_count", 0) or (prompt_tokens + completion_tokens)

    # Update session counters
    st.session_state.total_prompt_tokens += prompt_tokens
    st.session_state.total_completion_tokens += completion_tokens
    st.session_state.total_requests += 1

    rates = COMMERCIAL_RATES.get(model_name.lower(), COMMERCIAL_RATES["default"])
    estimated_commercial_cost = (
        (prompt_tokens / 1_000_000) * rates["input_per_m"]
        + (completion_tokens / 1_000_000) * rates["output_per_m"]
    )

    request_summary = {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "actual_cost": 0.00,  # Free Tier
        "estimated_commercial_cost": estimated_commercial_cost,
        "model": model_name,
    }

    st.session_state.last_request_usage = request_summary
    return request_summary

def render_cost_sidebar_widget():
    """Renders a sleek token usage metric widget in the Streamlit sidebar."""
    init_session_cost_tracker()

    st.sidebar.markdown("---")
    st.sidebar.subheader("⚡ API Token & Cost Tracker")
    st.sidebar.caption("Google Gemini Free Tier Active (15 RPM / 1,500 RPD)")

    req_count = st.session_state.total_requests
    p_tokens = st.session_state.total_prompt_tokens
    c_tokens = st.session_state.total_completion_tokens
    tot_tokens = p_tokens + c_tokens

    # Session summary metrics
    col1, col2 = st.sidebar.columns(2)
    col1.metric("Requests", req_count)
    col2.metric("Total Tokens", f"{tot_tokens:,}")

    if st.session_state.last_request_usage:
        last = st.session_state.last_request_usage
        with st.sidebar.expander("🔍 Last Request Breakdown", expanded=False):
            st.write(f"**Model:** `{last['model']}`")
            st.write(f"**Prompt Tokens:** {last['prompt_tokens']}")
            st.write(f"**Output Tokens:** {last['completion_tokens']}")
            st.write(f"**Total Tokens:** {last['total_tokens']}")
            st.write(f"**Actual Cost:** `$0.00` (Free Tier)")
            st.caption(f"Commercial Value: ~${last['estimated_commercial_cost']:.6f}")
