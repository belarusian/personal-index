"""NLP utilities for text analysis in personal-index.

Provides tokenization, lemmatization, stemming, POS tagging,
and text statistics without external NLP library dependencies.
"""

from __future__ import annotations

import re
import string
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from personal_index.text_utils import STOPWORDS, normalize_whitespace, tokenize


# --- Enums ---

class NLPPOS:
    """Part-of-speech tag constants."""
    NOUN = "NN"
    VERB = "VB"
    ADJ = "JJ"
    ADV = "RB"
    PRON = "PRP"
    DET = "DT"
    PREP = "IN"
    CONJ = "CC"
    ADP = "ADP"
    NUM = "CD"
    PUNCT = "."
    UNKNOWN = "XX"


# --- Data Classes ---

@dataclass
class NLPLemma:
    """A word with its lemma."""
    word: str
    lemma: str
    pos: str = NLPPOS.UNKNOWN


@dataclass
class NLPStem:
    """A word with its stem."""
    word: str
    stem: str


@dataclass
class NLPTextAnalysisResult:
    """Result of text analysis with various statistics."""
    word_count: int = 0
    char_count: int = 0
    sentence_count: int = 0
    paragraph_count: int = 0
    avg_word_length: float = 0.0
    unique_word_count: int = 0
    vocabulary_richness: float = 0.0
    readability_score: float = 0.0
    syllable_count: int = 0
    avg_sentence_length: float = 0.0
    top_words: List[Tuple[str, int]] = field(default_factory=list)


@dataclass
class NLPConfig:
    """Configuration for NLP processing."""
    lowercase: bool = True
    remove_stopwords: bool = True
    remove_punctuation: bool = True
    min_token_length: int = 2
    max_tokens: Optional[int] = None


# --- Tokenizer ---

class NLPTokenizer:
    """Tokenize text into words with configurable options."""

    def __init__(
        self,
        lowercase: bool = True,
        remove_stopwords: bool = False,
        remove_punctuation: bool = True,
        min_token_length: int = 2,
        max_tokens: Optional[int] = None,
    ):
        self.lowercase = lowercase
        self.remove_stopwords = remove_stopwords
        self.remove_punctuation = remove_punctuation
        self.min_token_length = min_token_length
        self.max_tokens = max_tokens

    def tokenize(self, text: str) -> List[str]:
        """Tokenize text into a list of word tokens."""
        if not text:
            return []

        if self.remove_punctuation:
            text = text.translate(str.maketrans("", "", string.punctuation))

        tokens = re.findall(r"\b\w+\b", text)

        if self.lowercase:
            tokens = [t.lower() for t in tokens]

        tokens = [t for t in tokens if len(t) >= self.min_token_length]

        if self.remove_stopwords:
            tokens = [t for t in tokens if t.lower() not in STOPWORDS]

        if self.max_tokens:
            tokens = tokens[: self.max_tokens]

        return tokens

    def tokenize_with_positions(self, text: str) -> List[Tuple[str, int, int]]:
        """Tokenize text returning (token, start_pos, end_pos) tuples."""
        if not text:
            return []

        results = []
        pattern = re.compile(r"\b\w+\b")
        for match in pattern.finditer(text):
            token = match.group()
            if self.lowercase:
                token = token.lower()
            if len(token) >= self.min_token_length:
                if not self.remove_stopwords or token.lower() not in STOPWORDS:
                    results.append((token, match.start(), match.end()))
                    if self.max_tokens and len(results) >= self.max_tokens:
                        break
        return results


# --- Lemmatizer (rule-based) ---

