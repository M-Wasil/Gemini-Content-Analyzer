"""
Analyzer Module
Handles sentiment analysis, key theme extraction, action item identification, and target audience classification using Google Gemini's JSON Structured Output mode.
"""

import json
from typing import List
from pydantic import BaseModel, Field
import google.generativeai as genai
from utils.cost_tracker import record_token_usage
from modules.summarizer import get_working_models

class ContentAnalysis(BaseModel):
    """Pydantic schema for guaranteed structured output from Gemini API."""
    sentiment: str = Field(
        description="Overall sentiment: 'Positive', 'Negative', or 'Neutral'"
    )
    sentiment_score: float = Field(
        description="Sentiment intensity score between -1.0 (very negative) and 1.0 (very positive)"
    )
    sentiment_reasoning: str = Field(
        description="Brief 1-sentence explanation of why this sentiment was assigned"
    )
    themes: List[str] = Field(
        description="List of top 3 to 5 core topics, themes, or subjects covered in the text"
    )
    action_items: List[str] = Field(
        description="List of explicit or implied action items, tasks, follow-ups, or decisions. Empty list [] if none."
    )
    target_audience: str = Field(
        description="Target demographic, domain audience, or intended readers (e.g., 'Software Engineers', 'General Public', 'Executive Team')"
    )

ANALYZER_PROMPT = """
You are an expert NLP content analyst. Analyze the following text and return a JSON object adhering strictly to the required schema.

Required Fields:
1. 'sentiment': Must be strictly one of ['Positive', 'Negative', 'Neutral'].
2. 'sentiment_score': Float from -1.0 to 1.0.
3. 'sentiment_reasoning': Concise justification for sentiment classification.
4. 'themes': Array of 3 to 5 key topics or central themes.
5. 'action_items': Array of concrete tasks, deadlines, follow-ups, or recommendations mentioned or implied. If none exist, return [].
6. 'target_audience': Primary intended reader or audience.

Text to Analyze:
{text}
"""

def analyze_content(
    api_key: str,
    text: str,
    model_name: str = "gemini-1.5-flash",
    temperature: float = 0.1
) -> tuple[dict, dict]:
    """
    Analyzes input text for sentiment, themes, action items, and audience using Gemini JSON mode.
    """
    if not api_key or not api_key.strip():
        raise ValueError("Gemini API Key is missing. Please enter your key in the sidebar or .env file.")

    if not text or len(text.strip()) == 0:
        raise ValueError("Input text is empty.")

    candidate_models = get_working_models(api_key, model_name)
    genai.configure(api_key=api_key.strip())
    prompt = ANALYZER_PROMPT.format(text=text)

    last_exception = None
    for target_model in candidate_models:
        try:
            model = genai.GenerativeModel(target_model)
            generation_config = genai.GenerationConfig(
                temperature=temperature,
                response_mime_type="application/json",
                response_schema=ContentAnalysis
            )

            response = model.generate_content(prompt, generation_config=generation_config)
            usage = record_token_usage(getattr(response, "usage_metadata", None), model_name=target_model)
            
            # Parse JSON output
            raw_text = response.text.strip()
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:]
            if raw_text.startswith("```"):
                raw_text = raw_text[3:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]
            raw_text = raw_text.strip()

            parsed_json = json.loads(raw_text)
            
            normalized_result = {
                "sentiment": parsed_json.get("sentiment", "Neutral"),
                "sentiment_score": float(parsed_json.get("sentiment_score", 0.0)),
                "sentiment_reasoning": parsed_json.get("sentiment_reasoning", "Analysis completed."),
                "themes": parsed_json.get("themes", []),
                "action_items": parsed_json.get("action_items", []),
                "target_audience": parsed_json.get("target_audience", "General Readers")
            }

            return normalized_result, usage

        except Exception as e:
            last_exception = e
            err_str = str(e).lower()
            if "404" in err_str or "no longer available" in err_str or "not found" in err_str or "not supported" in err_str:
                continue
            raise e

    raise RuntimeError(f"Failed to analyze text with Gemini API: {str(last_exception)}")
