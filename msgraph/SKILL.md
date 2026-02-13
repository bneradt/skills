---
name: msgraph
description: Access Microsoft OneNote notebooks — read, create, and update notes via Microsoft Graph API
triggers:
  - OneNote
  - notebooks
  - notes
  - Microsoft notes
  - create a note
  - read my notes
  - list notebooks
  - onenote
---

# Microsoft Graph — OneNote

Kit can access the user's Microsoft OneNote notebooks through the Microsoft Graph API. This skill enables reading, creating, and updating OneNote notebooks, sections, and pages. All content is converted between OneNote HTML and Markdown automatically.

## Prerequisites

Before using OneNote commands, the user must have:

1. An Azure app registration configured (see `references/azure-setup.md` in the msgraph repo)
2. A `.env` file in the msgraph repo with `MSGRAPH_CLIENT_ID` set
3. Completed authentication via the device code flow

If the user has not authenticated yet, run the auth login script first.

## Script Location

All scripts are in the msgraph repo. Use this base path:

```
MSGRAPH_DIR="$HOME/Library/CloudStorage/OneDrive-Personal/Documents/development/myopenclaw/msgraph"
```

Scripts auto-detect and use the repo's `.venv` Python if available.

## Authentication

### Check auth status

```bash
python3 "$MSGRAPH_DIR/scripts/auth_status.py"
```

Returns JSON: `{"authenticated": true, "username": "...", ...}` or `{"authenticated": false, "reason": "..."}`.

### Log in (device code flow)

```bash
python3 "$MSGRAPH_DIR/scripts/auth_login.py"
```

Prints a URL and code to stderr. Tell the user to open the URL in their browser and enter the code. The script prints JSON with the authenticated username on success. Tokens are cached in the macOS Keychain — subsequent commands authenticate silently.

Always check auth status before running OneNote commands. If not authenticated, run the login script first and wait for the user to complete the browser flow.

## OneNote Operations

### List notebooks

```bash
python3 "$MSGRAPH_DIR/scripts/onenote_list_notebooks.py"
```

Returns JSON array of notebooks with `id`, `displayName`, `createdDateTime`, `lastModifiedDateTime`.

### List sections in a notebook

```bash
python3 "$MSGRAPH_DIR/scripts/onenote_list_sections.py" --notebook-id "NOTEBOOK_ID"
```

Returns JSON array of sections with `id`, `displayName`, `createdDateTime`.

### List pages in a section

```bash
python3 "$MSGRAPH_DIR/scripts/onenote_list_pages.py" --section-id "SECTION_ID"
```

Returns JSON array of pages with `id`, `title`, `createdDateTime`, `lastModifiedDateTime`.

### Read a page

```bash
python3 "$MSGRAPH_DIR/scripts/onenote_read_page.py" --page-id "PAGE_ID"
```

Returns JSON with page metadata plus a `content` field containing the page body as Markdown.

### Create a notebook

```bash
python3 "$MSGRAPH_DIR/scripts/onenote_create_notebook.py" --name "My Notebook"
```

Returns JSON with the new notebook's `id` and `displayName`.

### Create a section

```bash
python3 "$MSGRAPH_DIR/scripts/onenote_create_section.py" --notebook-id "NOTEBOOK_ID" --name "My Section"
```

Returns JSON with the new section's `id` and `displayName`.

### Create a page

```bash
python3 "$MSGRAPH_DIR/scripts/onenote_create_page.py" --section-id "SECTION_ID" --title "Page Title" --content "Markdown content here"
```

For longer content, use `--stdin`:

```bash
echo "# My Page\n\nContent here" | python3 "$MSGRAPH_DIR/scripts/onenote_create_page.py" --section-id "SECTION_ID" --title "Page Title" --stdin
```

Returns JSON with the new page's `id`, `title`, and `contentUrl`.

### Update a page

```bash
python3 "$MSGRAPH_DIR/scripts/onenote_update_page.py" --page-id "PAGE_ID" --action append --content "New content to add"
```

Actions: `append` (add to end), `replace` (replace body), `insert` (insert at position). Content can be Markdown or HTML — Markdown is auto-converted.

## Workflow Patterns

### Browse notebooks → read a page

1. List notebooks to find the right one
2. List sections in that notebook
3. List pages in the target section
4. Read the specific page

### Create a note from scratch

1. List notebooks to find where to put the note (or create a new notebook)
2. List sections (or create a new section)
3. Create the page with the content

### Add content to an existing page

1. Navigate to the page (list notebooks → sections → pages)
2. Optionally read the page first to see current content
3. Use update with `--action append` to add content

## Error Handling

All scripts output JSON errors to stderr on failure:

- **Not authenticated**: `{"error": "..."}` — run `auth_login.py` first
- **Missing config**: Check that `.env` exists with `MSGRAPH_CLIENT_ID`
- **Permission denied**: The Azure app registration may need additional API permissions
- **Not found**: The notebook/section/page ID may be invalid — re-list to get current IDs
- **Token expired**: Run `auth_login.py` to re-authenticate

## Reference

For detailed API information and edge cases, see:
- `references/onenote-api.md` in the msgraph repo — full API details
- `references/azure-setup.md` in the msgraph repo — Azure app registration walkthrough
