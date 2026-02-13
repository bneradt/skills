"""Convert between HTML (Graph API) and Markdown (Kit-friendly)."""

import json
import re

import markdown
import markdownify


def html_to_markdown(html: str) -> str:
    """Convert OneNote HTML content to Markdown.

    Strips OneNote-specific metadata attributes and converts to clean Markdown.
    """
    # Remove OneNote-specific data attributes and style tags
    cleaned = re.sub(r'\s+data-[\w-]+="[^"]*"', "", html)
    cleaned = re.sub(r'\s+style="[^"]*"', "", cleaned)

    result = markdownify.markdownify(
        cleaned,
        heading_style="ATX",
        bullets="-",
        strip=["img"],  # Strip images (binary data not useful in CLI)
    )

    # Clean up excessive whitespace
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result.strip()


def markdown_to_onenote_html(title: str, md_content: str) -> str:
    """Convert Markdown to OneNote-compatible HTML for page creation.

    Wraps content in the required HTML structure for the OneNote API.
    """
    body_html = markdown.markdown(
        md_content,
        extensions=["tables", "fenced_code"],
    )

    return (
        "<!DOCTYPE html>\n"
        "<html>\n"
        f"  <head><title>{_escape_html(title)}</title></head>\n"
        f"  <body>{body_html}</body>\n"
        "</html>"
    )


def make_patch_content(action: str, html_content: str) -> str:
    """Create a JSON PATCH body for updating a OneNote page.

    Args:
        action: 'append', 'replace', or 'insert'
        html_content: HTML content for the patch

    Returns:
        JSON string for the PATCH request body.
    """
    patch = [
        {
            "target": "body",
            "action": action,
            "content": html_content,
        }
    ]
    return json.dumps(patch)


def _escape_html(text: str) -> str:
    """Escape HTML special characters in text."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
