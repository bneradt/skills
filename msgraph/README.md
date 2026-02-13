# msgraph-kit

Microsoft Graph integration for Claude Code (Kit). Provides OneNote access — read, create, and update notebooks, sections, and pages.

## Quick Start

### 1. Azure Setup

Create an Azure app registration with OneNote permissions. See [references/azure-setup.md](references/azure-setup.md) for a detailed walkthrough.

### 2. Configure

```bash
cp .env.example .env
# Edit .env with your Azure app client ID and tenant ID
```

### 3. Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

### 4. Authenticate

```bash
python3 scripts/auth_login.py
# Follow the device code flow in your browser
```

### 5. Install as Kit Skill

```bash
mkdir -p ~/.claude/skills/msgraph
ln -s "$(pwd)/SKILL.md" ~/.claude/skills/msgraph/SKILL.md
```

## Usage

Once installed as a skill, Kit can access OneNote naturally:

- "List my OneNote notebooks"
- "Read the page about project planning"
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

- **`src/msgraph_kit/`** — Core library modules (auth, config, OneNote operations, HTML conversion)
- **`scripts/`** — CLI entry points that Kit calls via Bash
- **`SKILL.md`** — Skill definition that teaches Kit when and how to use the scripts
- **`references/`** — Detailed API docs and setup guides

All scripts output JSON to stdout (results) and stderr (errors). Authentication uses the device code flow with tokens cached in the macOS Keychain.

## Dependencies

- `msgraph-sdk` — Official Microsoft Graph Python SDK
- `azure-identity` — Official Azure authentication library
- `python-dotenv` — Environment variable loading
- `markdownify` — HTML to Markdown conversion
- `markdown` — Markdown to HTML conversion
