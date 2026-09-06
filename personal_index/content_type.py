"""Content type detection and classification utilities."""

from __future__ import annotations

import mimetypes
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ContentTypeInfo:
    """Information about detected content type."""

    mime_type: str
    category: str  # "text", "image", "video", "audio", "media", "document", "archive", "unknown"
    extension: str
    is_text: bool
    is_media: bool
    is_document: bool
    encoding: str = "utf-8"

    @property
    def is_downloadable(self) -> bool:
        """Whether this content type should be downloaded."""
        return self.is_document or self.is_text


# Category mappings
CATEGORY_MAP = {
    "text": "text",
    "image": "image",
    "video": "video",
    "audio": "audio",
    "application/json": "text",
    "application/xml": "text",
    "application/javascript": "text",
    "application/pdf": "document",
    "application/msword": "document",
    "application/vnd.openxmlformats-officedocument": "document",
    "application/zip": "archive",
    "application/gzip": "archive",
    "application/x-tar": "archive",
    "application/x-rar": "archive",
    "application/octet-stream": "unknown",
}

# Known text extensions
TEXT_EXTENSIONS = {
    ".txt", ".md", ".rst", ".html", ".htm", ".xml", ".json", ".yaml",
    ".yml", ".csv", ".tsv", ".py", ".js", ".ts", ".java", ".c", ".cpp",
    ".h", ".css", ".sql", ".sh", ".bash", ".zsh", ".rb", ".go", ".rs",
    ".php", ".pl", ".lua", ".r", ".ipynb", ".toml", ".ini", ".cfg",
    ".conf", ".env", ".log", ".tex", ".bib", ".svg", ".graphql",
}

# Known document extensions
DOCUMENT_EXTENSIONS = {
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".odt", ".ods", ".odp", ".epub", ".mobi", ".djvu",
}

# Known media extensions
MEDIA_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".ico",
    ".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm",
    ".mp3", ".wav", ".flac", ".ogg", ".aac", ".wma",
}

# Known archive extensions
ARCHIVE_EXTENSIONS = {
    ".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".rar", ".tgz",
}


