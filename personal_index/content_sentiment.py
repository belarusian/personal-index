"""Sentiment analysis for saved content in personal-index.

Provides lexicon-based sentiment analysis without external NLP dependencies.
Supports sentence-level and document-level analysis with intensity detection.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

from personal_index.text_utils import normalize_whitespace


# --- Enums ---

class SentimentLabel(str, Enum):
    """Sentiment classification labels."""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class SentimentIntensity(str, Enum):
    """Sentiment intensity levels."""
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
    NONE = "none"


# --- Data Classes ---

@dataclass
class SentimentScore:
    """Sentiment scores with compound calculation."""
    positive: float = 0.0
    negative: float = 0.0
    neutral: float = 1.0

    @property
    def compound(self) -> float:
        """Compound score: positive - negative, normalized to [-1, 1]."""
        total = self.positive + self.negative
        if total == 0:
            return 0.0
        return (self.positive - self.negative) / max(total, 1.0)

    @property
    def label(self) -> SentimentLabel:
        """Determine sentiment label from scores."""
        if self.compound > 0.15:
            return SentimentLabel.POSITIVE
        elif self.compound < -0.15:
            return SentimentLabel.NEGATIVE
        return SentimentLabel.NEUTRAL

    @property
    def intensity(self) -> SentimentIntensity:
        """Determine sentiment intensity."""
        abs_compound = abs(self.compound)
        if abs_compound >= 0.6:
            return SentimentIntensity.STRONG
        elif abs_compound >= 0.2:
            return SentimentIntensity.MODERATE
        elif abs_compound > 0.0:
            return SentimentIntensity.WEAK
        return SentimentIntensity.NONE


@dataclass
class SentimentSentenceResult:
    """Sentiment result for a single sentence."""
    text: str
    score: SentimentScore
    words: List[str] = field(default_factory=list)


@dataclass
class SentimentResult:
    """Sentiment analysis result for a text."""
    text: str
    score: SentimentScore
    words: List[str] = field(default_factory=list)
    sentence_count: int = 0


@dataclass
class SentimentDocumentResult:
    """Sentiment analysis result for a full document."""
    text: str
    overall_score: SentimentScore
    sentences: List[SentimentSentenceResult] = field(default_factory=list)
    positive_sentences: int = 0
    negative_sentences: int = 0
    neutral_sentences: int = 0


@dataclass
class SentimentConfig:
    """Configuration for sentiment analysis."""
    min_length: int = 3
    boost_intensifiers: bool = False
    handle_negation: bool = True


# --- Lexicons ---

POSITIVE_WORDS: Dict[str, float] = {
    "good": 0.7, "great": 0.8, "excellent": 0.9, "amazing": 0.9,
    "wonderful": 0.9, "fantastic": 0.9, "awesome": 0.85, "love": 0.8,
    "happy": 0.7, "joy": 0.75, "beautiful": 0.7, "best": 0.9,
    "perfect": 0.9, "brilliant": 0.85, "superb": 0.85, "outstanding": 0.9,
    "impressive": 0.75, "pleasant": 0.6, "nice": 0.5, "fine": 0.4,
    "enjoy": 0.6, "enjoyable": 0.65, "delightful": 0.75, "charming": 0.7,
    "elegant": 0.65, "graceful": 0.6, "kind": 0.6, "generous": 0.65,
    "helpful": 0.6, "useful": 0.5, "valuable": 0.6, "worth": 0.5,
    "success": 0.7, "successful": 0.7, "achieve": 0.6, "achievement": 0.65,
    "progress": 0.5, "improve": 0.6, "improved": 0.6, "better": 0.5,
    "improvement": 0.6, "growth": 0.55, "positive": 0.6, "optimistic": 0.65,
    "hopeful": 0.6, "confident": 0.55, "strong": 0.5, "powerful": 0.6,
    "innovative": 0.65, "creative": 0.6, "inspiring": 0.7, "motivating": 0.65,
    "comfortable": 0.5, "safe": 0.5, "secure": 0.55, "reliable": 0.6,
    "trustworthy": 0.65, "honest": 0.6, "fair": 0.5, "just": 0.5,
    "peaceful": 0.6, "calm": 0.5, "serene": 0.6, "tranquil": 0.6,
    "friendly": 0.6, "warm": 0.5, "welcoming": 0.6, "inviting": 0.55,
    "fresh": 0.4, "clean": 0.4, "clear": 0.4, "bright": 0.5,
    "smart": 0.55, "intelligent": 0.6, "clever": 0.55, "wise": 0.6,
    "fast": 0.4, "quick": 0.4, "efficient": 0.55, "effective": 0.55,
    "recommend": 0.6, "recommended": 0.6, "satisfy": 0.6, "satisfied": 0.6,
    "satisfaction": 0.6, "quality": 0.5, "premium": 0.6, "luxury": 0.65,
    "free": 0.4, "bonus": 0.5, "reward": 0.55, "prize": 0.6,
    "celebrate": 0.65, "celebration": 0.65, "victory": 0.7, "win": 0.6,
    "thank": 0.5, "thanks": 0.5, "appreciate": 0.6, "grateful": 0.65,
    "excited": 0.7, "thrilled": 0.75, "proud": 0.6, "honored": 0.6,
    "fun": 0.5, "funny": 0.4, "entertaining": 0.55, "engaging": 0.6,
    "interesting": 0.45, "fascinating": 0.65, "captivating": 0.7,
    "remarkable": 0.7, "extraordinary": 0.8, "exceptional": 0.85,
    "magnificent": 0.85, "splendid": 0.8, "glorious": 0.8,
    "adventure": 0.5, "adventurous": 0.55, "bold": 0.5, "courageous": 0.65,
    "resilient": 0.6, "determined": 0.55, "dedicated": 0.6, "passionate": 0.65,
}

NEGATIVE_WORDS: Dict[str, float] = {
    "bad": 0.7, "terrible": 0.9, "awful": 0.85, "horrible": 0.9,
    "worst": 0.9, "poor": 0.6, "disappointing": 0.75, "disappointed": 0.75,
    "hate": 0.85, "hated": 0.85, "dislike": 0.6, "annoying": 0.65,
    "frustrating": 0.7, "frustrated": 0.7, "angry": 0.75, "mad": 0.6,
    "sad": 0.6, "unhappy": 0.7, "miserable": 0.85, "depressed": 0.8,
    "ugly": 0.6, "boring": 0.55, "dull": 0.5, "bland": 0.45,
    "slow": 0.5, "broken": 0.7, "fail": 0.7, "failed": 0.7,
    "failure": 0.75, "error": 0.5, "problem": 0.5, "issue": 0.45,
    "bug": 0.5, "crash": 0.65, "crashed": 0.65, "crashes": 0.65,
    "difficult": 0.5, "hard": 0.4, "complex": 0.35, "complicated": 0.4,
    "confusing": 0.55, "confused": 0.55, "unclear": 0.5, "vague": 0.45,
    "weak": 0.5, "flawed": 0.65, "defective": 0.7, "damaged": 0.65,
    "useless": 0.75, "worthless": 0.8, "pointless": 0.65, "meaningless": 0.6,
    "risky": 0.55, "dangerous": 0.7, "unsafe": 0.65, "insecure": 0.6,
    "unreliable": 0.7, "untrustworthy": 0.75, "dishonest": 0.7, "unfair": 0.6,
    "hostile": 0.7, "aggressive": 0.6, "violent": 0.8, "threatening": 0.75,
    "expensive": 0.4, "overpriced": 0.6, "costly": 0.45, "waste": 0.6,
    "wasted": 0.6, "regret": 0.65, "regretted": 0.65, "sorry": 0.5,
    "complaint": 0.55, "complain": 0.55, "complaints": 0.55,
    "scam": 0.85, "fraud": 0.85, "fake": 0.6, "false": 0.5,
    "stupid": 0.65, "dumb": 0.6, "foolish": 0.55, "ridiculous": 0.65,
    "pathetic": 0.75, "lousy": 0.7, "mediocre": 0.55, "inferior": 0.6,
    "obsolete": 0.5, "outdated": 0.5, "old": 0.2, "tired": 0.4,
    "stress": 0.55, "stressful": 0.6, "anxiety": 0.6, "anxious": 0.6,
    "fear": 0.65, "scared": 0.6, "afraid": 0.6, "worried": 0.55,
    "lonely": 0.6, "isolated": 0.5, "abandoned": 0.65, "rejected": 0.6,
    "hurt": 0.6, "pain": 0.6, "painful": 0.65, "suffering": 0.75,
    "tragedy": 0.85, "disaster": 0.8, "catastrophe": 0.9, "crisis": 0.7,
    "loss": 0.6, "losing": 0.6, "defeat": 0.65, "destroy": 0.7,
    "ruin": 0.7, "ruined": 0.7, "collapse": 0.7, "decline": 0.5,
    "negative": 0.55, "pessimistic": 0.6, "hopeless": 0.7, "despair": 0.75,
    "toxic": 0.7, "corrupt": 0.7, "evil": 0.8, "malicious": 0.8,
    "offensive": 0.65, "insulting": 0.65, "rude": 0.55, "impolite": 0.5,
    "irritating": 0.6, "nasty": 0.6, "gross": 0.55, "disgusting": 0.7,
    "shameful": 0.65, "embarrassing": 0.55, "humiliating": 0.7,
    "uncomfortable": 0.5, "awkward": 0.45, "tense": 0.45, "hostile": 0.6,
}

INTENSIFIERS: Dict[str, float] = {
    "very": 1.5, "really": 1.4, "extremely": 1.7, "incredibly": 1.7,
    "absolutely": 1.8, "totally": 1.5, "completely": 1.5, "utterly": 1.7,
    "highly": 1.4, "remarkably": 1.5, "exceptionally": 1.6, "particularly": 1.3,
    "especially": 1.3, "enormously": 1.6, "tremendously": 1.6, "immensely": 1.6,
    "super": 1.4, "most": 1.3, "quite": 1.2, "fairly": 1.1, "rather": 1.1,
    "pretty": 1.2, "so": 1.3, "too": 1.2,
}

DIMINISHERS: Dict[str, float] = {
    "slightly": 0.6, "somewhat": 0.65, "barely": 0.4, "hardly": 0.4,
    "a bit": 0.6, "a little": 0.6, "kind of": 0.6, "sort of": 0.6,
    "mildly": 0.6, "partially": 0.6, "mostly": 0.8, "largely": 0.8,
    "generally": 0.8, "usually": 0.8, "often": 0.8,
}

NEGATORS: set = {
    "not", "no", "never", "neither", "nor", "nothing", "nowhere",
    "nobody", "none", "cannot", "can't", "don't", "doesn't", "didn't",
    "won't", "wouldn't", "shouldn't", "couldn't", "isn't", "aren't",
    "wasn't", "weren't", "haven't", "hasn't", "hadn't", "donot",
    "dont", "doesnt", "didnt", "wont", "wouldnt", "shouldnt", "couldnt",
    "isnt", "arent", "wasnt", "werent", "havent", "hasnt", "hadnt",
}


class SentimentAnalyzer:
    """Lexicon-based sentiment analyzer for text content."""

    def __init__(self, config: Optional[SentimentConfig] = None):
        self.config = config or SentimentConfig()

    def analyze(self, text: str) -> SentimentResult:
        """Analyze sentiment of a text string."""
        if not text or not text.strip():
            return SentimentResult(
                text=text,
                score=SentimentScore(positive=0.0, negative=0.0, neutral=1.0),
            )

        normalized = normalize_whitespace(text).lower()
        tokens = self._tokenize(normalized)

        if not tokens:
            return SentimentResult(
                text=text,
                score=SentimentScore(positive=0.0, negative=0.0, neutral=1.0),
            )

        pos_score = 0.0
        neg_score = 0.0
        sentiment_words: List[str] = []

        for i, token in enumerate(tokens):
            if len(token) < self.config.min_length:
                continue

            # Check for negation
            negated = False
            if self.config.handle_negation:
                for j in range(max(0, i - 3), i):
                    if tokens[j] in NEGATORS:
                        negated = True
                        break

            # Check for intensifier
            intensifier = 1.0
            if self.config.boost_intensifiers:
                for j in range(max(0, i - 2), i):
                    if tokens[j] in INTENSIFIERS:
                        intensifier = INTENSIFIERS[tokens[j]]
                        break
                    elif tokens[j] in DIMINISHERS:
                        intensifier = DIMINISHERS[tokens[j]]
                        break

            # Look up sentiment
            if token in POSITIVE_WORDS:
                score = POSITIVE_WORDS[token] * intensifier
                if negated:
                    neg_score += score * 0.7
                else:
                    pos_score += score
                sentiment_words.append(token)
            elif token in NEGATIVE_WORDS:
                score = NEGATIVE_WORDS[token] * intensifier
                if negated:
                    pos_score += score * 0.3
                else:
                    neg_score += score
                sentiment_words.append(token)

        # Normalize scores
        total = pos_score + neg_score
        if total > 0:
            pos_norm = pos_score / total
            neg_norm = neg_score / total
            neutral_norm = max(0, 1.0 - pos_norm - neg_norm)
        else:
            pos_norm = 0.0
            neg_norm = 0.0
            neutral_norm = 1.0

        # Count sentences
        sentence_count = max(len(re.split(r"[.!?]+", text)), 1)

        score = SentimentScore(
            positive=round(pos_norm, 4),
            negative=round(neg_norm, 4),
            neutral=round(neutral_norm, 4),
        )

        return SentimentResult(
            text=text,
            score=score,
            words=sentiment_words,
            sentence_count=sentence_count,
        )

    def analyze_batch(self, texts: List[str]) -> List[SentimentResult]:
        """Analyze sentiment for multiple texts."""
        return [self.analyze(text) for text in texts]

    def analyze_document(self, text: str) -> SentimentDocumentResult:
        """Analyze sentiment at document level with sentence breakdown."""
        if not text or not text.strip():
            return SentimentDocumentResult(
                text=text,
                overall_score=SentimentScore(positive=0.0, negative=0.0, neutral=1.0),
            )

        # Split into sentences
        sentences = re.split(r"(?<=[.!?])\s+", text)
        sentences = [s.strip() for s in sentences if s.strip()]

        sentence_results: List[SentimentSentenceResult] = []
        total_pos = 0.0
        total_neg = 0.0
        total_neutral = 0.0
        pos_count = 0
        neg_count = 0
        neu_count = 0

        for sentence in sentences:
            result = self.analyze(sentence)
            sentence_results.append(SentimentSentenceResult(
                text=sentence,
                score=result.score,
                words=result.words,
            ))
            total_pos += result.score.positive
            total_neg += result.score.negative
            total_neutral += result.score.neutral

            if result.score.label == SentimentLabel.POSITIVE:
                pos_count += 1
            elif result.score.label == SentimentLabel.NEGATIVE:
                neg_count += 1
            else:
                neu_count += 1

        # Average scores across sentences
        n = max(len(sentence_results), 1)
        overall = SentimentScore(
            positive=round(total_pos / n, 4),
            negative=round(total_neg / n, 4),
            neutral=round(total_neutral / n, 4),
        )

        return SentimentDocumentResult(
            text=text,
            overall_score=overall,
            sentences=sentence_results,
            positive_sentences=pos_count,
            negative_sentences=neg_count,
            neutral_sentences=neu_count,
        )

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """Simple tokenizer for sentiment analysis."""
        return re.findall(r"\b[a-z']+\b", text.lower())
