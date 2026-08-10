"""Content categorizer module for classifying saved items by topic.

Analyzes content text, titles, URLs, and metadata to assign topic categories
with confidence scores. Uses rule-based keyword matching with multiple signals.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

from personal_index.text_utils import tokenize


# ---------------------------------------------------------------------------
# Built-in topic definitions
# ---------------------------------------------------------------------------

BUILTIN_TOPICS: Dict[str, List[str]] = {
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
    keywords: List[str] = field(default_factory=list)
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
    matched_keywords: List[str] = field(default_factory=list)
    signal_sources: List[str] = field(default_factory=list)

    def __lt__(self, other: "TopicScore") -> bool:
        return self.score < other.score

    def __gt__(self, other: "TopicScore") -> bool:
        return self.score > other.score


@dataclass
class CategorizationResult:
    """Result of content categorization."""

    primary_topic: str
    topics: List[TopicScore] = field(default_factory=list)
    confidence: float = 0.0
    reasons: List[str] = field(default_factory=list)
    text_length: int = 0
    keyword_count: int = 0

    @property
    def secondary_topics(self) -> List[TopicScore]:
        """Return topics after the primary one."""
        return self.topics[1:] if len(self.topics) > 1 else []

    def top_n(self, n: int = 3) -> List[TopicScore]:
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
    URL_TOPIC_HINTS: Dict[str, List[str]] = {
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
        custom_topics: Optional[Dict[str, List[str]]] = None,
        min_score: float = 0.1,
        max_topics: int = 5,
    ):
        """Initialize the categorizer.

        Args:
            custom_topics: Dict mapping topic names to keyword lists.
            min_score: Minimum score threshold to include a topic.
            max_topics: Maximum number of topics to return.
        """
        self._topics: Dict[str, TopicCategory] = {}
        self._max_topics = max_topics
        self.min_score = min_score

        # Load built-in topics
        for name, keywords in BUILTIN_TOPICS.items():
            self._topics[name] = TopicCategory(name=name, keywords=keywords)

        # Add custom topics
        if custom_topics:
            for name, keywords in custom_topics.items():
                self.add_topic(name, keywords)

    def add_topic(self, name: str, keywords: List[str], description: str = "", weight: float = 1.0) -> TopicCategory:
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

    def get_topics(self) -> List[str]:
        """Get list of all available topic names."""
        return sorted(self._topics.keys())

    def get_topic(self, name: str) -> Optional[TopicCategory]:
        """Get a topic category by name."""
        return self._topics.get(name.lower())

    def categorize(
        self,
        text: str,
        title: str = "",
        url: str = "",
        meta_description: str = "",
    ) -> CategorizationResult:
        """Categorize content into topics.

        Args:
            text: Main content text to analyze.
            title: Title or heading of the content (boosts matching).
            url: URL of the content (provides path hints).
            meta_description: Meta description text (boosts matching).

        Returns:
            CategorizationResult with ranked topics and confidence.
        """
        if not text and not title and not meta_description:
            return CategorizationResult(
                primary_topic="unknown",
                topics=[],
                confidence=0.0,
                reasons=["no content provided"],
            )

        # Tokenize all signals
        text_tokens = set(tokenize(text, lowercase=True, remove_stopwords=True))
        title_tokens = set(tokenize(title, lowercase=True, remove_stopwords=True))
        meta_tokens = set(tokenize(meta_description, lowercase=True, remove_stopwords=True))

        # Extract URL hints
        url_hints = self._extract_url_hints(url)

        # Score each topic
        topic_scores: List[TopicScore] = []
        for topic_name, topic in self._topics.items():
            score, matched, sources = self._score_topic(
                topic=topic,
                text_tokens=text_tokens,
                title_tokens=title_tokens,
                meta_tokens=meta_tokens,
                url_hints=url_hints,
            )
            if score >= self.min_score:
                topic_scores.append(TopicScore(
                    topic=topic_name,
                    score=round(score, 4),
                    matched_keywords=matched,
                    signal_sources=sources,
                ))

        # Sort by score descending
        topic_scores.sort(key=lambda s: s.score, reverse=True)
        topic_scores = topic_scores[: self._max_topics]

        # Determine primary topic and confidence
        if topic_scores:
            primary = topic_scores[0].topic
            confidence = topic_scores[0].score
        else:
            primary = "uncategorized"
            confidence = 0.0

        # Build reasons
        reasons = self._build_reasons(topic_scores, text)

        return CategorizationResult(
            primary_topic=primary,
            topics=topic_scores,
            confidence=round(confidence, 4),
            reasons=reasons,
            text_length=len(text.split()),
            keyword_count=len(text_tokens),
        )

    def categorize_batch(
        self,
        items: List[Dict[str, str]],
    ) -> List[CategorizationResult]:
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

    def _score_topic(
        self,
        topic: TopicCategory,
        text_tokens: set,
        title_tokens: set,
        meta_tokens: set,
        url_hints: set,
    ) -> Tuple[float, List[str], List[str]]:
        """Score a single topic against content signals.

        Returns:
            Tuple of (score, matched_keywords, signal_sources).
        """
        score = 0.0
        matched_keywords: List[str] = []
        signal_sources: List[str] = []

        # 1. Text keyword matching
        text_matches = [kw for kw in topic.keywords if kw in text_tokens]
        if text_matches:
            # Normalize by topic keyword count to avoid bias toward large topics
            text_ratio = len(text_matches) / max(len(topic.keywords), 1)
            # Logarithmic scaling to prevent dominance
            text_score = min(len(text_matches) * 0.15, 1.0)
            score += text_score * topic.weight
            matched_keywords.extend(text_matches)
            signal_sources.append("text")

        # 2. Title keyword matching (boosted)
        title_matches = [kw for kw in topic.keywords if kw in title_tokens]
        if title_matches:
            title_score = min(len(title_matches) * 0.3 * self.TITLE_BOOST, 1.0)
            score += title_score * topic.weight
            for kw in title_matches:
                if kw not in matched_keywords:
                    matched_keywords.append(kw)
            signal_sources.append("title")

        # 3. Meta description matching (boosted)
        meta_matches = [kw for kw in topic.keywords if kw in meta_tokens]
        if meta_matches:
            meta_score = min(len(meta_matches) * 0.2 * self.META_DESC_BOOST, 1.0)
            score += meta_score * topic.weight
            for kw in meta_matches:
                if kw not in matched_keywords:
                    matched_keywords.append(kw)
            signal_sources.append("meta_description")

        # 4. URL hint matching
        if topic.name in url_hints:
            score += self.URL_HINT_BOOST * topic.weight
            signal_sources.append("url_hint")

        return score, matched_keywords, signal_sources

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
        except Exception:
            url_parts = url.lower().split()

        for topic_name, hint_words in self.URL_TOPIC_HINTS.items():
            for hint_word in hint_words:
                for part in url_parts:
                    if hint_word in part or part in hint_word:
                        hints.add(topic_name)
                        break

        return hints

    def _build_reasons(self, topic_scores: List[TopicScore], text: str) -> List[str]:
        """Build human-readable reasons for categorization.

        Args:
            topic_scores: Ranked list of topic scores.
            text: Original text content.

        Returns:
            List of reason strings.
        """
        reasons: List[str] = []

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
