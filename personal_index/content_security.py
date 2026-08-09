"""Content security module - CSP, XSS protection, and security headers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ContentSecurityPolicy:
    """Content Security Policy builder for generating CSP headers."""

    report_only: bool = False
    directives: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Set default directives if not overridden."""
        if "default-src" not in self.directives:
            self.directives["default-src"] = "'self'"

    def add_directive(self, name: str, value: str) -> None:
        """Add or update a CSP directive.

        Args:
            name: Directive name (e.g., 'script-src', 'img-src').
            value: Directive value (e.g., "'self' https://cdn.example.com").
        """
        self.directives[name] = value

    def build_header(self) -> str:
        """Build the full CSP header string.

        Returns:
            The complete Content-Security-Policy header value.
        """
        parts = []
        for name, value in self.directives.items():
            parts.append(f"{name} {value}")
        return "; ".join(parts)

    def get_header_name(self) -> str:
        """Get the appropriate header name based on mode.

        Returns:
            'Content-Security-Policy-Report-Only' if report_only,
            otherwise 'Content-Security-Policy'.
        """
        if self.report_only:
            return "Content-Security-Policy-Report-Only"
        return "Content-Security-Policy"


@dataclass
class SecurityHeaders:
    """Collection of security-related HTTP headers."""

    csp: Optional[ContentSecurityPolicy] = None
    x_frame_options: str = "DENY"
    x_content_type_options: str = "nosniff"
    x_xss_protection: str = "1; mode=block"
    referrer_policy: str = "strict-origin-when-cross-origin"
    permissions_policy: str = "camera=(), microphone=(), geolocation=()"

    def get_headers(self) -> dict[str, str]:
        """Get all security headers as a dictionary.

        Returns:
            Dictionary of header name to header value.
        """
        headers: dict[str, str] = {
            "X-Frame-Options": self.x_frame_options,
            "X-Content-Type-Options": self.x_content_type_options,
            "X-XSS-Protection": self.x_xss_protection,
            "Referrer-Policy": self.referrer_policy,
            "Permissions-Policy": self.permissions_policy,
        }
        if self.csp:
            headers[self.csp.get_header_name()] = self.csp.build_header()
        return headers


class XssSanitizer:
    """Utility for sanitizing content against XSS attacks."""

    DANGEROUS_TAGS = {
        "script", "iframe", "object", "embed", "applet",
        "form", "input", "button", "link", "meta", "base",
    }

    DANGEROUS_ATTRIBUTES = {
        "onclick", "onload", "onerror", "onmouseover", "onfocus",
        "onblur", "onsubmit", "onchange", "onkeydown", "onkeyup",
        "onmouseout", "ondblclick", "oncontextmenu", "ondrag",
        "oninput", "oninvalid", "onreset", "onselect", "ontouchstart",
    }

    @classmethod
    def strip_tags(cls, html: str) -> str:
        """Remove all HTML tags from content.

        Args:
            html: Raw HTML string.

        Returns:
            Plain text with all tags removed.
        """
        result = []
        in_tag = False
        for char in html:
            if char == "<":
                in_tag = True
            elif char == ">":
                in_tag = False
                result.append(" ")
            elif not in_tag:
                result.append(char)
        return "".join(result).strip()

    @classmethod
    def remove_dangerous_tags(cls, html: str) -> str:
        """Remove only dangerous HTML tags while preserving safe ones.

        Args:
            html: Raw HTML string.

        Returns:
            HTML with dangerous tags removed.
        """
        result = []
        i = 0
        while i < len(html):
            if html[i] == "<":
                tag_end = html.find(">", i)
                if tag_end != -1:
                    tag_content = html[i + 1:tag_end].strip()
                    tag_name = tag_content.split()[0].lower() if tag_content else ""
                    if tag_name not in cls.DANGEROUS_TAGS:
                        result.append(html[i:tag_end + 1])
                    i = tag_end + 1
                    continue
            result.append(html[i])
            i += 1
        return "".join(result)

    @classmethod
    def sanitize_input(cls, text: str) -> str:
        """Sanitize user input for safe display.

        Args:
            text: Raw user input string.

        Returns:
            Sanitized string safe for HTML display.
        """
        replacements = {
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#x27;",
            "/": "&#x2F;",
        }
        result = text
        for char, replacement in replacements.items():
            result = result.replace(char, replacement)
        return result
