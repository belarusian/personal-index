"""Content extraction and text processing utilities."""

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from urllib.parse import urlparse

from bs4 import BeautifulSoup


@dataclass
class ExtractedContent:
    """Represents extracted content from a web page."""

    url: str
    title: str = ""
    text: str = ""
    meta_description: str = ""
    meta_keywords: List[str] = field(default_factory=list)
    headings: List[str] = field(default_factory=list)
    links: List[str] = field(default_factory=list)
    content_length: int = 0
    language: str = "en"
    fetched_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    status_code: int = 0

    def get_searchable_text(self) -> str:
        """Get combined searchable text from all fields."""
        parts = [self.title, self.meta_description]
        parts.extend(self.headings)
        parts.append(self.text)
        return " ".join(parts)

    def get_keywords(self) -> List[str]:
        """Extract keywords from meta tags and headings."""
        keywords = list(self.meta_keywords)
        for heading in self.headings:
            words = heading.lower().split()
            keywords.extend(words)
        return list(set(keywords))


def extract_content(html: str, url: str, status_code: int = 200) -> ExtractedContent:
    """Extract structured content from HTML."""
    soup = BeautifulSoup(html, "lxml")
    content = ExtractedContent(url=url, status_code=status_code)

    # Extract title
    title_tag = soup.find("title")
    if title_tag:
        content.title = title_tag.get_text(strip=True)

    # Extract meta description
    meta_desc = soup.find("meta", attrs={"name": "description"})
    if meta_desc:
        content.meta_description = meta_desc.get("content", "")

    # Extract meta keywords
    meta_kw = soup.find("meta", attrs={"name": "keywords"})
    if meta_kw:
        content.meta_keywords = [
            k.strip() for k in meta_kw.get("content", "").split(",") if k.strip()
        ]

    # Extract headings
    for level in ["h1", "h2", "h3", "h4", "h5", "h6"]:
        for heading in soup.find_all(level):
            text = heading.get_text(strip=True)
            if text:
                content.headings.append(f"{level}: {text}")

    # Extract main text content
    content.text = _extract_main_text(soup)
    content.content_length = len(content.text)

    # Extract language
    html_tag = soup.find("html")
    if html_tag and html_tag.get("lang"):
        content.language = html_tag["lang"]

    # Extract links
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"].strip()
        if href and not href.startswith(("javascript:", "mailto:", "tel:", "#")):
            content.links.append(href)

    return content


def _extract_main_text(soup: BeautifulSoup) -> str:
    """Extract main text content, removing scripts and styles."""
    # Remove script and style elements
    for element in soup(["script", "style", "nav", "footer", "header", "noscript"]):
        element.decompose()

    # Get text
    text = soup.get_text(separator="\n")

    # Clean up whitespace
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = "\n".join(chunk for chunk in chunks if chunk)

    return text


def tokenize(text: str) -> List[str]:
    """Tokenize text into lowercase words."""
    text = text.lower()
    tokens = re.findall(r"\b[a-z0-9]+\b", text)
    return tokens


def remove_stopwords(tokens: List[str], stopwords: Optional[set] = None) -> List[str]:
    """Remove common stopwords from token list."""
    if stopwords is None:
        stopwords = {
            "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
            "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will", "would",
            "could", "should", "may", "might", "shall", "can", "need", "dare",
            "it", "its", "this", "that", "these", "those", "i", "you", "he", "she",
            "we", "they", "what", "which", "who", "whom", "when", "where", "why",
            "how", "all", "each", "every", "both", "few", "more", "most", "other",
            "some", "such", "no", "nor", "not", "only", "own", "same", "so", "than",
            "too", "very", "just", "about", "above", "after", "again", "also",
            "any", "as", "at", "before", "below", "between", "during", "if", "into",
            "like", "me", "my", "myself", "new", "now", "old", "over", "per",
            "then", "there", "through", "under", "up", "us",
        }
    return [t for t in tokens if t not in stopwords]


def compute_tf(tokens: List[str]) -> dict:
    """Compute term frequency for a list of tokens."""
    tf = {}
    total = len(tokens)
    if total == 0:
        return tf
    for token in tokens:
        tf[token] = tf.get(token, 0) + 1
    # Normalize by total
    for token in tf:
        tf[token] /= total
    return tf