class ContentTypeDetector:
    """Detects and classifies content types from URLs, filenames, or raw data."""

    def __init__(self) -> None:
        self._mime_cache: dict[str, ContentTypeInfo] = {}

    def detect_from_url(self, url: str) -> ContentTypeInfo:
        """Detect content type from a URL.

        Args:
            url: The URL to analyze.

        Returns:
            ContentTypeInfo with detected type information.
        """
        # Try to get extension from URL path
        path = url.split("?")[0].split("#")[0]
        ext = self._get_extension(path)

        if ext:
            return self.detect_from_extension(ext)

        # Try mimetypes
        mime_type, _ = mimetypes.guess_type(url)
        if mime_type:
            return self._make_info(mime_type, ext or "")

        return ContentTypeInfo(
            mime_type="application/octet-stream",
            category="unknown",
            extension="",
            is_text=False,
            is_media=False,
            is_document=False,
        )

    def detect_from_filename(self, filename: str) -> ContentTypeInfo:
        """Detect content type from a filename.

        Args:
            filename: The filename to analyze.

        Returns:
            ContentTypeInfo with detected type information.
        """
        ext = self._get_extension(filename)
        if ext:
            return self.detect_from_extension(ext)

        mime_type, _ = mimetypes.guess_type(filename)
        if mime_type:
            return self._make_info(mime_type, ext or "")

        return ContentTypeInfo(
            mime_type="application/octet-stream",
            category="unknown",
            extension="",
            is_text=False,
            is_media=False,
            is_document=False,
        )

    def _classify_category_from_ext(self, ext: str) -> tuple[str, str]:
        """Classify a file extension into a category and MIME type.

        Args:
            ext: File extension (with leading dot).

        Returns:
            Tuple of (category, mime_type).
        """
        if ext in TEXT_EXTENSIONS:
            return "text", "text/plain"
        if ext in DOCUMENT_EXTENSIONS:
            mime_type, _ = mimetypes.guess_type(f"file{ext}")
            return "document", mime_type or "application/octet-stream"
        if ext in MEDIA_EXTENSIONS:
            mime_type, _ = mimetypes.guess_type(f"file{ext}")
            if ext in {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".ico"}:
                return "image", mime_type or "application/octet-stream"
            return "media", mime_type or "application/octet-stream"
        if ext in ARCHIVE_EXTENSIONS:
            if ext == ".zip":
                return "archive", "application/zip"
            return "archive", "application/x-archive"
        return "unknown", "application/octet-stream"

    def detect_from_extension(self, ext: str) -> ContentTypeInfo:
        """Detect content type from a file extension.

        Args:
            ext: File extension (with or without leading dot).

        Returns:
            ContentTypeInfo with detected type information.
        """
        ext = ext.lower() if ext.startswith(".") else f".{ext.lower()}"
        cache_key = f"ext:{ext}"
        if cache_key in self._mime_cache:
            return self._mime_cache[cache_key]

        category, mime_type = self._classify_category_from_ext(ext)

        info = ContentTypeInfo(
            mime_type=mime_type,
            category=category,
            extension=ext,
            is_text=category == "text",
            is_media=category in ("image", "video", "audio", "media"),
            is_document=category == "document",
        )

        self._mime_cache[cache_key] = info
        return info

    def _check_magic_numbers(self, data: bytes) -> ContentTypeInfo | None:
        """Check magic number patterns in raw bytes.

        Args:
            data: Raw bytes to analyze.

        Returns:
            ContentTypeInfo for a match, or None if no magic number matched.
        """
        if data[:4] == b"%PDF":
            return self._make_info("application/pdf", ".pdf")
        if data[:2] == b"\x1f\x8b":
            return self._make_info("application/gzip", ".gz")
        if data[:4] == b"PK\x03\x04":
            return self._make_info("application/zip", ".zip")
        if data[:8] == b"\x89PNG\r\n\x1a\n":
            return self._make_info("image/png", ".png")
        if data[:2] == b"\xff\xd8":
            return self._make_info("image/jpeg", ".jpg")
        if data[:6] in (b"GIF87a", b"GIF89a"):
            return self._make_info("image/gif", ".gif")
        if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
            return self._make_info("image/webp", ".webp")
        return None

    def _unknown_type(self) -> ContentTypeInfo:
        """Return default unknown content type info."""
        return ContentTypeInfo(
            mime_type="application/octet-stream",
            category="unknown",
            extension="",
            is_text=False,
            is_media=False,
            is_document=False,
        )

    def _try_detect_text(self, data: bytes) -> ContentTypeInfo | None:
        """Try to detect text by checking for null bytes."""
        try:
            text = data.decode("utf-8")
            if "\x00" not in text:
                return self._make_info("text/plain", ".txt")
        except (UnicodeDecodeError, ValueError):
            pass
        return None

    def detect_from_bytes(self, data: bytes) -> ContentTypeInfo:
        """Detect content type from raw bytes.

        Tries magic number detection first, then falls back to text detection
        (UTF-8 decode with null-byte check), returning unknown if neither
        matches. Empty input returns unknown.

        Args:
            data: Raw bytes to analyze.

        Returns:
            ContentTypeInfo with detected type information.
        """
        if not data:
            return self._unknown_type()

        result = self._check_magic_numbers(data)
        if result is not None:
            return result

        text_result = self._try_detect_text(data)
        if text_result is not None:
            return text_result

        return self._unknown_type()

    def classify(self, content_type: str) -> str:
        """Classify a MIME type into a category.

        Args:
            content_type: MIME type string.

        Returns:
            Category string: text, image, video, audio, document, archive, unknown.
        """
        if not content_type:
            return "unknown"

        # Direct match
        if content_type in CATEGORY_MAP:
            return CATEGORY_MAP[content_type]

        # Prefix match
        for prefix, category in CATEGORY_MAP.items():
            if content_type.startswith(prefix):
                return category

        # Fallback based on major type
        major = content_type.split("/")[0] if "/" in content_type else ""
        if major == "text":
            return "text"
        if major == "image":
            return "image"
        if major == "video":
            return "video"
        if major == "audio":
            return "audio"

        return "unknown"

    def should_index(self, url: str, content_type: str | None = None) -> bool:
        """Determine if content at URL should be indexed.

        Args:
            url: The URL to check.
            content_type: Optional known MIME type.

        Returns:
            True if the content should be indexed.
        """
        if content_type:
            category = self.classify(content_type)
        else:
            info = self.detect_from_url(url)
            category = info.category

        # Index text and documents, skip media and archives
        return category in ("text", "document")

    def _get_extension(self, path: str) -> str:
        """Extract file extension from path."""
        # Handle query strings and fragments
        clean = path.split("?")[0].split("#")[0]
        return Path(clean).suffix.lower()

    def _make_info(self, mime_type: str, ext: str) -> ContentTypeInfo:
        """Create a ContentTypeInfo from MIME type and extension."""
        category = self.classify(mime_type)
        return ContentTypeInfo(
            mime_type=mime_type,
            category=category,
            extension=ext,
            is_text=category == "text",
            is_media=category in ("image", "video", "audio"),
            is_document=category == "document",
        )