class NLPLemmatizer:
    """Rule-based English lemmatizer for common suffixes."""

    # Common suffix rules: (suffix, replacement, min_length)
    SUFFIX_RULES: List[Tuple[str, str, int]] = [
        ("ies", "y", 5),
        ("ves", "ve", 5),
        ("ches", "ch", 6),
        ("shes", "she", 5),
        ("ses", "s", 4),
        ("sses", "ss", 5),
        ("xes", "x", 4),
        ("zes", "z", 4),
        ("es", "e", 4),
        ("s", "", 4),
        ("ed", "e", 4),
        ("ing", "e", 5),
        ("tion", "te", 6),
        ("sion", "se", 6),
        ("ment", "", 6),
        ("ness", "", 6),
        ("able", "", 6),
        ("ible", "", 6),
        ("ful", "", 5),
        ("less", "", 6),
        ("ous", "", 5),
        ("ive", "", 5),
        ("al", "", 4),
        ("ly", "", 4),
        ("er", "", 4),
        ("est", "e", 5),
    ]

    def lemmatize(self, word: str) -> str:
        """Lemmatize a single word using suffix rules."""
        if not word:
            return ""

        original = word.lower()

        for suffix, replacement, min_len in self.SUFFIX_RULES:
            if original.endswith(suffix) and len(original) >= min_len:
                lemma = original[: -len(suffix)] + replacement
                if len(lemma) >= 2:
                    return lemma

        return original

    def lemmatize_list(self, words: List[str]) -> List[str]:
        """Lemmatize a list of words."""
        return [self.lemmatize(w) for w in words]

    def lemmatize_text(self, text: str) -> str:
        """Lemmatize all words in a text, returning the lemmatized text."""
        if not text:
            return ""
        tokens = tokenize(text, lowercase=True)
        lemmas = self.lemmatize_list(tokens)
        return " ".join(lemmas)

    def lemmatize_with_pos(self, words: List[str]) -> List[NLPLemma]:
        """Lemmatize words with basic POS detection."""
        results = []
        for word in words:
            pos = self._guess_pos(word)
            lemma = self.lemmatize(word)
            results.append(NLPLemma(word=word, lemma=lemma, pos=pos))
        return results

    @staticmethod
    def _guess_pos(word: str) -> str:
        """Guess the POS tag of a word based on suffixes."""
        w = word.lower()
        if w.endswith(("ing", "ed", "ate", "ize")):
            return NLPPOS.VERB
        if w.endswith(("tion", "sion", "ment", "ness", "ity")):
            return NLPPOS.NOUN
        if w.endswith(("ly", "ward")):
            return NLPPOS.ADV
        if w.endswith(("ful", "less", "ous", "ive", "al", "able", "ible")):
            return NLPPOS.ADJ
        if w.endswith(("s", "es")) and len(w) > 3:
            return NLPPOS.NOUN
        return NLPPOS.UNKNOWN


# --- Stemmer (rule-based Porter-like) ---

class NLPStemmer:
    """Rule-based English stemmer (simplified Porter algorithm)."""

    VOWELS = set("aeiou")

    def stem(self, word: str) -> str:
        """Stem a single word."""
        if not word:
            return ""

        w = word.lower()

        # Step 1a: plurals and verb endings
        if w.endswith("sses"):
            w = w[:-2]
        elif w.endswith("ies"):
            w = w[:-3] + "y"
        elif w.endswith("ss"):
            pass
        elif w.endswith("s") and not w.endswith("us") and not w.endswith("ss"):
            w = w[:-1]

        # Step 1b: ed/ing endings
        suffix = ""
        if w.endswith("eed"):
            if self._measure(w[:-3]) > 0:
                w = w[:-1]
        elif w.endswith(("ed", "ing")):
            base = w[:-2] if w.endswith("ed") else w[:-3]
            if self._measure(base) > 0:
                w = base
                if w.endswith(("at", "bl", "iz")):
                    w += "e"
                elif self._measure(w) == 1 and self._cvc(w):
                    w += w[-1]
            elif w.endswith("eed") and self._measure(w[:-3]) > 0:
                w = w[:-1]

        # Step 1c: terminal y
        if w.endswith("y") and self._measure(w[:-1]) > 0:
            w = w[:-1] + "i"

        # Step 2: double suffixes
        step2_rules = {
            "ational": "ate", "tional": "tion", "enci": "ence",
            "anci": "ance", "izer": "ize", "abli": "able",
            "alli": "al", "entli": "ent", "eli": "e",
            "ousli": "ous", "ization": "ize", "ation": "ate",
            "ator": "ate", "alism": "al", "iveness": "ive",
            "fulness": "ful", "ousness": "ous", "aliti": "al",
            "iviti": "ive", "biliti": "ble", "logi": "log",
        }
        for suffix, replacement in step2_rules.items():
            if w.endswith(suffix) and self._measure(w[:-len(suffix)]) > 0:
                w = w[:-len(suffix)] + replacement
                break

        # Step 3
        step3_rules = {
            "icate": "ic", "ative": "", "alize": "al",
            "iciti": "ic", "ical": "ic", "ful": "",
            "ness": "",
        }
        for suffix, replacement in step3_rules.items():
            if w.endswith(suffix) and self._measure(w[:-len(suffix)]) > 0:
                w = w[:-len(suffix)] + replacement
                break

        # Step 4
        step4_suffixes = [
            "al", "ance", "ence", "er", "ic", "able", "ible",
            "ant", "ement", "ment", "ent", "ion", "ou",
            "ism", "ate", "iti", "ous", "ive", "ize",
        ]
        for suffix in step4_suffixes:
            if w.endswith(suffix):
                base = w[:-len(suffix)]
                if suffix == "ion" and w[-3] not in "st":
                    continue
                if self._measure(base) > 1:
                    w = base
                    break

        # Step 5a: trailing e
        if self._measure(w[:-1]) > 1:
            if w.endswith("e"):
                w = w[:-1]
        elif self._measure(w[:-1]) == 1 and not self._cvc(w[:-1]):
            if w.endswith("e"):
                w = w[:-1]

        # Step 5b: trailing l
        if self._measure(w[:-1]) > 1 and w.endswith("ll"):
            w = w[:-1]

        return w

    def stem_list(self, words: List[str]) -> List[str]:
        """Stem a list of words."""
        return [self.stem(w) for w in words]

    def stem_text(self, text: str) -> str:
        """Stem all words in a text."""
        if not text:
            return ""
        tokens = tokenize(text, lowercase=True)
        stems = self.stem_list(tokens)
        return " ".join(stems)

    def _measure(self, word: str) -> int:
        """Count VC patterns in word (stem measure)."""
        if not word:
            return 0
        count = 0
        i = 0
        while i < len(word):
            if word[i] in self.VOWELS:
                count += 1
                while i < len(word) and word[i] in self.VOWELS:
                    i += 1
            else:
                while i < len(word) and word[i] not in self.VOWELS:
                    i += 1
        return count

    @staticmethod
    def _cvc(word: str) -> bool:
        """Check if word ends in consonant-vowel-consonant pattern."""
        if len(word) < 3:
            return False
        return (
            word[-1] not in "aeiouy"
            and word[-2] in "aeiouy"
            and word[-3] not in "aeiouy"
            and word[-1] not in "wx"
        )


