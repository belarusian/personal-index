"""Content security module - CSP, XSS protection, and security headers."""

from __future__ import annotations

import re
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
            Plain text with all tags removed, whitespace collapsed.
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
        text = "".join(result)
        # Collapse multiple spaces into one
        return re.sub(r"\s+", " ", text).strip()

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


class InputValidator:
    """Utility for validating user input against common attack vectors."""

    EMAIL_PATTERN = re.compile(
        r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    )
    URL_PATTERN = re.compile(
        r"^https?://[a-zA-Z0-9.-]+(:\d+)?(/[a-zA-Z0-9._~:/?#\[\]@!$&'()*+,;=-]*)?$"
    )

    @classmethod
    def is_valid_email(cls, email: str) -> bool:
        """Validate email format.

        Args:
            email: Email address to validate.

        Returns:
            True if the email format is valid.
        """
        if not email or len(email) > 254:
            return False
        return bool(cls.EMAIL_PATTERN.match(email))

    @classmethod
    def is_valid_url(cls, url: str) -> bool:
        """Validate URL format (requires http/https scheme).

        Args:
            url: URL to validate.

        Returns:
            True if the URL format is valid.
        """
        if not url or len(url) > 2048:
            return False
        return bool(cls.URL_PATTERN.match(url))

    @classmethod
    def check_max_length(cls, text: str, max_length: int) -> bool:
        """Check if text length is within allowed maximum.

        Args:
            text: Text to check.
            max_length: Maximum allowed length.

        Returns:
            True if text length is within limit.
        """
        return len(text) <= max_length

    @classmethod
    def check_allowed_chars(cls, text: str, allowed: str) -> bool:
        """Check if text contains only allowed characters.

        Args:
            text: Text to check.
            allowed: String of all allowed characters.

        Returns:
            True if all characters in text are in allowed set.
        """
        allowed_set = set(allowed)
        return all(c in allowed_set for c in text)


@dataclass
class SecurityAudit:
    """Security audit scanner for checking headers and configurations."""

    REQUIRED_HEADERS: list[str] = field(default_factory=lambda: [
        "X-Frame-Options",
        "X-Content-Type-Options",
        "X-XSS-Protection",
        "Content-Security-Policy",
        "Referrer-Policy",
    ])

    def scan_headers(self, headers: dict[str, str]) -> list[str]:
        """Scan headers for security issues.

        Args:
            headers: Dictionary of HTTP headers to audit.

        Returns:
            List of issue descriptions. Empty if no issues found.
        """
        issues: list[str] = []
        header_keys = {k.lower() for k in headers}

        for required in self.REQUIRED_HEADERS:
            if required.lower() not in header_keys:
                issues.append(f"Missing required header: {required}")

        # Check for weak CSP
        csp_value = headers.get("Content-Security-Policy", "")
        if csp_value and "*" in csp_value:
            issues.append("CSP contains wildcard (*) which is insecure")

        # Check for unsafe-inline in CSP
        if csp_value and "'unsafe-inline'" in csp_value:
            issues.append("CSP contains 'unsafe-inline' which weakens protection")

        # Check X-Frame-Options value
        xfo = headers.get("X-Frame-Options", "")
        if xfo and xfo not in ("DENY", "SAMEORIGIN"):
            issues.append(f"Invalid X-Frame-Options value: {xfo}")

        return issues

    def generate_report(self, headers: dict[str, str]) -> dict:
        """Generate a full security audit report.

        Args:
            headers: Dictionary of HTTP headers to audit.

        Returns:
            Report dictionary with issues list and score.
        """
        issues = self.scan_headers(headers)
        total_checks = len(self.REQUIRED_HEADERS) + 2  # +2 for CSP checks
        passed = total_checks - len(issues)
        score = max(0, int((passed / total_checks) * 100))

        return {
            "issues": issues,
            "score": score,
            "total_checks": total_checks,
            "passed": passed,
            "failed": len(issues),
        }


@dataclass
class SecurityMiddleware:
    """Middleware that applies security headers and input sanitization."""

    security_headers: Optional[SecurityHeaders] = None
    sanitize_inputs: bool = True
    blocked_paths: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Initialize default security headers if not provided."""
        if self.security_headers is None:
            csp = ContentSecurityPolicy()
            csp.add_directive("script-src", "'self'")
            self.security_headers = SecurityHeaders(csp=csp)

    def apply_headers(self) -> dict[str, str]:
        """Apply security headers to a response.

        Returns:
            Dictionary of security headers to apply.
        """
        return self.security_headers.get_headers()

    def sanitize_request(self, params: dict[str, str]) -> dict[str, str]:
        """Sanitize request parameters.

        Args:
            params: Request parameters to sanitize.

        Returns:
            Sanitized parameters dictionary.
        """
        if not self.sanitize_inputs:
            return params
        return {k: XssSanitizer.sanitize_input(v) for k, v in params.items()}

    def is_path_blocked(self, path: str) -> bool:
        """Check if a request path is blocked.

        Args:
            path: Request path to check.

        Returns:
            True if the path is blocked.
        """
        return path in self.blocked_paths

    def process_request(
        self, path: str, params: dict[str, str]
    ) -> tuple[bool, dict[str, str], dict[str, str]]:
        """Process a request through the security middleware.

        Args:
            path: Request path.
            params: Request parameters.

        Returns:
            Tuple of (allowed, headers, sanitized_params).
        """
        if self.is_path_blocked(path):
            return False, {}, {}
        headers = self.apply_headers()
        sanitized = self.sanitize_request(params)
        return True, headers, sanitized


@dataclass
class CSPNonceManager:
    """Manages CSP nonces for script/style tags."""

    nonces: dict[str, str] = field(default_factory=dict)

    def generate_nonce(self, tag_id: str) -> str:
        """Generate a unique nonce for a tag.

        Args:
            tag_id: Identifier for the tag (e.g., 'script-main').

        Returns:
            Base64-encoded nonce string.
        """
        import base64
        nonce = base64.b64encode(__import__("os").urandom(16)).decode("ascii")
        self.nonces[tag_id] = nonce
        return nonce

    def get_nonce(self, tag_id: str) -> Optional[str]:
        """Get a previously generated nonce.

        Args:
            tag_id: Tag identifier.

        Returns:
            Nonce string if exists, None otherwise.
        """
        return self.nonces.get(tag_id)

    def build_nonce_directive(self) -> str:
        """Build a CSP directive with all nonces.

        Returns:
            CSP script-src directive with all nonces.
        """
        nonce_parts = ["'self'"]
        for nonce in self.nonces.values():
            nonce_parts.append(f"'nonce-{nonce}'")
        return "script-src " + " ".join(nonce_parts)

    def reset(self) -> None:
        """Clear all nonces (for new request cycle)."""
        self.nonces.clear()
