"""
Extractor Module
Handles URL text fetching, web scraping, and content cleaning for summarization.
"""

import re
import requests
from bs4 import BeautifulSoup

# Standard HTTP headers to avoid simple scraping blocks
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

def fetch_and_clean_url(url: str, timeout: int = 12) -> tuple[str, str, int]:
    """
    Fetches content from a URL, strips HTML noise, and returns clean plain text.

    Args:
        url (str): Target webpage URL.
        timeout (int): HTTP request timeout in seconds.

    Returns:
        tuple[str, str, int]: (page_title, cleaned_text, word_count)
    
    Raises:
        ValueError: If URL format is invalid or content is unparseable.
        requests.RequestException: On HTTP or network connectivity failures.
    """
    # Clean up URL whitespace & validate scheme
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        response = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
        response.raise_for_status()
    except requests.exceptions.MissingSchema:
        raise ValueError("Invalid URL format. Please include http:// or https://")
    except requests.exceptions.Timeout:
        raise requests.RequestException(f"Connection to {url} timed out after {timeout} seconds.")
    except requests.exceptions.HTTPError as e:
        raise requests.RequestException(f"HTTP Error {response.status_code}: Could not fetch page.")
    except requests.exceptions.RequestException as e:
        raise requests.RequestException(f"Failed to fetch URL: {str(e)}")

    # Ensure content is HTML/text
    content_type = response.headers.get("Content-Type", "").lower()
    if "text/html" not in content_type and "text/plain" not in content_type:
        raise ValueError(f"URL returned non-text content type: {content_type}")

    soup = BeautifulSoup(response.text, "html.parser")

    # Extract page title
    page_title = "Untitled Page"
    if soup.title and soup.title.string:
        page_title = soup.title.string.strip()
    elif soup.h1:
        page_title = soup.h1.get_text(strip=True)

    # Decompose unwanted elements
    unwanted_tags = [
        "script", "style", "nav", "header", "footer", "aside",
        "form", "noscript", "iframe", "svg", "button", "input",
        "dialog", "menu"
    ]
    for tag in soup(unwanted_tags):
        tag.decompose()

    # Decompose common ad/cookie overlay class patterns
    for element in soup.find_all(class_=re.compile(r"(comment|sidebar|cookie|banner|advertisement|modal|nav|footer)", re.I)):
        element.decompose()

    # Target primary content areas if available
    main_content = (
        soup.find("article")
        or soup.find("main")
        or soup.find(attrs={"role": "main"})
        or soup.find(id=re.compile(r"(content|main|article)", re.I))
        or soup.body
        or soup
    )

    # Extract text from paragraphs and headers inside main content
    text_blocks = []
    for element in main_content.find_all(["h1", "h2", "h3", "h4", "p", "li"]):
        block_text = element.get_text(separator=" ", strip=True)
        if len(block_text.split()) >= 3:  # Skip trivial fragments
            text_blocks.append(block_text)

    # Fallback if block extraction yields little content
    if not text_blocks:
        raw_text = main_content.get_text(separator="\n", strip=True)
        lines = [line.strip() for line in raw_text.splitlines() if len(line.strip().split()) >= 3]
        text = "\n\n".join(lines)
    else:
        text = "\n\n".join(text_blocks)

    # Sanitize multiple whitespaces and consecutive newlines
    cleaned_text = re.sub(r"\n{3,}", "\n\n", text)
    cleaned_text = re.sub(r"[ \t]+", " ", cleaned_text).strip()

    word_count = len(cleaned_text.split())

    if word_count < 15:
        raise ValueError("Could not extract meaningful text from this URL. The page may require JavaScript or authentication.")

    return page_title, cleaned_text, word_count