# --- POS Tagger (rule-based) ---

class NLPPOSTagger:
    """Rule-based part-of-speech tagger using suffix heuristics."""

    SUFFIX_PATTERNS: List[Tuple[str, str]] = [
        ("ing", NLPPOS.VERB), ("ed", NLPPOS.VERB), ("ate", NLPPOS.VERB),
        ("ize", NLPPOS.VERB), ("ify", NLPPOS.VERB), ("ise", NLPPOS.VERB),
        ("tion", NLPPOS.NOUN), ("sion", NLPPOS.NOUN), ("ment", NLPPOS.NOUN),
        ("ness", NLPPOS.NOUN), ("ity", NLPPOS.NOUN), ("ance", NLPPOS.NOUN),
        ("ence", NLPPOS.NOUN), ("ity", NLPPOS.NOUN),
        ("ly", NLPPOS.ADV), ("ward", NLPPOS.ADV),
        ("ful", NLPPOS.ADJ), ("less", NLPPOS.ADJ), ("ous", NLPPOS.ADJ),
        ("ive", NLPPOS.ADJ), ("al", NLPPOS.ADJ), ("able", NLPPOS.ADJ),
        ("ible", NLPPOS.ADJ), ("ary", NLPPOS.ADJ), ("ory", NLPPOS.ADJ),
        ("ent", NLPPOS.ADJ), ("ant", NLPPOS.ADJ),
    ]

    COMMON_DETERMINERS = {"the", "a", "an", "this", "that", "these", "those"}
    COMMON_PRONOUNS = {"i", "you", "he", "she", "it", "we", "they",
                       "me", "him", "her", "us", "them", "my", "your",
                       "his", "its", "our", "their", "mine", "yours"}
    COMMON_PREPOSITIONS = {"in", "on", "at", "to", "for", "with", "by",
                           "from", "of", "about", "into", "through", "during",
                           "before", "after", "above", "below", "between"}
    COMMON_CONJUNCTIONS = {"and", "or", "but", "nor", "yet", "so", "because"}

    def tag(self, text: str) -> List[Tuple[str, str]]:
        """Tag words in text with POS tags. Returns list of (word, tag) tuples."""
        if not text:
            return []
        tokens = tokenize(text, lowercase=True)
        return [(word, self._tag_word(word)) for word in tokens]

    def tag_word(self, word: str) -> str:
        """Tag a single word."""
        return self._tag_word(word)

    def get_pos_counts(self, text: str) -> Dict[str, int]:
        """Get count of each POS tag in text."""
        tags = self.tag(text)
        counts: Dict[str, int] = {}
        for _, tag in tags:
            counts[tag] = counts.get(tag, 0) + 1
        return counts

    def get_nouns(self, text: str) -> List[str]:
        """Extract nouns from text."""
        return [word for word, tag in self.tag(text) if tag == NLPPOS.NOUN]

    def get_verbs(self, text: str) -> List[str]:
        """Extract verbs from text."""
        return [word for word, tag in self.tag(text) if tag == NLPPOS.VERB]

    def get_adjectives(self, text: str) -> List[str]:
        """Extract adjectives from text."""
        return [word for word, tag in self.tag(text) if tag == NLPPOS.ADJ]

    @staticmethod
    def _tag_word(word: str) -> str:
        """Tag a single word using heuristics."""
        w = word.lower()

        if w in NLPPOSTagger.COMMON_DETERMINERS:
            return NLPPOS.DET
        if w in NLPPOSTagger.COMMON_PRONOUNS:
            return NLPPOS.PRON
        if w in NLPPOSTagger.COMMON_PREPOSITIONS:
            return NLPPOS.PREP
        if w in NLPPOSTagger.COMMON_CONJUNCTIONS:
            return NLPPOS.CONJ
        if w.isdigit():
            return NLPPOS.NUM

        for suffix, pos in NLPPOSTagger.SUFFIX_PATTERNS:
            if w.endswith(suffix) and len(w) > len(suffix):
                return pos

        return NLPPOS.UNKNOWN


