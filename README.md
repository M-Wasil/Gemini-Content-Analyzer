# 🤖 GenAI Content Summarizer & Analyzer

> A Streamlit-based GenAI application for intelligent content summarization, structured NLP analysis, and prompt engineering experimentation, powered by the Google Gemini API.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-App-FF4B4B?logo=streamlit&logoColor=white)
![Google Gemini](https://img.shields.io/badge/Google-Gemini%20API-4285F4?logo=google&logoColor=white)
![Pydantic](https://img.shields.io/badge/Pydantic-Structured%20Output-E92063?logo=pydantic&logoColor=white)

---

## Application Preview

```text
<!-- Add screenshots/GIF here -->
```

The application is organized around a single-page Streamlit layout:

- **Sidebar Configuration** — Gemini API key input, model selector, temperature slider, and a live token/cost tracker.
- **Content Input** — paste text directly (with three one-click sample datasets: a tech news article, meeting minutes, and a customer support escalation) or extract content from a live web URL.
- **📄 Summarizer** — generate a summary in a chosen style using a chosen prompt strategy.
- **📊 Deep Analysis** — run structured sentiment, theme, and action-item extraction on the loaded content.
- **🔬 Prompt Lab** — view the actual V1/V2/V3 prompt templates and run them side-by-side on the same input.
- **💡 Project Learnings** — a write-up of the engineering takeaways behind the build.

---

## Key Features

### 📝 Multi-Style Summarization

Three summary styles are available for any prompt version:

- **TL;DR** — a 1–2 sentence core takeaway, no introductory fluff.
- **Concise** — 3–5 structured bullet points with bolded leading keywords.
- **Detailed** — a multi-section breakdown (Executive Summary / Key Findings / Implications & Next Steps).

### 🔬 Prompt Engineering Evolution

The **Prompt Lab** tab lets you run the same input text through three increasingly sophisticated prompt strategies and compare the outputs side-by-side:

| Version | Name | Description |
|---|---|---|
| **V1** | Basic Raw | A single-line instruction with no constraints or structure. |
| **V2** | Basic Constrained | Adds a simple output constraint ("summarize in 3 bullet points"). |
| **V3** | Professional System-Role | Assigns an explicit persona per style, adds formatting rules, anti-hallucination constraints, and style-specific structural guidance. |

This is a qualitative, side-by-side comparison of prompt design choices — not an automated or quantitative benchmarking system.

---

## 🔬 Structured Deep Analysis

The **Deep Analysis** tab uses a Pydantic model, `ContentAnalysis`, to force Gemini into returning a strictly-typed JSON object:

| Field | Type | Description |
|---|---|---|
| `sentiment` | `str` | One of `"Positive"`, `"Negative"`, or `"Neutral"`. |
| `sentiment_score` | `float` | Sentiment intensity, ranging from `-1.0` (very negative) to `1.0` (very positive). |
| `sentiment_reasoning` | `str` | A brief, one-sentence justification for the assigned sentiment. |
| `themes` | `List[str]` | The top 3–5 core topics or subjects covered in the text. |
| `action_items` | `List[str]` | Explicit or implied tasks, follow-ups, or decisions. Empty list if none exist. |
| `target_audience` | `str` | The likely intended readers or domain audience for the content. |

Structured generation is enforced by configuring the Gemini request with:

- `response_mime_type="application/json"`
- `response_schema=ContentAnalysis` (the Pydantic model passed directly to the Gemini SDK)

The raw JSON response is then parsed and normalized with safe defaults before being rendered in the UI, and the full raw object is viewable via a "View Raw Gemini JSON Output" expander.

### Example Output

Tested against a Technology Review article ([`technologyreview.com/.../knowledge-graph-ai-reads-web...`](https://www.technologyreview.com/2020/09/04/1008156/knowledge-graph-ai-reads-web-machine-learning-natural-language-processing/)), the app extracted the article and produced structured analysis similar to:

```json
{
  "sentiment": "Neutral",
  "sentiment_score": 0.1,
  "sentiment_reasoning": "The text provides an objective, journalistic overview of the differences between large language models and knowledge graphs, specifically focusing on Diffbot's approach to factual accuracy.",
  "themes": [
    "Artificial Intelligence and LLMs",
    "Knowledge Graphs vs. Language Models",
    "Automated Data Extraction",
    "Diffbot's Business Model",
    "Factual Accuracy in AI"
  ],
  "action_items": [],
  "target_audience": "Tech-savvy readers and professionals interested in AI, machine learning, and data extraction."
}
```

*(Presented as a representative example — actual output will vary by model, prompt version, and content.)*

This demonstrates schema-constrained generation, topic extraction, sentiment classification, audience identification, and machine-readable JSON output suitable for downstream consumption.

---

## 🌐 Web URL Extraction

Implemented in `modules/extractor.py`, the extraction pipeline:

1. Accepts a URL (auto-prepends `https://` if no scheme is given).
2. Fetches the page with `requests`, using a browser-like `User-Agent` header.
3. Parses the HTML with `BeautifulSoup`.
4. Removes non-content elements: `script`, `style`, `nav`, `header`, `footer`, `aside`, `form`, `iframe`, and elements matching common ad/cookie/sidebar class-name patterns.
5. Looks for a primary content container (`<article>`, `<main>`, `role="main"`, or an id containing `content`/`main`/`article`), falling back to `<body>`.
6. Pulls text from headers, paragraphs, and list items within that container (falling back to raw text extraction if block-based extraction yields nothing).
7. Extracts the page title from `<title>` or the first `<h1>`.
8. Cleans up whitespace and calculates a word count.

If the cleaned text comes out to fewer than 15 words, a `ValueError` is raised rather than returning near-empty content. HTTP errors, timeouts, invalid URL schemes, and non-HTML content types are also explicitly caught and surfaced as readable error messages in the UI.

### ⚠️ Known Web Scraping Limitation

This is a real, observed limitation and is documented here intentionally.

Testing against `https://en.wikipedia.org/wiki/Pakistan` currently returns:

> *Scraping Error: Could not extract meaningful text from this URL. The page may require JavaScript or authentication.*

The extractor is built on **static HTTP fetching + BeautifulSoup HTML parsing** — it does not execute JavaScript or render a real browser DOM. As a result, extraction can fail when:

- Content is rendered client-side via JavaScript.
- Meaningful content loads asynchronously after the initial HTML response.
- The site has anti-bot protections.
- The page's structure doesn't match the extractor's content-selection heuristics.
- Authentication is required to view the content.

**The URL extraction feature works well for many statically-accessible pages (e.g. blog posts, news articles, documentation) but is not guaranteed to support every modern website.** Possible future improvements include browser-based rendering (Playwright/Selenium) and more sophisticated, site-aware content extraction — see [Future Improvements](#-future-improvements).

---

## Architecture

```text
                    ┌─────────────────────┐
                    │     Streamlit UI    │
                    │       app.py        │
                    └──────────┬──────────┘
                               │
             ┌─────────────────┴─────────────────┐
             │                                   │
             ▼                                   ▼
     Direct Text Input                    Web URL Input
             │                                   │
             │                                   ▼
             │                         URL Extractor
             │                    requests + BeautifulSoup
             │                                   │
             └─────────────────┬─────────────────┘
                               ▼
                        Clean Text Content
                               │
                 ┌─────────────┴─────────────┐
                 │                           │
                 ▼                           ▼
          Summarization                Deep Analysis
       (V1 / V2 / V3 prompts)      (response_schema JSON)
                 │                           │
                 ▼                           ▼
        Gemini Generation          Gemini Structured JSON
           (with model                       │
            fallback)                        ▼
                 │                     Pydantic Validation
                 │                           │
                 └─────────────┬─────────────┘
                               ▼
                       Streamlit Presentation
                               │
                               ▼
                     Token / Cost Tracking
                    (utils/cost_tracker.py)
```

---

## Project Structure

```text
content-analyzer/
│
├── app.py                   # Main Streamlit application and UI orchestration
├── requirements.txt
├── .env.example
│
├── modules/
│   ├── __init__.py
│   ├── extractor.py         # URL fetching, HTML parsing, cleaning, extraction
│   ├── summarizer.py        # Prompt strategies, summary generation, model fallback
│   └── analyzer.py          # Structured content analysis (Pydantic + Gemini JSON mode)
│
└── utils/
    ├── __init__.py
    └── cost_tracker.py      # Token usage accounting and estimated cost calculation
```

---

## Technology Stack

| Technology | Role |
|---|---|
| **Python** | Core application language |
| **Streamlit** | Web UI framework and app runtime |
| **Google Gemini API** (`google-generativeai`) | LLM backend for summarization and structured analysis |
| **Pydantic** | Schema definition and validation for structured Gemini output |
| **BeautifulSoup4** | HTML parsing for web content extraction |
| **Requests** | HTTP fetching for URL-based content input |
| **python-dotenv** | Loads `GEMINI_API_KEY` from a local `.env` file |

---

## Environment Setup

### Clone the repository

```bash
git clone <your-repository-url>
cd content-analyzer
```

### Create a virtual environment

```bash
python -m venv .venv
```

Activate it:

```bash
# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### Install dependencies

```bash
pip install -r requirements.txt
```

### Configure your Gemini API key

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Then edit `.env` and add your key:

```env
GEMINI_API_KEY=your_gemini_api_key_here
```

Get a free key from [Google AI Studio](https://aistudio.google.com/). You can also paste the key directly into the sidebar at runtime instead of using `.env`.

---

## Running the Application

```bash
streamlit run app.py
```

This launches a local Streamlit server (by default at `http://localhost:8501`). Enter your Gemini API key in the sidebar (or set it via `.env`), load or paste content, and use the Summarizer, Deep Analysis, or Prompt Lab tabs.

---

## 🔐 API Key Security

- **Never commit `.env`** — it should stay local and out of version control.
- **Never hardcode the Gemini API key** in source files.
- `.env.example` contains only a placeholder value — copy it to `.env` and fill in your real key.
- If a real API key is ever accidentally committed or exposed, **revoke/rotate it immediately** from [Google AI Studio](https://aistudio.google.com/).

This project does not implement enterprise-grade secret management (e.g. vaults or key rotation automation) — it relies on standard local `.env` practices suitable for a development/portfolio project.

---

## Gemini Configuration

The sidebar model selector currently exposes:

- `gemini-1.5-flash` **(default)**
- `gemini-2.0-flash`
- `gemini-1.5-pro`

Under the hood, `get_working_models()` queries the Gemini API's live model list (`genai.list_models()`), filters out deprecated/unreleased models — **`gemini-2.5*` model names are explicitly excluded from this candidate list** — and builds a prioritized fallback chain: your requested model first, then the standard Flash/Pro models, then any remaining active models. If the requested model returns a `404`/"not found"/"not supported" error, `generate_summary()` and `analyze_content()` automatically retry the next candidate in the chain.

**Temperature** is user-adjustable from 0.0–1.0 (default 0.3) and is applied to both summarization and Deep Analysis. Lower values generally produce more deterministic output, while higher values allow more variation in phrasing and analysis.

---

## Token Usage & Cost Tracking

Implemented in `utils/cost_tracker.py`, the sidebar widget tracks, for the current Streamlit session (`st.session_state`):

- Total number of requests made
- Cumulative prompt (input) tokens
- Cumulative completion (output) tokens
- Total tokens
- A breakdown of the **last request** (model used, prompt/output/total tokens)

Because the Gemini Free Tier is used, **Actual Cost is always displayed as `$0.00`**. Alongside it, the tracker computes an **Estimated Commercial Cost** using hardcoded reference per-million-token rates (`COMMERCIAL_RATES` in `cost_tracker.py`) for Flash and Pro models. This is a rough estimate based on rates configured in code — **it is not a live lookup of Google's current pricing and does not represent your actual Google billing.**

---

## Prompt Engineering Concepts Demonstrated

- **Basic prompting** — a single instruction with no formatting or context (`V1`).
- **Structured prompting** — explicit output constraints (e.g. bullet count) to improve consistency (`V2`).
- **Professional prompting** — persona assignment, explicit constraints, negative constraints, and style-specific structural rules to improve reliability and output quality (`V3`).

The project treats prompts as an iterated, comparable design surface rather than static strings — the Prompt Lab tab exists specifically to make that progression visible and testable.

---

## Structured Outputs vs. Free-Form Generation

The app deliberately uses two different generation modes:

- **Summarization** uses free-form natural language generation, appropriate because summaries are meant to be read directly by a human.
- **Deep Analysis** uses Gemini's `response_schema` JSON mode with a Pydantic model, appropriate because the output (sentiment, score, themes, action items, audience) is meant to be consumed reliably by other application logic — parsing free-form text for these fields would be brittle.

---

## Example Workflow

```text
Input Content
     ↓
Text / URL
     ↓
Content Extraction & Cleaning
     ↓
Gemini Processing
     ↓
 ┌───────────────┬────────────────┐
 │               │                │
 ▼               ▼                ▼
Summary       Deep Analysis    Prompt Lab
 │               │                │
 ▼               ▼                ▼
Human Text    JSON Output     Prompt Comparison
```

A user pastes text or extracts it from a URL, then chooses whether to generate a human-readable summary, run structured JSON analysis, or compare prompt strategies side-by-side — all against the same cleaned input content.

---

## Testing / Validation

This project has been **manually tested** (no automated test suite currently exists in the repository) across:

- Direct text summarization (TL;DR, Concise, and Detailed styles)
- All three prompt versions (V1, V2, V3) via the Prompt Lab
- Deep structured analysis output and JSON parsing
- Web URL extraction — successfully against a Technology Review article ([link](https://www.technologyreview.com/2020/09/04/1008156/knowledge-graph-ai-reads-web-machine-learning-natural-language-processing/))
- Web URL extraction — **failed as a known limitation** against `https://en.wikipedia.org/wiki/Pakistan` (see [Known Web Scraping Limitation](#️-known-web-scraping-limitation))
- Sidebar token/cost tracking across multiple requests
- Error handling for missing API keys, empty input, and invalid URLs
- Temperature control for both summarization and Deep Analysis, including validation with higher-temperature analysis runs

---

## Known Limitations

- **Web scraping coverage** — static HTTP + BeautifulSoup extraction cannot reliably handle every modern website.
- **JavaScript-rendered pages** — pages that require client-side JS execution to display content may fail extraction.
- **Anti-bot / authentication** — protected or bot-guarded websites may reject requests or return unusable content.
- **LLM output variability** — Gemini outputs can vary depending on model, prompt version, temperature, and input content, even for the same input.
- **API dependency** — the app requires a valid Gemini API key and network access; it does not function offline.
- **Token / context constraints** — very large documents are still subject to the selected Gemini model's context window and any API-side limits.

---

## 🚀 Future Improvements

Planned/potential — **not currently implemented:**

- Browser-based extraction (Playwright or Selenium) for JavaScript-rendered pages
- Dedicated readability/article-extraction libraries for more robust content isolation
- Batch document processing
- PDF/DOCX upload support
- Persistent history or database storage
- User authentication
- Export summaries to Markdown/PDF
- Additional structured analysis schemas
- Automated, quantitative evaluation of prompt versions
- RAG (retrieval-augmented generation) support
- Multi-provider LLM support (beyond Gemini)
- Streaming Gemini responses
- Automated test suite
- Observability/logging
- Deployment configuration (Docker, cloud hosting)

---

## 🎓 What I Learned / Engineering Takeaways

Building this project involved hands-on work with:

- **Prompt engineering** as an iterative process — comparing basic, constrained, and persona-driven prompts (V1 → V2 → V3)
- **LLM application architecture** — separating extraction, generation, and presentation into distinct modules
- **Structured generation** — using `response_mime_type="application/json"` and `response_schema` to constrain Gemini's output
- **Pydantic** for schema definition and output validation
- **API integration** with `google-generativeai`, including graceful **multi-model fallback** when a requested model is unavailable
- **Token accounting and cost awareness** — tracking prompt/completion tokens per request and estimating commercial cost even while using a free tier
- **Web scraping fundamentals** with `requests` + `BeautifulSoup`, including content-area heuristics and noise removal
- **Defensive error handling** — surfacing HTTP errors, timeouts, invalid input, and low-content extraction as clear user-facing messages
- **Streamlit application design** — multi-tab layouts, session state management, and custom CSS styling
- **Modular Python architecture** — clean separation between `modules/` (domain logic) and `utils/` (cross-cutting concerns)
- **Temperature tuning** — exposing adjustable temperature control for both summarization and structured analysis, allowing users to explore the trade-off between deterministic and varied generation.
- **Reliability considerations** in GenAI systems — model fallback chains, JSON parsing safety nets, and normalized defaults for missing fields

---

## 🔒 Security / Privacy Note

Content submitted to this application (pasted text or web-extracted text) is sent to the configured **Google Gemini API** for processing. This project does not itself persist, log, or store submitted content beyond the current Streamlit session state.

For details on how Google handles data sent to the Gemini API, refer to Google's official API terms and data-handling documentation. Avoid submitting sensitive or private information unless you have reviewed and are comfortable with the applicable provider data-handling policies.

---

## License

This repository does not currently specify a license.
