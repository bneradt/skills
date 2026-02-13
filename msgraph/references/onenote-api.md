# OneNote API Reference

Detailed reference for the Microsoft Graph OneNote API as used by msgraph-kit.

## API Endpoints

All endpoints are relative to `https://graph.microsoft.com/v1.0`.

### Notebooks

| Operation | Method | Endpoint |
|-----------|--------|----------|
| List notebooks | GET | `/me/onenote/notebooks` |
| Get notebook | GET | `/me/onenote/notebooks/{id}` |
| Create notebook | POST | `/me/onenote/notebooks` |

**Create notebook body**: `{"displayName": "Name"}`

### Sections

| Operation | Method | Endpoint |
|-----------|--------|----------|
| List sections in notebook | GET | `/me/onenote/notebooks/{id}/sections` |
| Create section | POST | `/me/onenote/notebooks/{id}/sections` |

**Create section body**: `{"displayName": "Name"}`

### Pages

| Operation | Method | Endpoint |
|-----------|--------|----------|
| List pages in section | GET | `/me/onenote/sections/{id}/pages` |
| Get page metadata | GET | `/me/onenote/pages/{id}` |
| Get page content | GET | `/me/onenote/pages/{id}/content` |
| Create page | POST | `/me/onenote/sections/{id}/pages` |
| Update page | PATCH | `/me/onenote/pages/{id}/content` |

**Create page**: Content-Type `text/html`, body is full HTML document:

```html
<!DOCTYPE html>
<html>
  <head><title>Page Title</title></head>
  <body><p>Content here</p></body>
</html>
```

**Update page**: Content-Type `application/json`, body is a JSON array of patch operations:

```json
[
  {
    "target": "body",
    "action": "append",
    "content": "<p>New content</p>"
  }
]
```

## Patch Actions

| Action | Description |
|--------|-------------|
| `append` | Add content to the end of the page body |
| `replace` | Replace the content of a target element |
| `insert` | Insert content before or after a target element |

For `replace` and `insert`, you can target specific elements by their `data-id` attribute instead of `body`.

## OneNote HTML Specifics

### Reading pages

OneNote returns HTML with extra attributes:

- `data-id` — unique identifier for each element
- `data-tag` — OneNote tags (to-do, important, etc.)
- `style` — inline styles for formatting
- `data-absolute-enabled` — absolute positioning flag

The `html_convert.py` module strips these when converting to Markdown.

### Creating pages

The OneNote API requires a specific HTML structure:

- Must include `<html>`, `<head>`, `<title>`, and `<body>` tags
- `<title>` sets the page title (required)
- Supported HTML elements: `<p>`, `<h1>`-`<h6>`, `<ul>`, `<ol>`, `<li>`, `<table>`, `<tr>`, `<td>`, `<img>`, `<a>`, `<br>`, `<b>`, `<i>`, `<u>`, `<span>`
- Does NOT support: `<script>`, `<style>`, `<div>` (converted to `<p>`)

### Content limits

- Maximum page content size: 2 MB
- Maximum PATCH request size: 2 MB
- Image size limit: 70 MB (but images aren't used in this integration)

## Required Permissions (Delegated)

| Permission | Use |
|------------|-----|
| `User.Read` | Read user profile (verify auth) |
| `Notes.Read` | Read OneNote notebooks, sections, pages |
| `Notes.ReadWrite` | Read and write OneNote content |
| `Notes.Create` | Create new notebooks |

## Rate Limits

Microsoft Graph has per-app and per-user throttling. If you receive a `429 Too Many Requests` response, the `Retry-After` header indicates how long to wait. For normal Kit usage, you are unlikely to hit rate limits.

## Error Codes

| Code | Meaning |
|------|---------|
| 401 | Token expired or invalid — re-authenticate |
| 403 | Missing permissions — check Azure app API permissions |
| 404 | Resource not found — ID may be invalid |
| 409 | Conflict — notebook name already exists |
| 429 | Throttled — wait and retry |
| 503 | Service unavailable — transient, retry |

## Hierarchy

```
User
└── Notebooks (list, create)
    └── Sections (list, create)
        └── Pages (list, read, create, update)
```

OneNote also supports Section Groups (folders within notebooks) — not currently implemented in msgraph-kit but can be added later.