# --- Text Statistics ---

class NLPTextStats:
    """Compute text statistics and readability metrics."""

    def compute(self, text: str) -> NLPTextAnalysisResult:
        """Compute comprehensive text statistics."""
        if not text:
            return NLPTextAnalysisResult()

        normalized = normalize_whitespace(text)
        chars = len(normalized)
        words = normalized.split()
        word_count = len(words)

        # Sentences
        sentences = re.split(r"[.!?]+", normalized)
        sentences = [s.strip() for s in sentences if s.strip()]
        sentence_count = max(len(sentences), 1)

        # Paragraphs
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        paragraph_count = max(len(paragraphs), 1)

        # Unique words
        lower_words = [w.lower().strip(string.punctuation) for w in words]
        lower_words = [w for w in lower_words if w]
        unique_words = set(lower_words)
        unique_word_count = len(unique_words)

        # Vocabulary richness (type-token ratio)
        vocabulary_richness = unique_word_count / word_count if word_count > 0 else 0.0

        # Average word length
        total_word_len = sum(len(w) for w in lower_words)
        avg_word_length = total_word_len / word_count if word_count > 0 else 0.0

        # Average sentence length
        avg_sentence_length = word_count / sentence_count if sentence_count > 0 else 0.0

        # Syllable count (approximate)
        syllable_count = self._count_syllables(normalized)

        # Readability score (Flesch-Kincaid approximation)
        readability = 206.835 - (1.015 * avg_sentence_length) - (84.6 * (syllable_count / word_count if word_count > 0 else 0))
        readability = max(0, min(100, readability))

        # Top words
        word_freq = Counter(lower_words)
        top_words = word_freq.most_common(10)

        return NLPTextAnalysisResult(
            word_count=word_count,
            char_count=chars,
            sentence_count=sentence_count,
            paragraph_count=paragraph_count,
            avg_word_length=round(avg_word_length, 2),
            unique_word_count=unique_word_count,
            vocabulary_richness=round(vocabulary_richness, 4),
            readability_score=round(readability, 2),
            syllable_count=syllable_count,
            avg_sentence_length=round(avg_sentence_length, 2),
            top_words=top_words,
        )

    @staticmethod
    def _count_syllables(text: str) -> int:
        """Approximate syllable count using vowel group heuristic."""
        count = 0
        in_vowel = False
        vowels = set("aeiouAEIOU")
        for char in text:
            is_vowel = char in vowels
            if is_vowel and not in_vowel:
                count += 1
                in_vowel = True
            elif not is_vowel:
                in_vowel = False
        # Adjust for silent e
        if text.lower().endswith("e") and count > 1:
            count -= 1
        return max(count, 1)
