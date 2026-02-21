# msgraph-kit

Microsoft Graph integration for OpenClaw. Provides OneNote access — read, create, and update notebooks, sections, and pages via lightweight HTTP calls.

## Quick Start

### 1. Azure Setup

Create an Azure app registration with OneNote permissions. See [references/azure-setup.md](references/azure-setup.md) for a detailed walkthrough.

### 2. Configure

```bash
cp .env.example .env
# Edit .env with your Azure app client ID
# Use MSGRAPH_TENANT_ID=consumers for personal Microsoft accounts
```

### 3. Install

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

### 4. Authenticate

```bash
.venv/bin/python3 scripts/auth_login.py
# Follow the device code flow in your browser
```

### 5. Install as OpenClaw Skill

Copy or clone this repo into your OpenClaw skills directory:

```bash
# Clone directly
git clone https://github.com/bneradt/msgraph.git /path/to/openclaw/skills/msgraph

# Or symlink
ln -s /path/to/msgraph /path/to/openclaw/skills/msgraph
```

## Usage

Once installed as a skill, the agent can access OneNote naturally:

- "List my OneNote notebooks"
- "Read the shopping list from the Family notebook"
- "Create a note about today's meeting"

## Scripts

| Script | Purpose |
|--------|---------|
| `auth_login.py` | Authenticate via device code flow |
| `auth_status.py` | Check authentication status |
| `onenote_list_notebooks.py` | List all notebooks |
| `onenote_list_sections.py` | List sections in a notebook |
| `onenote_list_pages.py` | List pages in a section |
| `onenote_read_page.py` | Read a page as Markdown |
| `onenote_create_notebook.py` | Create a new notebook |
| `onenote_create_section.py` | Create a new section |
| `onenote_create_page.py` | Create a new page |
| `onenote_update_page.py` | Update a page's content |

## Architecture

- **`src/msgraph_kit/`** — Core library (auth, config, OneNote operations, HTML↔Markdown conversion)
- **`scripts/`** — CLI entry points that the agent calls
- **`SKILL.md`** — Skill definition (when and how to use the scripts)
- **`references/`** — API docs and setup guides

All scripts output JSON to stdout (results) and stderr (errors). Authentication uses the device code flow with tokens cached via `msal-extensions` (file-based on Linux, Keychain on macOS).

## Design Decisions

- **No msgraph-sdk**: The official Microsoft Graph Python SDK uses ~1GB of memory on import due to its massive generated model classes. This is unsuitable for constrained environments like a Raspberry Pi. Instead, all API calls use lightweight `requests` HTTP calls directly.
- **Synchronous**: All operations are synchronous (no asyncio) for simplicity and lower overhead.
- **`consumers` tenant**: Personal Microsoft accounts (including Microsoft 365 Family) require `MSGRAPH_TENANT_ID=consumers`, not `common` or a specific tenant ID.

## Dependencies

- `azure-identity` — Azure authentication (device code flow + token caching)
- `requests` — Lightweight HTTP calls to Microsoft Graph API
- `python-dotenv` — Environment variable loading
- `markdownify` — HTML to Markdown conversion
- `markdown` — Markdown to HTML conversion

## License

Apache License 2.0
