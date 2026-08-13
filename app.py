"""
Content Summarizer & Analyzer App
Streamlit Main Application File
"""

import os
import streamlit as st
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Import project modules
from modules.extractor import fetch_and_clean_url
from modules.summarizer import generate_summary, PROMPT_STRATEGIES, build_summary_prompt
from modules.analyzer import analyze_content
from utils.cost_tracker import render_cost_sidebar_widget, init_session_cost_tracker

# Page Configuration
st.set_page_config(
    page_title="Content Summarizer & Analyzer",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Modern Design Aesthetics
CUSTOM_CSS = """
<style>
    /* Metric Card styling */
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 15px;
        border-left: 4px solid #1E88E5;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        margin-bottom: 15px;
    }
    /* Badge styling */
    .badge-positive {
        background-color: #E8F5E9;
        color: #2E7D32;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: bold;
        display: inline-block;
    }
    .badge-negative {
        background-color: #FFEBEE;
        color: #C62828;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: bold;
        display: inline-block;
    }
    .badge-neutral {
        background-color: #E3F2FD;
        color: #1565C0;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: bold;
        display: inline-block;
    }
    .theme-tag {
        background-color: #F1F3F4;
        color: #3C4043;
        padding: 6px 14px;
        border-radius: 16px;
        font-size: 0.9em;
        margin-right: 6px;
        margin-bottom: 6px;
        display: inline-block;
        border: 1px solid #DADCE0;
    }
    .action-item {
        background-color: #FFF8E1;
        border-left: 4px solid #FFA000;
        padding: 10px 15px;
        margin-bottom: 8px;
        border-radius: 4px;
    }
    .prompt-box {
        background-color: #262730;
        color: #F0F2F6;
        padding: 12px;
        border-radius: 6px;
        font-family: monospace;
        font-size: 0.85em;
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# Sample Preset Datasets for quick testing
SAMPLE_TEXTS = {
    "📰 Tech News Article": (
        "Google has officially introduced Gemini 2.5 Flash, its latest multimodal artificial intelligence model "
        "designed for high-efficiency, long-context reasoning tasks. The new model boasts a 1-million token context window, "
        "enabling developers to process massive documents, codebases, and audio streams seamlessly. Additionally, Google AI Studio "
        "offers a generous free tier allowing developers to execute up to 15 requests per minute without incurring any charges or requiring "
        "a credit card. Industry analysts highlight that Gemini 2.5 Flash drastically lowers latency while preserving benchmark reasoning accuracy, "
        "making it a strong competitor in the GenAI ecosystem for real-time applications."
    ),
    "📋 Team Meeting Minutes": (
        "Q3 Product Planning Sync Notes (August 12, 2026)\n"
        "Attendees: Sarah (PM), David (Lead Dev), Priya (UX), Alex (QA)\n\n"
        "Discussion Points:\n"
        "- David reported that the database migration is 90% complete but requires 2 additional days for stress testing.\n"
        "- Priya presented the new dashboard wireframes. User feedback on navigation was highly positive.\n"
        "- Alex noted that automated end-to-end test coverage for authentication stands at 85%.\n\n"
        "Action Items:\n"
        "1. David to complete load testing by Friday end of day.\n"
        "2. Priya to finalize micro-interaction design tokens for the design system by Wednesday.\n"
        "3. Sarah to schedule client demo meeting for next Tuesday at 10 AM.\n"
        "4. Alex to log authentication edge cases in Jira by Thursday morning."
    ),
    "✉️ Customer Support Escalation": (
        "Subject: URGENT: Payment Gateway Timeout Issue - Account #88492\n\n"
        "Dear Support Team,\n"
        "Our team has experienced repeated transaction timeouts on our production checkout page since 9:00 AM EST today. "
        "Over 45 customer checkouts have failed, resulting in customer frustration and an estimated loss of $12,000 in revenue. "
        "We checked our server logs and confirmed the gateway responds with HTTP 504 Gateway Timeout. "
        "Please escalate this immediately to your infrastructure engineering team and provide an ETA for resolution. "
        "We require a formal incident report once the service is restored."
    )
}

def main():
    init_session_cost_tracker()

    # Sidebar Settings & Configuration
    st.sidebar.title("⚙️ App Settings")
    
    # API Key Input handling
    env_api_key = os.getenv("GEMINI_API_KEY", "")
    api_key = st.sidebar.text_input(
        "Google Gemini API Key",
        value=env_api_key,
        type="password",
        help="Get your free key at https://aistudio.google.com/"
    )

    if not api_key:
        st.sidebar.warning("⚠️ No API Key found! Get a free key at [Google AI Studio](https://aistudio.google.com/) and enter it above.")

    # Model Selection
    model_choice = st.sidebar.selectbox(
        "Gemini Model",
        options=["gemini-1.5-flash", "gemini-2.0-flash", "gemini-1.5-pro"],
        index=0,
        help="gemini-1.5-flash is the primary, high-performance model on Google AI Studio's Free Tier."
    )

    # Temperature Control
    temperature = st.sidebar.slider(
        "Creativity (Temperature)",
        min_value=0.0,
        max_value=1.0,
        value=0.3,
        step=0.1,
        help="Lower values (0.1-0.3) produce factual, deterministic output. Higher values foster creativity."
    )

    # Render Live Token Usage Sidebar Widget
    render_cost_sidebar_widget()

    # Main Application Header
    st.title("🤖 GenAI Content Summarizer & Analyzer")
    st.caption("Powered by Google Gemini API • Free Tier • Instant Text & Web Extraction")

    # Input Section with Dual Tabs
    st.markdown("### 📥 1. Select Content Source")
    
    input_tab1, input_tab2 = st.tabs(["📝 Direct Text Input", "🌐 Extract from Web URL"])

    raw_input_text = ""
    extracted_title = ""

    with input_tab1:
        # Sample Quick Loader Buttons
        st.write("**Quick Test Samples:**")
        cols = st.columns(len(SAMPLE_TEXTS))
        selected_sample = None
        for i, (sample_name, sample_content) in enumerate(SAMPLE_TEXTS.items()):
            if cols[i].button(sample_name, use_container_width=True):
                selected_sample = sample_content
        
        default_area_value = selected_sample if selected_sample else ""
        raw_input_text = st.text_area(
            "Paste your text content below (article, meeting notes, email, report):",
            value=default_area_value,
            height=200,
            placeholder="Type or paste long text here..."
        )

    with input_tab2:
        url_input = st.text_input(
            "Enter Webpage URL:",
            placeholder="https://example.com/blog-post"
        )
        if st.button("🌐 Fetch & Clean Webpage Text"):
            if not url_input:
                st.error("Please enter a valid URL.")
            else:
                with st.spinner("Scraping and cleaning webpage content..."):
                    try:
                        extracted_title, extracted_text, word_count = fetch_and_clean_url(url_input)
                        st.session_state["extracted_text"] = extracted_text
                        st.session_state["extracted_title"] = extracted_title
                        st.success(f"Successfully extracted {word_count} words from **{extracted_title}**!")
                    except Exception as e:
                        st.error(f"Scraping Error: {str(e)}")

        if "extracted_text" in st.session_state:
            raw_input_text = st.session_state["extracted_text"]
            st.text_area("Extracted Web Content:", value=raw_input_text, height=180)

    # Calculate Word Count for Input Text
    text_to_process = raw_input_text.strip()
    input_word_count = len(text_to_process.split()) if text_to_process else 0

    if input_word_count > 0:
        st.info(f"📊 **Content Ready:** {input_word_count:,} words loaded for analysis.")
    else:
        st.info("💡 **Tip:** Paste text above or select one of the Quick Test Samples to start.")

    st.markdown("---")
    st.markdown("### 🎯 2. Summarization & Intelligence Capabilities")

    # Main Application Output Tabs
    tab_summary, tab_analysis, tab_prompt_lab, tab_learnings = st.tabs([
        "📄 Summarizer",
        "📊 Deep Analysis",
        "🔬 Prompt Lab (V1 vs V2 vs V3)",
        "💡 Project Learnings"
    ])

    # ---------------------------------------------------------
    # TAB 1: SUMMARIZER
    # ---------------------------------------------------------
    with tab_summary:
        st.subheader("Generate Custom Text Summary")
        
        col_style, col_ver = st.columns(2)
        with col_style:
            summary_style = st.radio(
                "Summary Style:",
                options=["TL;DR", "Concise", "Detailed"],
                index=1,
                horizontal=True,
                help="TL;DR (1-2 sentences), Concise (bullet points), Detailed (multi-section breakdown)"
            )
        with col_ver:
            prompt_version = st.selectbox(
                "Prompt Quality Strategy:",
                options=["V3", "V2", "V1"],
                format_func=lambda x: f"{x} - {PROMPT_STRATEGIES[x]['name']}",
                index=0,
                help="V3 uses professional system persona, V2 uses basic constraints, V1 uses standard raw prompt."
            )

        if st.button("⚡ Generate Summary", type="primary", use_container_width=True):
            if not api_key:
                st.error("Please provide your Google Gemini API Key in the sidebar.")
            elif not text_to_process:
                st.warning("Please provide input text or load a sample first.")
            else:
                with st.spinner(f"Generating {summary_style} summary with Gemini ({prompt_version})..."):
                    try:
                        summary, usage = generate_summary(
                            api_key=api_key,
                            text=text_to_process,
                            style=summary_style,
                            prompt_version=prompt_version,
                            model_name=model_choice,
                            temperature=temperature
                        )
                        st.markdown("#### 📝 Summary Result")
                        st.markdown(summary)
                        
                        out_words = len(summary.split())
                        st.caption(f"⏱️ Compression Ratio: Reduced {input_word_count} words down to {out_words} words.")
                    except Exception as e:
                        st.error(f"Error generating summary: {str(e)}")

    # ---------------------------------------------------------
    # TAB 2: DEEP ANALYSIS (Structured Output)
    # ---------------------------------------------------------
    with tab_analysis:
        st.subheader("Structured NLP Content Analysis")
        st.caption("Uses Gemini's `response_schema` mode to strictly enforce JSON output structure.")

        if st.button("🔍 Run Deep Analysis", type="primary", use_container_width=True):
            if not api_key:
                st.error("Please provide your Google Gemini API Key in the sidebar.")
            elif not text_to_process:
                st.warning("Please provide input text or load a sample first.")
            else:
                with st.spinner("Extracting sentiment, key themes, and action items via Gemini JSON Schema..."):
                    try:
                        result, usage = analyze_content(
                            api_key=api_key,
                            text=text_to_process,
                            model_name=model_choice,
                            temperature=temperature
                        )
                        st.session_state["analysis_result"] = result
                    except Exception as e:
                        st.error(f"Error running content analysis: {str(e)}")

        if "analysis_result" in st.session_state:
            res = st.session_state["analysis_result"]
            
            # Row 1: Sentiment & Target Audience Cards
            col_sent, col_aud = st.columns(2)
            
            with col_sent:
                st.markdown("#### 🎭 Sentiment Analysis")
                sentiment = res.get("sentiment", "Neutral")
                score = res.get("sentiment_score", 0.0)
                reasoning = res.get("sentiment_reasoning", "")
                
                badge_class = (
                    "badge-positive" if sentiment == "Positive"
                    else "badge-negative" if sentiment == "Negative"
                    else "badge-neutral"
                )
                
                st.markdown(f'<span class="{badge_class}">{sentiment.upper()} (Score: {score:+.2f})</span>', unsafe_allow_html=True)
                st.write(f"**Justification:** {reasoning}")
                st.progress(max(0.0, min(1.0, (score + 1.0) / 2.0)))

            with col_aud:
                st.markdown("#### 🎯 Target Audience")
                st.info(f"**Identified Readers:** {res.get('target_audience', 'General Public')}")

            st.markdown("---")

            # Row 2: Key Themes & Action Items
            col_themes, col_actions = st.columns(2)

            with col_themes:
                st.markdown("#### 🏷️ Key Themes & Topics")
                themes = res.get("themes", [])
                if themes:
                    html_tags = "".join([f'<span class="theme-tag">#{theme}</span>' for theme in themes])
                    st.markdown(html_tags, unsafe_allow_html=True)
                else:
                    st.write("No distinct key themes extracted.")

            with col_actions:
                st.markdown("#### ✅ Extracted Action Items")
                actions = res.get("action_items", [])
                if actions:
                    for item in actions:
                        st.markdown(f'<div class="action-item">📌 {item}</div>', unsafe_allow_html=True)
                else:
                    st.write("🟢 *No explicit action items or pending tasks found in this content.*")

            # Display JSON Output Inspection
            with st.expander("📦 View Raw Gemini JSON Output", expanded=False):
                st.json(res)

    # ---------------------------------------------------------
    # TAB 3: PROMPT LAB (V1 vs V2 vs V3)
    # ---------------------------------------------------------
    with tab_prompt_lab:
        st.subheader("🔬 Prompt Engineering Evolution & Comparison Lab")
        st.markdown(
            "Demonstrating the progression of prompt quality from basic unconstrained prompts (V1) "
            "to simple constrained prompts (V2), and production-ready system role-playing prompts (V3)."
        )

        # Show prompt templates side-by-side
        with st.expander("📖 View Strategy Prompt Templates", expanded=True):
            p1, p2, p3 = st.columns(3)
            with p1:
                st.markdown("### V1 (Basic)")
                st.caption(PROMPT_STRATEGIES["V1"]["description"])
                st.code(PROMPT_STRATEGIES["V1"]["template"], language="text")
            with p2:
                st.markdown("### V2 (Structured)")
                st.caption(PROMPT_STRATEGIES["V2"]["description"])
                st.code(PROMPT_STRATEGIES["V2"]["template"], language="text")
            with p3:
                st.markdown("### V3 (Professional)")
                st.caption(PROMPT_STRATEGIES["V3"]["description"])
                st.code(PROMPT_STRATEGIES["V3"]["styles"]["Concise"], language="text")

        if st.button("⚡ Run Side-by-Side Prompt Comparison", type="secondary", use_container_width=True):
            if not api_key:
                st.error("Please enter your Google Gemini API Key in the sidebar.")
            elif not text_to_process:
                st.warning("Please provide input text or load a sample first.")
            else:
                st.markdown("### 📊 Side-by-Side Output Comparison")
                comp_cols = st.columns(3)
                
                for idx, ver in enumerate(["V1", "V2", "V3"]):
                    with comp_cols[idx]:
                        st.markdown(f"#### {PROMPT_STRATEGIES[ver]['name']}")
                        with st.spinner(f"Running {ver}..."):
                            try:
                                sum_out, _ = generate_summary(
                                    api_key=api_key,
                                    text=text_to_process,
                                    style="Concise",
                                    prompt_version=ver,
                                    model_name=model_choice,
                                    temperature=temperature
                                )
                                st.markdown(sum_out)
                            except Exception as e:
                                st.error(f"Error ({ver}): {str(e)}")

    # ---------------------------------------------------------
    # TAB 4: PROJECT LEARNINGS
    # ---------------------------------------------------------
    with tab_learnings:
        st.subheader("🎓 GenAI Internship Learnings & Architecture Overview")
        
        st.markdown("""
        ### Key Technical Takeaways:

        1. **Google Gemini Free Tier Advantages**:
           - **15 Requests / Minute & 1,500 Requests / Day**: Enables full prototyping without cost barriers.
           - **1 Million Token Context Window**: Allows analyzing entire reports or articles in a single prompt.
           - **Zero Credit Card Setup**: Accessible directly via Google AI Studio API key.

        2. **Structured Outputs (`response_schema`)**:
           - Using Pydantic models with `response_mime_type="application/json"` guarantees deterministic JSON keys.
           - Prevents JSON parsing failures in production downstreams (sentiment, action items, themes).

        3. **Prompt Engineering Taxonomy**:
           - **V1 (Naive)**: Produces unformatted text, prone to variable length and hallucination.
           - **V2 (Constrained)**: Adds simple length rules but lacks structural formatting controls.
           - **V3 (Production)**: Uses explicit personas, negative constraints, bold keyword formatting, and clear input boundaries.

        4. **Clean Web Extraction**:
           - Using `BeautifulSoup` to decompose non-content elements (`<script>`, `<style>`, `<nav>`, `<footer>`) ensures high-density text input, minimizing token burn.
        """)

if __name__ == "__main__":
    main()
