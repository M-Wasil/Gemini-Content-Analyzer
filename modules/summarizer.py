"""
Summarizer Module
Handles prompt construction and Google Gemini API calls for text summarization across multiple styles and prompt engineering versions.
"""

import google.generativeai as genai
from utils.cost_tracker import record_token_usage

# Prompt Engineering Strategy Documentation
PROMPT_STRATEGIES = {
    "V1": {
        "name": "V1 (Basic Raw)",
        "description": "Simple baseline prompt without context, constraints, or structural instructions.",
        "template": "Summarize the following text:\n\n{text}"
    },
    "V2": {
        "name": "V2 (Basic Constrained)",
        "description": "Short prompt with simple output count constraints.",
        "template": "Summarize the following text in 3 bullet points:\n\n{text}"
    },
    "V3": {
        "name": "V3 (Professional System-Role)",
        "description": "Production-grade prompt with explicit persona, formatting rules, anti-hallucination constraints, and target style guidance.",
        "styles": {
            "TL;DR": (
                "You are an expert executive editor. Summarize the following content into a crisp, high-impact TL;DR.\n"
                "Constraints:\n"
                "- Maximum 2 sentences.\n"
                "- Highlight only the core takeaway or primary objective.\n"
                "- Do not include introductory fluff (e.g., 'This article discusses...').\n\n"
                "Content:\n{text}"
            ),
            "Concise": (
                "You are a principal intelligence analyst. Provide a concise bulleted summary of the key insights.\n"
                "Constraints:\n"
                "- Format as exactly 3 to 5 clear, structured bullet points.\n"
                "- Use bold leading keywords for each bullet (e.g., '**Key Trend:** ...').\n"
                "- Keep explanations tight and informative.\n\n"
                "Content:\n{text}"
            ),
            "Detailed": (
                "You are a senior technical writer. Generate a comprehensive multi-section summary of the following document.\n"
                "Constraints:\n"
                "- Structure into clear section headers (### Executive Summary, ### Key Findings, ### Implications & Next Steps).\n"
                "- Ensure complete coverage of essential facts while eliminating redundancy.\n"
                "- Maintain an objective, professional tone.\n\n"
                "Content:\n{text}"
            )
        }
    }
}

DEFAULT_SAFE_MODELS = ["models/gemini-1.5-flash", "models/gemini-2.0-flash", "models/gemini-1.5-pro"]

def get_working_models(api_key: str, requested_model: str) -> list[str]:
    """
    Queries Google Gemini API for active generateContent models, excluding deprecated ones (e.g. gemini-2.5),
    and returns a prioritized list of model candidates.
    """
    if not api_key or not api_key.strip():
        raise ValueError("Gemini API Key is missing. Please enter your key in the sidebar or .env file.")

    genai.configure(api_key=api_key.strip())
    
    api_models = []
    try:
        for m in genai.list_models():
            if "generateContent" in getattr(m, "supported_generation_methods", []):
                name = m.name
                # Exclude deprecated / legacy / unreleased test models
                if not any(dep in name.lower() for dep in ["gemini-2.5", "deprecated", "bison"]):
                    api_models.append(name)
    except Exception as e:
        err_msg = str(e)
        if "API_KEY_INVALID" in err_msg or "API key not valid" in err_msg or "400" in err_msg or "Unauthenticated" in err_msg:
            raise ValueError("Invalid Google Gemini API Key. Please get a free API key at https://aistudio.google.com/") from e
        # If list_models fails, use default safe candidates
        api_models = DEFAULT_SAFE_MODELS.copy()

    candidates = []
    clean_req = requested_model.lower().replace("models/", "")

    # 1. Add requested model if it's not deprecated
    if "gemini-2.5" not in clean_req:
        for m in api_models:
            if clean_req == m.lower().replace("models/", ""):
                candidates.append(m)

    # 2. Add standard safe Flash/Pro models
    for safe in DEFAULT_SAFE_MODELS:
        for m in api_models:
            if safe.replace("models/", "") in m.lower():
                candidates.append(m)

    # 3. Add all remaining active models
    candidates.extend(api_models)
    candidates.extend(DEFAULT_SAFE_MODELS)

    # Return unique candidates preserving order
    return list(dict.fromkeys(candidates))

def build_summary_prompt(text: str, style: str = "Concise", prompt_version: str = "V3") -> str:
    """
    Constructs the prompt string based on selected version and summary style.
    """
    if prompt_version == "V1":
        return PROMPT_STRATEGIES["V1"]["template"].format(text=text)
    elif prompt_version == "V2":
        return PROMPT_STRATEGIES["V2"]["template"].format(text=text)
    else:  # V3 Professional
        style_prompt = PROMPT_STRATEGIES["V3"]["styles"].get(
            style, PROMPT_STRATEGIES["V3"]["styles"]["Concise"]
        )
        return style_prompt.format(text=text)

def generate_summary(
    api_key: str,
    text: str,
    style: str = "Concise",
    prompt_version: str = "V3",
    model_name: str = "gemini-1.5-flash",
    temperature: float = 0.3
) -> tuple[str, dict]:
    """
    Generates a text summary using Google Gemini API with multi-model fallback retry.
    """
    if not api_key or not api_key.strip():
        raise ValueError("Gemini API Key is missing. Please enter your key in the sidebar or .env file.")

    if not text or len(text.strip()) == 0:
        raise ValueError("Input text is empty.")

    candidate_models = get_working_models(api_key, model_name)
    genai.configure(api_key=api_key.strip())
    prompt = build_summary_prompt(text=text, style=style, prompt_version=prompt_version)

    last_exception = None
    for target_model in candidate_models:
        try:
            model = genai.GenerativeModel(target_model)
            config = genai.GenerationConfig(temperature=temperature)
            response = model.generate_content(prompt, generation_config=config)
            
            summary_text = response.text
            usage = record_token_usage(getattr(response, "usage_metadata", None), model_name=target_model)
            return summary_text, usage
        except Exception as e:
            last_exception = e
            err_str = str(e).lower()
            # Catch deprecation, 404, or model unavailable errors and try next candidate
            if "404" in err_str or "no longer available" in err_str or "not found" in err_str or "not supported" in err_str:
                continue
            raise e

    raise RuntimeError(f"Failed to generate summary with Gemini API: {str(last_exception)}")
