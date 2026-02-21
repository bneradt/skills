---
name: msgraph
description: Access Microsoft OneNote notebooks — read, create, and update notes via Microsoft Graph API. Use when the user mentions OneNote, notebooks, notes, Microsoft notes, or wants to read/create/edit OneNote content.
---

# Microsoft Graph — OneNote

Access the user's Microsoft OneNote notebooks through lightweight HTTP calls to the Microsoft Graph API. All content is converted between OneNote HTML and Markdown automatically.

## ⚠️ Safety — Do Not Delete Without Confirmation

**NEVER delete any notebooks, sections, or pages without explicit confirmation from the user.** Many of these notes are shared with his wife and family. Some contain years of important information. Deleting the wrong thing could cause real harm. Always ask before any destructive action — no exceptions.

## Script Location

```
MSGRAPH_DIR="/home/bneradt/.openclaw/workspace/skills/msgraph"
```

Always invoke scripts with the venv Python.

Preferred (self-bootstraps venv if missing, and sets PYTHONPATH correctly):

```bash
$MSGRAPH_DIR/scripts/py.sh "$MSGRAPH_DIR/scripts/<script>.py" [args...]
```

Direct venv (when you know .venv already exists):

```bash
$MSGRAPH_DIR/.venv/bin/python3 "$MSGRAPH_DIR/scripts/<script>.py" [args...]
```

## Known Notebooks

| Notebook | ID | Shared |
|----------|----|--------|
| Family | `0-F45FC9EC7A91390E!107541` | Yes |
| Family Notebook | `0-F45FC9EC7A91390E!111630` | Yes |
| Personal | `0-F45FC9EC7A91390E!107482` | No |
| Religious | `0-F45FC9EC7A91390E!106680` | No |

Use these IDs to skip the list-notebooks step when the user references a known notebook.

## Authentication

Auth is already configured. If a script returns an auth error, check status first:

```bash
$MSGRAPH_DIR/scripts/py.sh "$MSGRAPH_DIR/scripts/auth_status.py"
```

If re-auth is needed:

```bash
$MSGRAPH_DIR/scripts/py.sh "$MSGRAPH_DIR/scripts/auth_login.py"
```

Prints a URL and device code to stderr — tell the user to open the URL and enter the code.

## OneNote Operations

### List notebooks

```bash
$MSGRAPH_DIR/scripts/py.sh "$MSGRAPH_DIR/scripts/onenote_list_notebooks.py"
```

### List sections in a notebook

```bash
$MSGRAPH_DIR/scripts/py.sh "$MSGRAPH_DIR/scripts/onenote_list_sections.py" --notebook-id "NOTEBOOK_ID"
```

### List pages in a section

```bash
$MSGRAPH_DIR/scripts/py.sh "$MSGRAPH_DIR/scripts/onenote_list_pages.py" --section-id "SECTION_ID"
```

### Read a page

```bash
$MSGRAPH_DIR/scripts/py.sh "$MSGRAPH_DIR/scripts/onenote_read_page.py" --page-id "PAGE_ID"
```

Returns JSON with page metadata and a `content` field as Markdown.

### Create a notebook

```bash
$MSGRAPH_DIR/scripts/py.sh "$MSGRAPH_DIR/scripts/onenote_create_notebook.py" --name "My Notebook"
```

### Create a section

```bash
$MSGRAPH_DIR/scripts/py.sh "$MSGRAPH_DIR/scripts/onenote_create_section.py" --notebook-id "NOTEBOOK_ID" --name "My Section"
```

### Create a page

```bash
$MSGRAPH_DIR/scripts/py.sh "$MSGRAPH_DIR/scripts/onenote_create_page.py" --section-id "SECTION_ID" --title "Page Title" --content "Markdown content here"
```

For longer content, use `--stdin`:

```bash
echo "# My Page\n\nContent here" | $MSGRAPH_DIR/scripts/py.sh "$MSGRAPH_DIR/scripts/onenote_create_page.py" --section-id "SECTION_ID" --title "Page Title" --stdin
```

### Update a page

```bash
$MSGRAPH_DIR/scripts/py.sh "$MSGRAPH_DIR/scripts/onenote_update_page.py" --page-id "PAGE_ID" --action append --content "New content to add"
```

Actions: `append` (add to end), `replace` (replace body), `insert` (insert at position). Content can be Markdown or HTML — Markdown is auto-converted.

## Workflow Patterns

### Browse → read

1. List sections in notebook (use known ID if possible)
2. List pages in target section
3. Read the specific page

### Create a note

1. List sections (or create a new one)
2. Create the page with content

### Append to existing page

1. Navigate to the page (sections → pages)
2. Use update with `--action append`

## Error Handling

All scripts output JSON. Common errors:

- **Auth expired**: Run `auth_login.py` for device code re-auth
- **Not found (404)**: Re-list to get current IDs
- **Permission denied (403)**: Check Azure app API permissions

## Reference

For API details and edge cases, see:
- `references/onenote-api.md` — full API reference
- `references/azure-setup.md` — Azure app registration walkthrough
