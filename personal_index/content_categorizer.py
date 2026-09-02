"""Content categorizer module for classifying saved items by topic.

Analyzes content text, titles, URLs, and metadata to assign topic categories
with confidence scores. Uses rule-based keyword matching with multiple signals.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar
from urllib.parse import urlparse

from personal_index.text_utils import tokenize

# ---------------------------------------------------------------------------
# Built-in topic definitions
# ---------------------------------------------------------------------------

BUILTIN_TOPICS: dict[str, list[str]] = {
    "technology": [
        "software", "programming", "developer", "api", "framework", "library",
        "algorithm", "database", "server", "cloud", "devops", "docker", "kubernetes",
        "microservice", "frontend", "backend", "fullstack", "javascript", "python",
        "rust", "go", "golang", "typescript", "react", "vue", "angular", "node",
        "linux", "kernel", "compiler", "runtime", "virtualization", "container",
        "ci/cd", "pipeline", "terraform", "ansible", "aws", "azure", "gcp",
        "machine learning", "deep learning", "neural network", "ai", "artificial intelligence",
        "blockchain", "cryptocurrency", "web3", "nft", "smart contract",
        "cybersecurity", "encryption", "firewall", "penetration testing", "vulnerability",
        "open source", "git", "github", "stackoverflow", "debugging", "refactoring",
        "performance", "optimization", "caching", "load balancing", "cdn",
        "mobile", "ios", "android", "app", "sdk", "rest", "graphql",
        "data structure", "design pattern", "architecture", "scalability",
    ],
    "science": [
        "research", "experiment", "hypothesis", "peer review", "journal",
        "physics", "chemistry", "biology", "astronomy", "geology", "ecology",
        "quantum", "molecule", "atom", "particle", "genetics", "dna", "rna",
        "evolution", "species", "ecosystem", "climate", "carbon", "photosynthesis",
        "neuroscience", "brain", "cognitive", "psychology", "behavior",
        "mathematics", "theorem", "proof", "calculus", "algebra", "statistics",
        "probability", "topology", "geometry", "arithmetic",
        "discovery", "observation", "methodology", "empirical", "data analysis",
        "telescope", "microscope", "laboratory", "specimen", "sample",
        "nasa", "space", "planet", "star", "galaxy", "orbit", "gravity",
        "thermodynamics", "entropy", "energy", "force", "velocity", "acceleration",
        "organic", "inorganic", "compound", "reaction", "catalyst", "enzyme",
        "cell", "tissue", "organism", "microbe", "bacteria", "virus",
    ],
    "health": [
        "medical", "doctor", "hospital", "treatment", "therapy", "diagnosis",
        "patient", "symptom", "disease", "illness", "condition", "chronic",
        "nutrition", "diet", "exercise", "fitness", "wellness", "mental health",
        "medication", "prescription", "dosage", "clinical trial", "pharma",
        "cardiology", "neurology", "oncology", "pediatrics", "surgery",
        "vaccine", "immunization", "pandemic", "epidemic", "infection",
        "blood pressure", "cholesterol", "diabetes", "cancer", "tumor",
        "mental", "anxiety", "depression", "stress", "meditation", "mindfulness",
        "sleep", "recovery", "rehabilitation", "physical therapy",
        "healthcare", "insurance", "wellness", "preventive", "screening",
        "vitamin", "supplement", "antibiotic", "antiviral",
    ],
    "finance": [
        "stock", "market", "investment", "portfolio", "trading", "equity",
        "bond", "mutual fund", "etf", "dividend", "yield", "interest rate",
        "banking", "loan", "mortgage", "credit", "debit", "savings",
        "inflation", "deflation", "recession", "gdp", "fiscal", "monetary",
        "tax", "taxation", "deduction", "filing", "irs", "audit",
        "budget", "expense", "revenue", "profit", "loss", "earnings",
        "accounting", "bookkeeping", "balance sheet", "cash flow", "ledger",
        "cryptocurrency", "bitcoin", "ethereum", "defi", "staking",
        "insurance", "premium", "claim", "coverage", "actuary",
        "venture capital", "startup", "funding", "ipo", "valuation",
        "forex", "commodity", "futures", "options", "hedging",
        "financial planning", "retirement", "401k", "ira", "pension",
    ],
    "education": [
        "learning", "course", "curriculum", "syllabus", "lecture", "tutorial",
        "university", "college", "school", "degree", "certificate", "diploma",
        "student", "teacher", "professor", "instructor", "tutor",
        "exam", "test", "assignment", "homework", "grade", "gpa",
        "online learning", "mooc", "edtech", "distance learning", "webinar",
        "research paper", "thesis", "dissertation", "publication", "academic",
        "pedagogy", "andragogy", "instructional design", "assessment",
        "scholarship", "grant", "fellowship", "tuition", "financial aid",
        "literacy", "numeracy", "critical thinking", "problem solving",
        "workshop", "seminar", "conference", "symposium",
    ],
    "business": [
        "startup", "entrepreneur", "venture capital", "funding", "pitch",
        "strategy", "marketing", "sales", "revenue", "growth", "scaling",
        "management", "leadership", "team", "culture", "hiring", "recruiting",
        "product", "launch", "mvp", "roadmap", "agile", "scrum", "kanban",
        "customer", "user", "experience", "ux", "ui", "design",
        "brand", "logo", "identity", "positioning", "competitive analysis",
        "merger", "acquisition", "partnership", "joint venture", "licensing",
        "supply chain", "logistics", "inventory", "procurement", "vendor",
        "crm", "erp", "saas", "b2b", "b2c", "d2c",
        "kpi", "metric", "analytics", "dashboard", "reporting",
        "negotiation", "contract", "legal", "compliance", "regulation",
    ],
    "entertainment": [
        "movie", "film", "cinema", "theater", "actor", "actress", "director",
        "music", "album", "song", "artist", "band", "concert", "festival",
        "game", "gaming", "esports", "console", "pc gaming", "mobile game",
        "tv show", "series", "episode", "streaming", "netflix", "hbo",
        "comedy", "drama", "action", "horror", "documentary", "animation",
        "book", "novel", "author", "publisher", "literature", "fiction",
        "podcast", "radio", "interview", "talk show",
        "celebrity", "famous", "award", "oscar", "grammy", "emmy",
        "art", "painting", "sculpture", "gallery", "museum", "exhibition",
        "photography", "video", "vlog", "youtube", "tiktok",
    ],
    "sports": [
        "football", "soccer", "basketball", "baseball", "hockey", "tennis",
        "golf", "swimming", "athletics", "track", "marathon", "olympics",
        "player", "team", "coach", "league", "championship", "tournament",
        "score", "goal", "point", "win", "loss", "draw", "tiebreaker",
        "training", "workout", "stamina", "endurance", "strength", "speed",
        "injury", "recovery", "rehabilitation", "fitness", "conditioning",
        "draft", "trade", "roster", "free agent", "contract", "salary cap",
        "fan", "stadium", "arena", "venue", "broadcast", "highlight",
        "world cup", "super bowl", "world series", "mclaren", "formula 1",
    ],
    "travel": [
        "destination", "vacation", "trip", "journey", "adventure", "explore",
        "hotel", "resort", "hostel", "accommodation", "booking", "reservation",
        "flight", "airline", "airport", "boarding", "layover", "transit",
        "passport", "visa", "customs", "immigration", "border",
        "tourism", "tourist", "guide", "itinerary", "backpacking", "cruise",
        "landmark", "attraction", "museum", "monument", "heritage",
        "culture", "local", "tradition", "festival", "cuisine", "food",
        "budget travel", "luxury travel", "solo travel", "family travel",
        "road trip", "camping", "hiking", "national park", "wilderness",
        "exchange rate", "currency", "travel insurance", "luggage",
    ],
    "food": [
        "recipe", "cooking", "baking", "ingredient", "kitchen", "chef",
        "restaurant", "dining", "menu", "cuisine", "gourmet", "fine dining",
        "vegetarian", "vegan", "gluten-free", "organic", "farm-to-table",
        "wine", "beer", "cocktail", "spirits", "brewery", "winery",
        "breakfast", "lunch", "dinner", "snack", "dessert", "appetizer",
        "grilling", "roasting", "sauteing", "boiling", "steaming", "frying",
        "spice", "herb", "seasoning", "sauce", "marinade", "glaze",
        "nutrition", "calorie", "protein", "carbohydrate", "fat", "fiber",
        "meal prep", "food delivery", "takeout", "catering", "food truck",
        "farmers market", "grocery", "pantry", "storage", "preservation",
    ],
    "politics": [
        "election", "vote", "campaign", "candidate", "president", "congress",
        "senate", "house", "parliament", "government", "administration",
        "policy", "legislation", "bill", "law", "regulation", "executive order",
        "democracy", "republic", "authoritarian", "totalitarian", "dictatorship",
        "liberal", "conservative", "progressive", "moderate", "extremist",
        "partisan", "bipartisan", "nonpartisan", "independent",
        "foreign policy", "diplomacy", "treaty", "sanction", "embargo",
        "protest", "rally", "demonstration", "march", "civil rights",
        "supreme court", "judicial", "constitutional", "amendment",
        "lobbying", "campaign finance", "polarization", "partisan",
        "referendum", "ballot", "poll", "opinion", "approval rating",
    ],
    "environment": [
        "climate change", "global warming", "greenhouse gas", "carbon footprint",
        "renewable energy", "solar", "wind", "hydroelectric", "geothermal",
        "sustainability", "sustainable", "eco-friendly", "green", "carbon neutral",
        "pollution", "emission", "air quality", "water quality", "waste",
        "recycling", "compost", "upcycling", "circular economy",
        "deforestation", "reforestation", "biodiversity", "habitat", "wildlife",
        "ocean", "coral reef", "sea level", "acidification", "marine",
        "conservation", "endangered species", "extinction", "ecosystem",
        "environmental justice", "carbon tax", "cap and trade", "paris agreement",
        "drought", "flood", "hurricane", "wildfire", "natural disaster",
        "electric vehicle", "ev", "tesla", "battery", "charging station",
    ],
}

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class TopicCategory:
    """A topic category with associated keywords and metadata."""

    name: str
    keywords: list[str] = field(default_factory=list)
    description: str = ""
    weight: float = 1.0

    def __post_init__(self):
        # Normalize keywords to lowercase
        self.keywords = [kw.lower() for kw in self.keywords]

@dataclass
class TopicScore:
    """Score for a single topic assignment."""

    topic: str
    score: float
    matched_keywords: list[str] = field(default_factory=list)
    signal_sources: list[str] = field(default_factory=list)

    def __lt__(self, other: TopicScore) -> bool:
        return self.score < other.score

    def __gt__(self, other: TopicScore) -> bool:
        return self.score > other.score

@dataclass
class CategorizationResult:
    """Result of content categorization."""

    primary_topic: str
    topics: list[TopicScore] = field(default_factory=list)
    confidence: float = 0.0
    reasons: list[str] = field(default_factory=list)
    text_length: int = 0
    keyword_count: int = 0

    @property
    def secondary_topics(self) -> list[TopicScore]:
        """Return topics after the primary one."""
        return self.topics[1:] if len(self.topics) > 1 else []

    def top_n(self, n: int = 3) -> list[TopicScore]:
        """Return top N topics."""
        return self.topics[:n]

# ---------------------------------------------------------------------------
# Categorization engine
# ---------------------------------------------------------------------------

class ContentCategorizer:
    """Classifies content into topic categories using multi-signal analysis.

    Signals used:
    - Keyword matching against topic dictionaries
    - Title/heading boosting (keywords in titles count more)
    - URL path hints (e.g., /tech/, /health/)
    - Meta description analysis

    Supports both built-in topics and user-defined custom topics.
    """

    # URL path patterns that hint at topics
    URL_TOPIC_HINTS: ClassVar[dict[str, list[str]]] = {
        "technology": ["tech", "dev", "api", "code", "software", "programming", "blog"],
        "science": ["science", "research", "lab", "study", "journal"],
        "health": ["health", "medical", "wellness", "fitness", "clinic"],
        "finance": ["finance", "money", "invest", "bank", "stock", "crypto"],
        "education": ["education", "learn", "course", "tutorial", "academy"],
        "business": ["business", "company", "startup", "enterprise", "corp"],
        "entertainment": ["entertainment", "media", "show", "movie", "music", "game"],
        "sports": ["sports", "sport", "team", "league", "match"],
        "travel": ["travel", "trip", "tourism", "destination", "vacation"],
        "food": ["food", "recipe", "cooking", "restaurant", "dining", "eat"],
        "politics": ["politics", "political", "government", "election", "news"],
        "environment": ["environment", "climate", "green", "sustainability", "eco"],
    }

    # Minimum score to include a topic in results
    MIN_TOPIC_SCORE: float = 0.1

    # Score multipliers for different signals
    TITLE_BOOST: float = 2.0
    URL_HINT_BOOST: float = 0.3
    META_DESC_BOOST: float = 1.5

    def __init__(
        self,
        custom_topics: dict[str, list[str]] | None = None,
        min_score: float = 0.1,
        max_topics: int = 5,
    ):
        """Initialize the categorizer.

        Args:
            custom_topics: Dict mapping topic names to keyword lists.
            min_score: Minimum score threshold to include a topic.
            max_topics: Maximum number of topics to return.
        """
        self._topics: dict[str, TopicCategory] = {}
        self._max_topics = max_topics
        self.min_score = min_score

        # Load built-in topics
        for name, keywords in BUILTIN_TOPICS.items():
            self._topics[name] = TopicCategory(name=name, keywords=keywords)

        # Add custom topics
        if custom_topics:
            for name, keywords in custom_topics.items():
                self.add_topic(name, keywords)

    def add_topic(self, name: str, keywords: list[str], description: str = "", weight: float = 1.0) -> TopicCategory:
        """Add or update a topic category.

        Args:
            name: Topic name (lowercase, no spaces recommended).
            keywords: List of keywords associated with this topic.
            description: Human-readable description.
            weight: Weight multiplier for this topic's scores.

        Returns:
            The created/updated TopicCategory.
        """
        topic = TopicCategory(
            name=name.lower(),
            keywords=keywords,
            description=description,
            weight=weight,
        )
        self._topics[name.lower()] = topic
        return topic

    def remove_topic(self, name: str) -> bool:
        """Remove a topic category.

        Args:
            name: Topic name to remove.

        Returns:
            True if topic was removed, False if it didn't exist.
        """
        name_lower = name.lower()
        if name_lower in self._topics:
            del self._topics[name_lower]
            return True
        return False

    def get_topics(self) -> list[str]:
        """Get list of all available topic names."""
        return sorted(self._topics.keys())

    def get_topic(self, name: str) -> TopicCategory | None:
        """Get a topic category by name."""
        return self._topics.get(name.lower())

    def categorize(
        self,
        text: str,
        title: str = "",
        url: str = "",
        meta_description: str = "",
    ) -> CategorizationResult:
        """Categorize content into topics."""
        if not text and not title and not meta_description:
            return CategorizationResult(
                primary_topic="unknown",
                topics=[],
                confidence=0.0,
                reasons=["no content provided"],
            )

        tokens = self._tokenize_signals(text, title, meta_description)
        text_lower, title_lower, meta_lower = self._lowercase_signals(
            text, title, meta_description
        )
        url_hints = self._extract_url_hints(url)

        topic_scores = self._score_all_topics(
            tokens["text"], tokens["title"], tokens["meta"],
            text_lower, title_lower, meta_lower, url_hints,
        )
        topic_scores = topic_scores[:self._max_topics]

        primary, confidence = self._primary_and_confidence(topic_scores)
        reasons = self._build_reasons(topic_scores, text)

        return CategorizationResult(
            primary_topic=primary,
            topics=topic_scores,
            confidence=round(confidence, 4),
            reasons=reasons,
            text_length=len(text.split()),
            keyword_count=len(tokens["text"]),
        )

    def _tokenize_signals(
        self, text: str, title: str, meta: str
    ) -> dict[str, set]:
        def tok(s: str) -> set:
            return set(tokenize(s, lowercase=True, remove_stopwords=True))
        return {"text": tok(text), "title": tok(title), "meta": tok(meta)}

    @staticmethod
    def _lowercase_signals(text: str, title: str, meta: str) -> tuple[str, str, str]:
        return text.lower(), title.lower(), meta.lower()

    def _score_all_topics(
        self, text_tokens, title_tokens, meta_tokens,
        text_lower: str, title_lower: str, meta_lower: str, url_hints
    ) -> list[TopicScore]:
        scores: list[TopicScore] = []
        for topic_name, topic in self._topics.items():
            score, matched, sources = self._score_topic(
                topic=topic,
                text_tokens=text_tokens,
                title_tokens=title_tokens,
                meta_tokens=meta_tokens,
                text_lower=text_lower,
                title_lower=title_lower,
                meta_lower=meta_lower,
                url_hints=url_hints,
            )
            if score >= self.min_score:
                scores.append(TopicScore(
                    topic=topic_name,
                    score=round(score, 4),
                    matched_keywords=matched,
                    signal_sources=sources,
                ))
        scores.sort(key=lambda s: s.score, reverse=True)
        return scores

    @staticmethod
    def _primary_and_confidence(
        topic_scores: list[TopicScore],
    ) -> tuple[str, float]:
        if topic_scores:
            return topic_scores[0].topic, topic_scores[0].score
        return "uncategorized", 0.0

    def categorize_batch(
        self,
        items: list[dict[str, str]],
    ) -> list[CategorizationResult]:
        """Categorize multiple content items.

        Args:
            items: List of dicts with keys 'text', 'title', 'url', 'meta_description'.

        Returns:
            List of CategorizationResult objects.
        """
        return [
            self.categorize(
                text=item.get("text", ""),
                title=item.get("title", ""),
                url=item.get("url", ""),
                meta_description=item.get("meta_description", ""),
            )
            for item in items
        ]

    def _add_matches(
        self,
        matches: list[str],
        kw: list[str],
        src: list[str],
        source: str = "text",
    ) -> list[str]:
        for k in matches:
            if k not in kw:
                kw.append(k)
        if matches:
            src.append(source)
        return kw

    def _score_topic(
        self,
        topic: TopicCategory,
        text_tokens: set,
        title_tokens: set,
        meta_tokens: set,
        text_lower: str,
        title_lower: str,
        meta_lower: str,
        url_hints: set,
    ) -> tuple[float, list[str], list[str]]:
        """Score a single topic against content signals."""
        score = 0.0
        matched: list[str] = []
        sources: list[str] = []

        tm = self._match_keywords(topic.keywords, text_tokens, text_lower)
        if tm:
            score += min(len(tm) * 0.15, 1.0) * topic.weight
            matched.extend(tm)
            sources.append("text")

        ttm = self._match_keywords(topic.keywords, title_tokens, title_lower)
        if ttm:
            score += min(len(ttm) * 0.3 * self.TITLE_BOOST, 1.0) * topic.weight
            self._add_matches(ttm, matched, sources, "title")

        mm = self._match_keywords(topic.keywords, meta_tokens, meta_lower)
        if mm:
            score += min(len(mm) * 0.2 * self.META_DESC_BOOST, 1.0) * topic.weight
            self._add_matches(mm, matched, sources, "meta_description")

        if topic.name in url_hints:
            score += self.URL_HINT_BOOST * topic.weight
            sources.append("url_hint")

        return score, matched, sources

    def _match_keywords(
        self,
        keywords: list[str],
        tokens: set,
        raw_text: str,
    ) -> list[str]:
        """Match keywords against both single-word tokens and multi-word phrases.

        Single-word keywords are matched against the token set.
        Multi-word keywords are matched as substrings in the raw text.

        Args:
            keywords: List of keyword strings (may be single or multi-word).
            tokens: Set of single-word tokens from the text.
            raw_text: Lowercased raw text for phrase matching.

        Returns:
            List of matched keywords.
        """
        matches: list[str] = []
        for kw in keywords:
            if " " in kw:
                # Multi-word keyword: check as substring in raw text
                if kw in raw_text:
                    matches.append(kw)
            else:
                # Single-word keyword: check in token set
                if kw in tokens:
                    matches.append(kw)
        return matches

    def _extract_url_hints(self, url: str) -> set:
        """Extract topic hints from URL path and domain.

        Args:
            url: URL string to analyze.

        Returns:
            Set of topic names hinted at by the URL.
        """
        if not url:
            return set()

        hints: set = set()
        try:
            parsed = urlparse(url)
            path_parts = [p.lower() for p in parsed.path.split("/") if p]
            domain_parts = [p.lower() for p in parsed.netloc.split(".") if p]
            url_parts = path_parts + domain_parts
        except ValueError:
            url_parts = url.lower().split()

        for topic_name, hint_words in self.URL_TOPIC_HINTS.items():
            for hint_word in hint_words:
                for part in url_parts:
                    if hint_word in part or part in hint_word:
                        hints.add(topic_name)
                        break

        return hints

    def _build_reasons(self, topic_scores: list[TopicScore], _text: str) -> list[str]:
        """Build human-readable reasons for categorization.

        Args:
            topic_scores: Ranked list of topic scores.
            _text: Original text content (unused).

        Returns:
            List of reason strings.
        """
        reasons: list[str] = []

        if not topic_scores:
            reasons.append("no matching topics found in content")
            return reasons

        for ts in topic_scores[:3]:
            sources_str = ", ".join(ts.signal_sources) if ts.signal_sources else "text"
            kw_preview = ", ".join(ts.matched_keywords[:5])
            if len(ts.matched_keywords) > 5:
                kw_preview += f" (+{len(ts.matched_keywords) - 5} more)"
            reasons.append(
                f"{ts.topic} (score={ts.score}, signals={sources_str}, "
                f"keywords=[{kw_preview}])"
            )

        return reasons
