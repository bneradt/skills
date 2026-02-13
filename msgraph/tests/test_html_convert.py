"""Tests for HTML <-> Markdown conversion."""

import json

from msgraph_kit.html_convert import (
    _escape_html,
    html_to_markdown,
    make_patch_content,
    markdown_to_onenote_html,
)


class TestHtmlToMarkdown:
    def test_basic_paragraph(self):
        html = "<p>Hello world</p>"
        result = html_to_markdown(html)
        assert "Hello world" in result

    def test_headings(self):
        html = "<h1>Title</h1><h2>Subtitle</h2><p>Body text</p>"
        result = html_to_markdown(html)
        assert "# Title" in result
        assert "## Subtitle" in result
        assert "Body text" in result

    def test_bold_italic(self):
        html = "<p><b>bold</b> and <i>italic</i></p>"
        result = html_to_markdown(html)
        assert "**bold**" in result
        assert "*italic*" in result

    def test_unordered_list(self):
        html = "<ul><li>one</li><li>two</li><li>three</li></ul>"
        result = html_to_markdown(html)
        assert "- one" in result
        assert "- two" in result
        assert "- three" in result

    def test_strips_data_attributes(self):
        html = '<p data-id="abc" data-tag="to-do">Text</p>'
        result = html_to_markdown(html)
        assert "data-id" not in result
        assert "Text" in result

    def test_strips_style_attributes(self):
        html = '<p style="font-size:12px;color:red">Styled text</p>'
        result = html_to_markdown(html)
        assert "style" not in result
        assert "Styled text" in result

    def test_strips_images(self):
        html = '<p>Before</p><img src="data:image/png;base64,abc"/><p>After</p>'
        result = html_to_markdown(html)
        assert "Before" in result
        assert "After" in result
        assert "data:image" not in result

    def test_excessive_whitespace_cleaned(self):
        html = "<p>Line 1</p>\n\n\n\n\n<p>Line 2</p>"
        result = html_to_markdown(html)
        assert "\n\n\n" not in result

    def test_links(self):
        html = '<p><a href="https://example.com">Example</a></p>'
        result = html_to_markdown(html)
        assert "[Example](https://example.com)" in result


class TestMarkdownToOnenoteHtml:
    def test_basic_structure(self):
        result = markdown_to_onenote_html("My Title", "Hello world")
        assert "<!DOCTYPE html>" in result
        assert "<title>My Title</title>" in result
        assert "<body>" in result
        assert "<p>Hello world</p>" in result

    def test_heading_conversion(self):
        result = markdown_to_onenote_html("Test", "# Heading 1\n\nSome text")
        assert "<h1>Heading 1</h1>" in result
        assert "<p>Some text</p>" in result

    def test_title_escaping(self):
        result = markdown_to_onenote_html("Title <with> & special \"chars\"", "Content")
        assert "&lt;with&gt;" in result
        assert "&amp;" in result
        assert "&quot;chars&quot;" in result

    def test_empty_content(self):
        result = markdown_to_onenote_html("Empty", "")
        assert "<title>Empty</title>" in result
        assert "<body>" in result

    def test_fenced_code_block(self):
        md = "```python\nprint('hello')\n```"
        result = markdown_to_onenote_html("Code", md)
        assert "<code" in result
        assert "print" in result

    def test_table(self):
        md = "| A | B |\n|---|---|\n| 1 | 2 |"
        result = markdown_to_onenote_html("Table", md)
        assert "<table>" in result
        assert "<td>" in result


class TestMakePatchContent:
    def test_append_action(self):
        result = make_patch_content("append", "<p>New content</p>")
        parsed = json.loads(result)
        assert len(parsed) == 1
        assert parsed[0]["target"] == "body"
        assert parsed[0]["action"] == "append"
        assert parsed[0]["content"] == "<p>New content</p>"

    def test_replace_action(self):
        result = make_patch_content("replace", "<p>Replaced</p>")
        parsed = json.loads(result)
        assert parsed[0]["action"] == "replace"

    def test_valid_json(self):
        result = make_patch_content("insert", "<p>Inserted</p>")
        # Should not raise
        json.loads(result)


class TestEscapeHtml:
    def test_ampersand(self):
        assert _escape_html("A & B") == "A &amp; B"

    def test_angle_brackets(self):
        assert _escape_html("<script>") == "&lt;script&gt;"

    def test_quotes(self):
        assert _escape_html('"hello"') == "&quot;hello&quot;"

    def test_no_special_chars(self):
        assert _escape_html("plain text") == "plain text"
