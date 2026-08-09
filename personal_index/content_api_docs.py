"""API documentation generator for personal-index content API."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ParameterDoc:
    """Documentation for an API parameter."""
    name: str
    param_type: str
    required: bool = False
    default: Any = None
    description: str = ""

    def to_dict(self) -> dict:
        result: dict[str, Any] = {
            "name": self.name,
            "type": self.param_type,
            "required": self.required,
        }
        if self.default is not None:
            result["default"] = self.default
        if self.description:
            result["description"] = self.description
        return result


@dataclass
class ResponseDoc:
    """Documentation for an API response."""
    status_code: int
    description: str
    schema: Optional[dict] = None

    def to_dict(self) -> dict:
        result: dict[str, Any] = {
            "status_code": self.status_code,
            "description": self.description,
        }
        if self.schema:
            result["schema"] = self.schema
        return result


@dataclass
class EndpointDoc:
    """Documentation for a single API endpoint."""
    path: str
    method: str
    summary: str
    description: str = ""
    parameters: list[ParameterDoc] = field(default_factory=list)
    responses: list[ResponseDoc] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    auth_required: bool = False

    def to_dict(self) -> dict:
        result: dict[str, Any] = {
            "path": self.path,
            "method": self.method.upper(),
            "summary": self.summary,
        }
        if self.description:
            result["description"] = self.description
        if self.parameters:
            result["parameters"] = [p.to_dict() for p in self.parameters]
        if self.responses:
            result["responses"] = [r.to_dict() for r in self.responses]
        if self.tags:
            result["tags"] = self.tags
        if self.auth_required:
            result["auth_required"] = True
        return result


@dataclass
class DocSection:
    """A section of API documentation."""
    title: str
    content: str
    endpoints: list[EndpointDoc] = field(default_factory=list)

    def to_dict(self) -> dict:
        result: dict[str, Any] = {
            "title": self.title,
            "content": self.content,
        }
        if self.endpoints:
            result["endpoints"] = [e.to_dict() for e in self.endpoints]
        return result


@dataclass
class APIDocumentation:
    """Complete API documentation container."""
    title: str = "Personal Index API"
    version: str = "1.0.0"
    description: str = "API documentation for personal-index content operations"
    endpoints: list[EndpointDoc] = field(default_factory=list)
    sections: list[DocSection] = field(default_factory=list)

    def add_endpoint(self, endpoint: EndpointDoc) -> None:
        """Add an endpoint to the documentation."""
        self.endpoints.append(endpoint)

    def add_section(self, section: DocSection) -> None:
        """Add a section to the documentation."""
        self.sections.append(section)

    def get_endpoint_by_path(self, path: str) -> Optional[EndpointDoc]:
        """Find an endpoint by its path."""
        for ep in self.endpoints:
            if ep.path == path:
                return ep
        return None

    def generate(self) -> dict:
        """Generate full documentation as a dict."""
        return {
            "title": self.title,
            "version": self.version,
            "description": self.description,
            "endpoints": [e.to_dict() for e in self.endpoints],
            "sections": [s.to_dict() for s in self.sections],
        }


class DocumentationBuilder:
    """Builder for constructing API documentation."""

    def __init__(self):
        self.endpoints: list[EndpointDoc] = []
        self.sections: list[DocSection] = []
        self.title: str = "Personal Index API"
        self.version: str = "1.0.0"

    def add_endpoint(self, endpoint: EndpointDoc) -> "DocumentationBuilder":
        """Add an endpoint (fluent interface)."""
        self.endpoints.append(endpoint)
        return self

    def add_section(self, section: DocSection) -> "DocumentationBuilder":
        """Add a section (fluent interface)."""
        self.sections.append(section)
        return self

    def build(self) -> dict:
        """Build the final documentation dict."""
        return {
            "title": self.title,
            "version": self.version,
            "endpoints": [e.to_dict() for e in self.endpoints],
            "sections": [s.to_dict() for s in self.sections],
        }


def generate_openapi_spec(
    endpoints: Optional[list[EndpointDoc]] = None,
) -> dict:
    """Generate an OpenAPI 3.0 specification.

    Args:
        endpoints: Optional list of endpoint docs to include.

    Returns:
        OpenAPI spec as a dict.
    """
    spec: dict[str, Any] = {
        "openapi": "3.0.3",
        "info": {
            "title": "Personal Index API",
            "version": "1.0.0",
            "description": "REST API for personal-index content operations",
        },
        "paths": {},
        "components": {
            "securitySchemes": {
                "ApiKeyAuth": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "X-API-Key",
                }
            }
        },
    }

    if endpoints:
        for ep in endpoints:
            method = ep.method.lower()
            path_item: dict[str, Any] = {
                "summary": ep.summary,
                "responses": {
                    str(r.status_code): {"description": r.description}
                    for r in ep.responses
                },
            }
            if ep.parameters:
                path_item["parameters"] = [
                    {
                        "name": p.name,
                        "in": "query",
                        "required": p.required,
                        "schema": {"type": p.param_type},
                    }
                    for p in ep.parameters
                ]
            if ep.auth_required:
                path_item["security"] = [{"ApiKeyAuth": []}]

            if ep.path not in spec["paths"]:
                spec["paths"][ep.path] = {}
            spec["paths"][ep.path][method] = path_item

    return spec


def generate_markdown_docs(
    endpoints: Optional[list[EndpointDoc]] = None,
) -> str:
    """Generate Markdown documentation.

    Args:
        endpoints: Optional list of endpoint docs to include.

    Returns:
        Markdown formatted documentation string.
    """
    lines = [
        "# API Documentation",
        "",
        "Personal Index Content API - Version 1.0.0",
        "",
        "## Overview",
        "",
        "This API provides access to content management operations including",
        "searching, indexing, and managing tracked web content.",
        "",
        "## Authentication",
        "",
        "All endpoints require an API key passed via the `X-API-Key` header.",
        "",
        "## Endpoints",
        "",
    ]

    if endpoints:
        for ep in endpoints:
            lines.append(f"### {ep.method} {ep.path}")
            lines.append("")
            lines.append(ep.summary)
            if ep.description:
                lines.append("")
                lines.append(ep.description)
            if ep.parameters:
                lines.append("")
                lines.append("#### Parameters")
                lines.append("")
                lines.append("| Name | Type | Required | Default |")
                lines.append("|------|------|----------|---------|")
                for p in ep.parameters:
                    default = str(p.default) if p.default is not None else "-"
                    lines.append(
                        f"| {p.name} | {p.param_type} | "
                        f"{'Yes' if p.required else 'No'} | {default} |"
                    )
            if ep.responses:
                lines.append("")
                lines.append("#### Responses")
                lines.append("")
                for r in ep.responses:
                    lines.append(f"- **{r.status_code}**: {r.description}")
            lines.append("")
            lines.append("---")
            lines.append("")

    return "\n".join(lines)


def generate_swagger_ui_html(
    spec_url: str = "/api/docs/openapi.json",
) -> str:
    """Generate Swagger UI HTML page.

    Args:
        spec_url: URL to the OpenAPI spec JSON.

    Returns:
        HTML string for Swagger UI.
    """
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8"/>
    <title>Personal Index API Docs</title>
    <link rel="stylesheet" type="text/css" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css"/>
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
    <script>
        SwaggerUIBundle.presets([SwaggerUIBundle.presets.apis, SwaggerUIBundle.SwaggerUIStandalonePreset])
        SwaggerUIBundle.urls([{{
            url: "{spec_url}",
            name: "Personal Index API"
        }}])
        SwaggerUIBundle.init("#swagger-ui")
    </script>
</body>
</html>"""
