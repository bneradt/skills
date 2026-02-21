# OpenClaw Internals (v2026.2.9)

Understanding how OpenClaw works from the source code perspective. Reference for debugging issues like cron timeouts, compaction amnesia, Telegram message failures, auth profile rotation, and more.

## Architecture Overview

OpenClaw is a personal AI assistant platform built in TypeScript/Node.js. The codebase lives at `/home/bneradt/openclaw`. Core runtime uses `@mariozechner/pi-agent-core` and `@mariozechner/pi-coding-agent` as embedded agent SDKs.

### Top-Level Directory Structure

```
openclaw/
├── src/
│   ├── entry.ts              # CLI entry point (respawns with --disable-warning=ExperimentalWarning)
│   ├── index.ts              # Legacy entry (exports getReplyFromConfig, web monitor, etc.)
│   ├── runtime.ts            # RuntimeEnv type
│   ├── gateway/              # WebSocket server + HTTP control plane (central hub)
│   ├── agents/               # Agent runtime (pi-mono derivative), tools, compaction, skills
│   ├── auto-reply/           # Message→reply pipeline (directives, queue, agent runner)
│   ├── channels/             # Channel plugin system (abstract layer)
│   ├── telegram/             # Telegram bot (grammY)
│   ├── discord/              # Discord (discord.js)
│   ├── signal/               # Signal (signal-cli SSE)
│   ├── slack/                # Slack (Bolt + HTTP)
│   ├── imessage/             # iMessage (BlueBubbles)
│   ├── line/                 # LINE Messaging API
│   ├── web/                  # WhatsApp (Baileys)
│   ├── whatsapp/             # WhatsApp normalization helpers
│   ├── browser/              # Playwright browser control + Chrome extension relay
│   ├── cron/                 # Scheduled jobs (CronService)
│   ├── sessions/             # Session key utilities, send policy, transcript events
│   ├── memory/               # Memory search (SQLite + vector embeddings)
│   ├── config/               # Configuration system (Zod schemas, sessions, paths)
│   ├── cli/                  # CLI framework (Commander.js)
│   ├── commands/             # CLI command implementations
│   ├── infra/                # Infrastructure (heartbeat, outbound, updates, ports, etc.)
│   ├── hooks/                # Hook system (bundled + workspace + plugin hooks)
│   ├── plugins/              # Plugin system (discovery, loader, SDK)
│   ├── plugin-sdk/           # Plugin SDK exports
│   ├── acp/                  # Agent Client Protocol (ACP) server
│   ├── media/                # Media hosting & file handling
│   ├── media-understanding/  # Audio/video/image transcription pipeline
│   ├── link-understanding/   # Auto-fetch & summarize links in messages
│   ├── canvas-host/          # Canvas presentation server (A2UI)
│   ├── tts/                  # Text-to-speech (ElevenLabs, Edge TTS, etc.)
│   ├── tui/                  # Terminal UI (blessed-based)
│   ├── daemon/               # Systemd/launchd service management
│   ├── logging/              # Structured logging subsystem
│   ├── routing/              # Session key parsing, agent routing
│   ├── security/             # File permission audits, external content safety
│   ├── pairing/              # Mobile node pairing store
│   ├── process/              # Command queue, exec, spawn utilities
│   ├── providers/            # Provider-specific auth (GitHub Copilot, Qwen Portal)
│   ├── markdown/             # Markdown processing (tables, fences, frontmatter)
│   ├── shared/               # Shared text utilities (reasoning tags)
│   ├── terminal/             # Terminal formatting (ANSI, tables, themes)
│   ├── node-host/            # Node host runner
│   └── wizard/               # Onboarding wizard
├── docs/                     # Documentation (mirrors docs.openclaw.ai)
├── skills/                   # Bundled skills
└── extensions/               # Channel extensions (browser relay, etc.)
```

---

## 1. Gateway (`src/gateway/`)

The **Gateway** is the central control plane — a WebSocket + HTTP server that orchestrates everything.

### Key Files
- `server.impl.ts` — `startGatewayServer()`: boots everything (config, channels, cron, browser, canvas, plugins, heartbeats, discovery)
- `server-methods-list.ts` — Master list of all RPC methods (~90+ methods)
- `server-methods.ts` — Core handler registry (delegates to `server-methods/*.ts`)
- `server-methods/*.ts` — Individual method groups: `chat.ts`, `config.ts`, `cron.ts`, `sessions.ts`, `agents.ts`, `nodes.ts`, `browser.ts`, `health.ts`, `send.ts`, `usage.ts`, `skills.ts`, `logs.ts`, `exec-approvals.ts`, `wizard.ts`, etc.
- `server-chat.ts` — Chat message routing, `ChatRunRegistry` for tracking active runs
- `session-utils.ts` — Session listing, transcript reading, agent row resolution
- `session-utils.fs.ts` — Low-level file I/O for session transcripts
- `client.ts` — `GatewayClient` WebSocket client for RPC calls
- `hooks.ts` + `hooks-mapping.ts` — Webhook/hook dispatch
- `server-cron.ts` — `buildGatewayCronService()`: wires CronService to gateway
- `server-channels.ts` — `createChannelManager()`: starts/stops channel plugins
- `server-plugins.ts` — `loadGatewayPlugins()`: initializes plugin system
- `server-browser.ts` — Browser control server startup
- `server-startup.ts` — Sidecar services (media server, canvas host)
- `server-runtime-state.ts` — Global mutable state for the gateway process
- `server-restart-sentinel.ts` — Graceful restart via sentinel file
- `config-reload.ts` — Hot config reload via file watcher
- `protocol/` — Zod schemas for all RPC method params/results
- `server/ws-connection.ts` — WebSocket connection handler
- `server/health-state.ts` — Health snapshot cache
- `openai-http.ts` — OpenAI-compatible `POST /v1/chat/completions` endpoint
- `openresponses-http.ts` — OpenResponses API (`POST /v1/responses`)

### Startup Flow
1. Load & validate config (`openclaw.json`)
2. Auto-migrate legacy config if needed
3. Start HTTP/WS server on configured port (default 18789)
4. Load plugins, start channel managers
5. Start CronService, heartbeat runner, discovery (Bonjour/mDNS)
6. Start browser control server, canvas host, media server
7. Initialize subagent registry, skills refresh listener
8. Start config file watcher for hot reload

### Key RPC Methods
| Method | Purpose |
|--------|---------|
| `chat.send` | Send message to agent session |
| `chat.abort` | Abort active agent run |
| `chat.history` | Get session transcript |
| `config.get/apply/patch` | Configuration management |
| `cron.add/update/remove/run/list` | Cron job management |
| `sessions.list/preview/patch/reset/delete/compact` | Session operations |
| `send` | Send outbound message via channel |
| `agent` | Agent event stream |
| `agent.wait` | Wait for subagent completion |
| `models.list` | List available models |
| `health` | Health check |
| `wake` | Wake agent for immediate action |
| `system-event` | Inject system event into session |
| `browser.request` | Browser control actions |

### Session Transcripts
Stored as JSONL at:
```
~/.openclaw/agents/<agentId>/sessions/<SessionId>.jsonl
```
Each line is a JSON-encoded `AgentMessage` (from `@mariozechner/pi-agent-core`).

---

## 2. Auto-Reply Pipeline (`src/auto-reply/`)

This is the **message processing pipeline** — the bridge between channels and the agent. Critical for understanding how messages flow.

### Key Files
- `reply.ts` — Re-exports; main entry is `reply/get-reply.ts`
- `reply/get-reply.ts` — `getReplyFromConfig()`: master orchestrator
- `reply/get-reply-directives.ts` — Parse `/model`, `/think`, `/verbose`, `/elevated` directives
- `reply/get-reply-run.ts` — `runPreparedReply()`: executes the agent turn
- `reply/agent-runner.ts` — `runReplyAgent()`: the core agent execution loop
- `reply/agent-runner-execution.ts` — `runAgentTurnWithFallback()`: handles model fallback
- `reply/agent-runner-memory.ts` — Post-turn memory flush
- `reply/agent-runner-payloads.ts` — Build reply payloads from agent output
- `reply/queue.ts` — Message queue (`steer`/`followup`/`collect` modes)
- `reply/queue/*.ts` — Queue internals (enqueue, drain, settings, state)
- `reply/directive-handling*.ts` — Slash command parsing and execution
- `reply/commands*.ts` — Native commands (`/status`, `/model`, `/compact`, `/reset`, etc.)
- `reply/session.ts` — Session state initialization
- `reply/typing.ts` — Typing indicator management
- `reply/block-reply-pipeline.ts` — Streaming block reply coalescing
- `reply/block-streaming.ts` — Paragraph-level streaming config
- `reply/followup-runner.ts` — Multi-turn followup execution
- `reply/memory-flush.ts` — Memory flush after compaction
- `heartbeat.ts` — Heartbeat token detection, HEARTBEAT_OK handling
- `tokens.ts` — Special tokens: `HEARTBEAT_TOKEN`, `SILENT_REPLY_TOKEN`, `NO_REPLY`
- `thinking.ts` — ThinkLevel/VerboseLevel/ReasoningLevel resolution
- `command-detection.ts` — Detect if message is a slash command
- `envelope.ts` — Message envelope (metadata wrapping)
- `dispatch.ts` — Reply dispatch to channels

### Message Flow
```
Channel (Telegram/Discord/etc.)
  → Channel monitor creates MsgContext
  → getReplyFromConfig(ctx)
    → resolveReplyDirectives() — parse /model, /think, etc.
    → handleInlineActions() — handle /status, /reset, etc.
    → initSessionState() — resolve session key, load store
    → applyMediaUnderstanding() — transcribe audio/video/images
    → applyLinkUnderstanding() — fetch & summarize URLs
    → runPreparedReply()
      → queue management (steer/followup/collect)
      → runReplyAgent()
        → runAgentTurnWithFallback()
          → runEmbeddedPiAgent() (from agents/pi-embedded-runner)
            → Anthropic/OpenAI/Google API call
            → Stream response, execute tool calls
            → subscribeEmbeddedPiSession() for streaming
        → buildReplyPayloads() — format response
        → runMemoryFlushIfNeeded() — update memory after compaction
  → Deliver reply via channel
```

### Queue Modes
- **steer**: Inject messages into currently running agent turn
- **followup**: Hold messages until turn ends, then start new turn
- **collect**: Batch messages together before processing

---

## 3. Agent Runtime (`src/agents/`)

The agent is an embedded derivative of **pi-mono** (pi-coding-agent). This is the largest subsystem.

### Core Execution Files
- `pi-embedded-runner.ts` — Barrel exports for the runner
- `pi-embedded-runner/run.ts` — `runEmbeddedPiAgent()`: THE core agent execution function
- `pi-embedded-runner/run/attempt.ts` — `runEmbeddedAttempt()`: single API call attempt
- `pi-embedded-runner/run/payloads.ts` — Build API request payloads
- `pi-embedded-runner/runs.ts` — Run lifecycle: abort, queue, wait
- `pi-embedded-runner/compact.ts` — `compactEmbeddedPiSession()`: in-session compaction
- `pi-embedded-runner/history.ts` — History turn limiting (`limitHistoryTurns`, `getDmHistoryLimitFromSessionKey`)
- `pi-embedded-runner/model.ts` — Model resolution for runs
- `pi-embedded-runner/system-prompt.ts` — System prompt override resolution
- `pi-embedded-runner/extra-params.ts` — Extra API params (temperature, etc.)
- `pi-embedded-runner/lanes.ts` — Lane/concurrency resolution
- `pi-embedded-runner/tool-result-truncation.ts` — Truncate oversized tool results
- `pi-embedded-runner/tool-split.ts` — Split SDK vs OpenClaw tools
- `pi-embedded-runner/sandbox-info.ts` — Sandbox environment info for prompts

### Streaming / Subscription
- `pi-embedded-subscribe.ts` — `subscribeEmbeddedPiSession()`: handles streaming events
- `pi-embedded-subscribe.handlers.ts` — Event handler factory
- `pi-embedded-subscribe.handlers.messages.ts` — Text/thinking message handlers
- `pi-embedded-subscribe.handlers.tools.ts` — Tool call/result handlers
- `pi-embedded-subscribe.handlers.lifecycle.ts` — Start/end handlers
- `pi-embedded-subscribe.tools.ts` — Tool execution bridge
- `pi-embedded-block-chunker.ts` — Splits long responses into sendable chunks

### System Prompt (`system-prompt.ts`)
`buildAgentSystemPrompt()` constructs the full system prompt from:
1. Identity line ("You are a personal assistant running inside OpenClaw.")
2. **Tooling** — Available tools with summaries (case-sensitive names)
3. **Tool Call Style** — Narration guidance
4. **Safety** — Anthropic-inspired constraints
5. **CLI Quick Reference** — OpenClaw commands
6. **Skills** — Available skills with `<available_skills>` block
7. **Memory Recall** — memory_search/memory_get guidance + citations mode
8. **Self-Update** — Gateway tool constraints (only when user asks)
9. **Model Aliases** — Configured aliases
10. **Workspace** — Working directory, notes
11. **Documentation** — Docs paths, links
12. **Sandbox** — If sandboxed (Docker details, elevated access)
13. **User Identity** — Owner numbers
14. **Time** — Timezone, session_status hint
15. **Reply Tags** — `[[reply_to_current]]`, `[[reply_to:<id>]]`
16. **Messaging** — sessions_send, message tool, inline buttons
17. **Voice** — TTS hint
18. **Reactions** — Emoji reaction guidance (minimal/extensive)
19. **Project Context** — Injected workspace files (AGENTS.md, SOUL.md, etc.)
20. **Silent Replies** — `NO_REPLY` / `SILENT_REPLY` handling
21. **Heartbeats** — `HEARTBEAT_OK` handling
22. **Runtime** — Model, channel, capabilities, reasoning level

### Prompt Modes
- `full` — All sections (main agent)
- `minimal` — Reduced sections: Tooling, Safety, Workspace, Time, Runtime, Subagent Context
- `none` — Just basic identity line

### Compaction (`compaction.ts`)
When context window fills up:
1. `pruneHistoryForContextShare()` — Drop oldest chunks to fit budget (default 50% of context)
2. `splitMessagesByTokenShare()` — Divide messages into N parts by token count
3. `summarizeInStages()` — Summarize each chunk, merge partial summaries
4. `summarizeWithFallback()` — Progressive fallback: full → partial (skip oversized) → note-only
5. `computeAdaptiveChunkRatio()` — Reduce chunk ratio when messages are large
6. `repairToolUseResultPairing()` — Fix orphaned tool_results after dropping chunks

**Key constants:**
- `BASE_CHUNK_RATIO = 0.4` (40% of context for history)
- `MIN_CHUNK_RATIO = 0.15`
- `SAFETY_MARGIN = 1.2` (20% buffer for token estimation)

### Compaction Safeguard Extension (`pi-extensions/compaction-safeguard.ts`)
A pi-coding-agent extension that hooks into the `compact` event. Summarizes dropped messages, preserves tool failure notes, handles split-turn summaries.

### Context Pruning Extension (`pi-extensions/context-pruning/`)
Another extension that prunes old/stale tool results from context before API calls:
- `extension.ts` — Hooks into `context` event
- `pruner.ts` — `pruneContextMessages()`: truncates or removes old tool results
- `settings.ts` — Config: mode (`cache-ttl` or `always`), budget thresholds
- `tools.ts` — Determines which tool results are prunable

### Auth Profiles (`auth-profiles/`)
Manages multiple API keys per provider with rotation and cooldown:
- `profiles.ts` — Profile resolution and ordering
- `store.ts` — Persistent profile store
- `order.ts` — Priority ordering (round-robin, last-good)
- `session-override.ts` — Per-session auth profile overrides
- `oauth.ts` — OAuth credential management
- `usage.ts` — Usage tracking per profile

### Model Selection (`model-selection.ts`, `model-auth.ts`, `model-catalog.ts`)
- `resolveConfiguredModelRef()` — Resolve model from config
- `getApiKeyForModel()` — Get API key with profile rotation
- `resolveAuthProfileOrder()` — Profile priority with cooldown
- `loadModelCatalog()` — Load known model capabilities

### Model Fallback (`model-fallback.ts`)
- `runWithModelFallback()` — Try primary model, fall back to configured alternatives

### Skills System (`skills.ts`, `skills/`)
- `buildWorkspaceSkillSnapshot()` — Scan workspace + bundled + managed skills
- `skills/refresh.ts` — File watcher for skill changes
- `skills/frontmatter.ts` — Parse SKILL.md frontmatter
- `skills/workspace.ts` — Workspace skill discovery
- `skills/bundled-dir.ts` — Bundled skill directory
- `skills-install.ts` — Remote skill installation

### Subagent System
- `subagent-registry.ts` — Track spawned subagent runs, persist to disk
- `subagent-announce.ts` — Announce subagent results to parent session
- `subagent-announce-queue.ts` — Queue announcements for delivery

### Tools
See Section 4 below.

---

## 4. Tools (`src/agents/tools/`, `src/agents/pi-tools*.ts`)

### Tool Architecture
- `pi-tools.ts` — `createOpenClawCodingTools()`: master tool factory
- `pi-tools.schema.ts` — JSON Schema definitions for tools
- `pi-tools.policy.ts` — Tool availability filtering (deny/allow patterns, subagent restrictions)
- `pi-tools.read.ts` — Enhanced `Read` tool (images, offsets, Claude-compatible params)
- `pi-tools.types.ts` — `AnyAgentTool` type
- `bash-tools.ts` — Factory for exec/process tools
- `bash-tools.exec.ts` — `exec` tool: shell execution (pty, background, timeout, security)
- `bash-tools.process.ts` — `process` tool: session management (list, poll, log, write, send-keys, kill)
- `bash-tools.shared.ts` — Shared bash tool utilities
- `tool-policy.ts` — Tool group expansion, owner-only policies
- `tool-policy.conformance.ts` — Validate tool sets against policy
- `openclaw-tools.ts` — OpenClaw-specific tools (sessions, cron, gateway, nodes, camera, etc.)

### Individual Tool Implementations (`tools/`)
| File | Tool(s) |
|------|---------|
| `browser-tool.ts` | `browser` — Playwright control |
| `canvas-tool.ts` | `canvas` — Present/eval/snapshot |
| `cron-tool.ts` | `cron` — Manage scheduled jobs |
| `gateway-tool.ts` | `gateway` — Config, restart, update |
| `image-tool.ts` | `image` — Vision model analysis |
| `memory-tool.ts` | `memory_search`, `memory_get` |
| `message-tool.ts` | `message` — Cross-channel messaging |
| `nodes-tool.ts` | `nodes` — Mobile node control |
| `sessions-spawn-tool.ts` | `sessions_spawn` — Subagent spawning |
| `sessions-send-tool.ts` | `sessions_send` — Cross-session messaging |
| `sessions-list-tool.ts` | `sessions_list` — List sessions |
| `sessions-history-tool.ts` | `sessions_history` — Fetch history |
| `session-status-tool.ts` | `session_status` — Status card |
| `tts-tool.ts` | `tts` — Text-to-speech |
| `web-search.ts` | `web_search` — Brave Search |
| `web-fetch.ts` | `web_fetch` — URL content extraction |
| `agents-list-tool.ts` | `agents_list` — List available agents |
| `discord-actions*.ts` | Discord-specific actions |
| `telegram-actions.ts` | Telegram-specific actions |
| `slack-actions.ts` | Slack-specific actions |
| `whatsapp-actions.ts` | WhatsApp-specific actions |

### Tool Policy (`pi-tools.policy.ts`)
Controls which tools are available per session:
- `filterToolsByPolicy()` — Apply deny/allow patterns
- `resolveEffectiveToolPolicy()` — Merge agent + group + sandbox policies
- `resolveSubagentToolPolicy()` — Subagent restrictions (no session management, limited gateway, etc.)
- `DEFAULT_SUBAGENT_TOOL_DENY` — Tools denied to subagents by default

---

## 5. Cron System (`src/cron/`)

### Key Files
- `service.ts` — `CronService` class: the public API
- `service/ops.ts` — Operations: start, stop, add, update, remove, run, wakeNow
- `service/jobs.ts` — Job creation, validation, next-run computation
- `service/timer.ts` — Timer scheduling, job execution, exponential backoff on errors
- `service/store.ts` — Job persistence (load/save/migrate)
- `service/state.ts` — `CronServiceState` (mutable state + event emitter)
- `service/locked.ts` — Lock wrapper for concurrent access
- `service/normalize.ts` — Input normalization
- `isolated-agent.ts` → `isolated-agent/run.ts` — Isolated session execution
- `isolated-agent/session.ts` — Session resolution for isolated runs
- `isolated-agent/delivery-target.ts` — Delivery target resolution
- `isolated-agent/helpers.ts` — Helper utilities
- `delivery.ts` — Delivery plan resolution
- `types.ts` — All type definitions
- `schedule.ts` — `computeNextRunAtMs()`: cron expression evaluation
- `parse.ts` — Parse absolute time strings
- `store.ts` — Low-level store file I/O
- `run-log.ts` — Cron run history log
- `normalize.ts` — Schedule/payload normalization
- `payload-migration.ts` — Migrate legacy payload format

### Job Types
```typescript
interface CronJob {
  id: string;
  agentId?: string;
  name: string;
  description?: string;
  enabled: boolean;
  deleteAfterRun?: boolean;
  createdAtMs: number;
  updatedAtMs: number;
  schedule: CronSchedule;       // 'at' | 'every' | 'cron'
  sessionTarget: CronSessionTarget; // 'main' | 'isolated'
  wakeMode: CronWakeMode;       // 'next-heartbeat' | 'now'
  payload: CronPayload;         // 'systemEvent' | 'agentTurn'
  delivery?: CronDelivery;      // For isolated: announce mode
  state: CronJobState;          // nextRunAtMs, lastRunAtMs, lastStatus, consecutiveErrors
}
```

### Schedule Types
- **at**: One-shot at absolute time (`{ kind: "at", at: "2026-02-05T09:00:00Z" }`)
- **every**: Recurring interval (`{ kind: "every", everyMs: 3600000, anchorMs?: number }`)
- **cron**: Cron expression (`{ kind: "cron", expr: "0 7 * * *", tz: "America/Chicago" }`)

### Session Targets
- **main**: Injects `systemEvent` text into main session (requires heartbeat)
- **isolated**: Runs `agentTurn` in isolated session with full agent, can announce results

### Error Handling
- Exponential backoff: 30s → 1m → 5m → 15m → 60m (by `consecutiveErrors`)
- Max job timeout: 10 minutes (`DEFAULT_JOB_TIMEOUT_MS`)
- `STUCK_RUN_MS = 2 hours` — detect stuck jobs
- One-shot jobs (`at`): disable after successful run, can optionally `deleteAfterRun`

### Critical Lessons
- **If HEARTBEAT.md is empty, heartbeats are skipped and `wakeMode: next-heartbeat` jobs never execute!** Always have content in HEARTBEAT.md.
- Cron store is at `~/.openclaw/state/cron.json`
- Run log at `~/.openclaw/state/cron-runs.jsonl`

---

## 6. Heartbeat System (`src/infra/heartbeat-runner.ts`)

### How It Works
1. `startHeartbeatRunner()` sets up a periodic timer per agent
2. Timer reads `HEARTBEAT.md` from workspace
3. If file is empty/missing, heartbeat is considered "effectively empty" → skipped
4. If content exists, injects `HEARTBEAT_TOKEN` + content as user message
5. Agent processes heartbeat, responds with `HEARTBEAT_OK` (no action) or actual content
6. System events (cron `wakeMode: next-heartbeat`) are delivered during heartbeat

### Key Files
- `infra/heartbeat-runner.ts` — Main runner, scheduling, delivery
- `infra/heartbeat-events.ts` — Event emission
- `infra/heartbeat-visibility.ts` — Per-channel visibility (showOk, showContent)
- `infra/heartbeat-wake.ts` — `requestHeartbeatNow()`, wake handler
- `auto-reply/heartbeat.ts` — Content validation, token stripping

### Configuration
```json
{
  "agents": {
    "defaults": {
      "heartbeat": {
        "every": "30m",
        "ackMaxChars": 300,
        "deliveryTarget": { "channel": "telegram", "to": "..." }
      }
    }
  }
}
```

---

## 7. Memory Search (`src/memory/`)

### Key Files
- `manager.ts` — `MemoryManager`: main class (~2400 lines), handles indexing, search, sync
- `manager-search.ts` — `searchVector()`, `searchKeyword()` query execution
- `internal.ts` — `chunkMarkdown()`, `listMemoryFiles()`, file entry building
- `embeddings.ts` — `createEmbeddingProvider()`: factory for OpenAI/Gemini/Voyage/local
- `embeddings-openai.ts` — OpenAI embedding client
- `embeddings-gemini.ts` — Gemini embedding client
- `embeddings-voyage.ts` — Voyage embedding client
- `hybrid.ts` — Hybrid search: BM25 + vector merge
- `sqlite.ts` — SQLite access (node:sqlite)
- `sqlite-vec.ts` — Load sqlite-vec extension for vector operations
- `memory-schema.ts` — Database schema (ensure tables exist)
- `sync-memory-files.ts` — Sync workspace memory files to index
- `sync-session-files.ts` — Sync session transcripts to index
- `batch-openai.ts`, `batch-gemini.ts`, `batch-voyage.ts` — Batch embedding requests
- `backend-config.ts` — Provider/model resolution for embeddings

### How It Works
1. Files in `MEMORY.md` and `memory/*.md` are chunked into ~400 token chunks (configurable)
2. Chunks are embedded via configured provider (OpenAI, Gemini, Voyage, or local llama)
3. Stored in SQLite with sqlite-vec extension for vector similarity
4. `memory_search` tool queries both FTS (keyword) and vector (semantic) indexes
5. Results merged via hybrid scoring (`mergeHybridResults`)
6. `memory_get` retrieves specific line ranges from source files

### Configuration (`agents/memory-search.ts`)
```typescript
{
  enabled: boolean;
  sources: ['memory', 'sessions'];
  provider: 'openai' | 'gemini' | 'voyage' | 'local' | 'auto';
  chunking: { tokens: 400, overlap: 80 };
  query: { maxResults: 6, minScore: 0.35 };
}
```

### Store Location
```
~/.openclaw/memory/<agentId>.sqlite
```

---

## 8. Channels (`src/channels/`, `src/telegram/`, `src/discord/`, etc.)

### Channel Plugin System (`channels/plugins/`)
Abstract interface for all messaging channels:
- `types.core.ts` — `ChannelPlugin`, `ChannelMeta`, `ChannelId`, etc.
- `types.plugin.ts` — Full plugin interface
- `index.ts` — `listChannelPlugins()`, `getChannelPlugin()`
- `catalog.ts` — Channel catalog
- `load.ts` — Plugin loading
- `normalize/*.ts` — Per-channel message normalization
- `outbound/*.ts` — Per-channel outbound message sending
- `onboarding/*.ts` — Per-channel setup wizards
- `actions/*.ts` — Per-channel message actions (reactions, edits, etc.)

### Telegram (`src/telegram/`)
- Uses **grammY** framework
- `bot.ts` — `createTelegramBot()`: creates and configures bot
- `bot-handlers.ts` — `registerTelegramHandlers()`: message/callback handlers
- `bot-message.ts` — `createTelegramMessageProcessor()`: processes incoming messages
- `bot-message-context.ts` — Build MsgContext from Telegram update
- `bot-message-dispatch.ts` — Dispatch to auto-reply pipeline
- `bot-native-commands.ts` — `/status`, `/model`, `/reset`, etc.
- `bot/delivery.ts` — Reply delivery to Telegram
- `bot/helpers.ts` — Forum topics, stream mode, group peer resolution
- `send.ts` — `sendTelegramMessage()`: message sending with chunking, formatting
- `format.ts` — Markdown → Telegram HTML conversion
- `inline-buttons.ts` — Inline keyboard buttons
- `model-buttons.ts` — Model picker buttons
- `draft-stream.ts` — Edit-in-place streaming
- `draft-chunking.ts` — Chunk management for streaming
- `webhook.ts` — Webhook setup/teardown
- `reaction-level.ts` — Reaction mode resolution (minimal/extensive)
- `monitor.ts` — `TelegramMonitor` gateway integration
- `download.ts` — File download from Telegram API
- `sent-message-cache.ts` — Track sent messages to avoid echo
- `network-config.ts` — Proxy, API URL configuration
- `network-errors.ts` — Telegram API error handling

### Discord (`src/discord/`)
- Uses **discord.js**
- `monitor.ts` — `DiscordMonitor` with message handling
- `monitor/message-handler.ts` — Inbound message processing
- `monitor/threading.ts` — Thread/channel resolution
- `send.ts` — Message sending (channels, DMs, threads)
- `send.guild.ts` — Guild-specific operations

### Signal (`src/signal/`)
- Uses **signal-cli** SSE connection
- `monitor.ts` — `SignalMonitor`
- `daemon.ts` — signal-cli daemon management
- `sse-reconnect.ts` — SSE reconnection logic

### Slack (`src/slack/`)
- Uses **Bolt** framework + HTTP mode
- `monitor.ts` — `SlackMonitor`
- `monitor/slash.ts` — Slash command handling
- `http/` — HTTP endpoint registration

### WhatsApp (`src/web/`)
- Uses **Baileys** library
- `auto-reply.ts` — WhatsApp auto-reply integration
- `inbound/` — Inbound message processing
- `login.ts` — QR code login
- `reconnect.ts` — Reconnection logic

### LINE (`src/line/`)
- LINE Messaging API
- `bot.ts` — Bot setup
- `webhook.ts` — Webhook verification
- `flex-templates.ts` — LINE Flex Message templates
- `markdown-to-line.ts` — Markdown conversion

---

## 9. Browser Control (`src/browser/`)

### Key Files
- `server.ts` — HTTP control server (REST API for agent browser tool)
- `server-context.ts` — Server context management, tab operations
- `routes/` — HTTP route handlers (snapshot, act, navigate, screenshot, etc.)
- `pw-session.ts` — Playwright session management, browser lifecycle
- `pw-tools-core.ts` + `pw-tools-core.*.ts` — Core Playwright operations (click, type, screenshot, snapshot, etc.)
- `pw-ai.ts` — AI-powered element resolution
- `pw-role-snapshot.ts` — Accessibility tree snapshot with role-based refs
- `cdp.ts` — Chrome DevTools Protocol direct access
- `cdp.helpers.ts` — CDP helper utilities
- `extension-relay.ts` — Chrome extension relay (attach to existing tabs)
- `chrome.ts` — Chrome executable detection
- `chrome.executables.ts` — Platform-specific Chrome paths
- `profiles-service.ts` — Browser profile management
- `profiles.ts` — Profile config resolution
- `client.ts` — Browser control client (for agent tool)
- `client-actions*.ts` — Client-side action handlers
- `bridge-server.ts` — Bridge for sandbox→host browser access
- `config.ts` — Browser configuration resolution
- `screenshot.ts` — Screenshot capture

### Profiles
- `openclaw` — Isolated browser managed by OpenClaw (Playwright)
- `chrome` — Chrome extension relay (attach to existing tabs via extension)

### Actions
- `snapshot` — Get accessibility tree (role-based or aria refs)
- `screenshot` — Capture page image
- `act` — Perform interactions (click, type, press, hover, drag, select, fill, wait, evaluate)
- `navigate` — Go to URL
- `open` — Open new tab
- `close` — Close tab
- `tabs` — List open tabs
- `console` — Get console logs
- `pdf` — Generate PDF
- `upload` — Upload files

---

## 10. Configuration (`src/config/`)

### Key Files
- `config.ts` — `loadConfig()`, `writeConfigFile()`, validation, legacy migration
- `schema.ts` — JSON Schema generation
- `zod-schema*.ts` — Zod validation schemas (split across many files)
- `types.ts` + `types.*.ts` — TypeScript type definitions for every config section
- `defaults.ts` — Default values
- `paths.ts` — State dir, config paths
- `config-paths.ts` — Config file path resolution
- `sessions.ts` — Re-exports from `sessions/`
- `sessions/session-key.ts` — `resolveSessionKey()`, `deriveSessionKey()`
- `sessions/store.ts` — Session store CRUD
- `sessions/transcript.ts` — Transcript file operations
- `sessions/metadata.ts` — Session metadata
- `sessions/paths.ts` — Session file paths
- `sessions/reset.ts` — Session reset logic
- `sessions/group.ts` — Group session key resolution
- `env-substitution.ts` — `${ENV_VAR}` substitution in config
- `includes.ts` — Config file includes
- `io.ts` — Config file I/O
- `merge-config.ts` — Config merging
- `legacy*.ts` — Legacy config migration rules

### Config Location
```
~/.openclaw/openclaw.json
```

### Key Config Sections
```javascript
{
  gateway: { port: 18789, bind: "loopback", auth: {}, controlUi: {}, http: {} },
  agents: {
    defaults: {
      workspace: "~/.openclaw/workspace",
      model: "anthropic/claude-sonnet-4-20250514",
      heartbeat: { every: "30m" },
      timeout: { run: "5m" },
      compaction: { instructions: "..." },
      contextPruning: { mode: "cache-ttl" },
    },
    list: [{ id: "main", ... }]
  },
  channels: {
    telegram: { token: "...", allowFrom: [...] },
    discord: { token: "...", guilds: {} },
    ...
  },
  cron: { enabled: true },
  memorySearch: { enabled: true, ... },
  sandbox: { enabled: false, docker: {} },
  models: { aliases: {}, fallbacks: {}, providers: {} },
  tools: { allow: [], deny: [] },
  hooks: { ... },
  plugins: { ... },
}
```

### Validation
Config is **strictly validated** against Zod schemas. Unknown keys cause Gateway to refuse to start. Run `openclaw doctor` to diagnose.

---

## 11. Sessions (`src/config/sessions/`, `src/sessions/`, `src/routing/`)

### Session Keys
Format: `agent:<agentId>:<channel>:<type>:<identifier>`

Examples:
- `agent:main:main` — Default DM session
- `agent:main:telegram:dm:<userId>` — Telegram DM
- `agent:main:discord:guild:<guildId>:channel:<channelId>` — Discord channel
- `agent:main:subagent:<uuid>` — Subagent session

### Session Key Resolution (`routing/session-key.ts`)
- `parseAgentSessionKey()` — Parse components
- `buildAgentMainSessionKey()` — Build main session key
- `normalizeAgentId()`, `normalizeMainKey()` — Normalization
- `isSubagentSessionKey()` — Check if subagent

### Session Store
- Per-agent JSON store at `~/.openclaw/agents/<agentId>/sessions.json`
- Tracks model, status, metadata per session key

### Queue Modes (`auto-reply/reply/queue/`)
- `steer` — Inject messages into current run
- `followup` — Hold until turn ends, then new turn
- `collect` — Batch messages together

---

## 12. Hooks System (`src/hooks/`)

### Key Files
- `hooks.ts` — Hook discovery and execution
- `loader.ts` — Load hook modules
- `types.ts` — `Hook`, `HookEntry`, `OpenClawHookMetadata`
- `internal-hooks.ts` — Internal hook handler interface
- `frontmatter.ts` — Parse HOOK.md frontmatter
- `workspace.ts` — Workspace hook discovery
- `installs.ts` — Hook installation
- `bundled/` — Bundled hooks:
  - `session-memory/handler.ts` — Auto-memory after compaction
  - `boot-md/handler.ts` — BOOTSTRAP.md processing
  - `soul-evil/handler.ts` — Soul personality override
  - `command-logger/handler.ts` — Command logging

### Hook Events
Hooks can handle: `command:new`, `session:start`, `session:compact`, `session:end`, etc.

---

## 13. Plugin System (`src/plugins/`)

### Key Files
- `types.ts` — `OpenClawPlugin` type (tools, hooks, channels, providers, config)
- `discovery.ts` — Find installed plugins
- `loader.ts` — Load plugin modules
- `registry.ts` — Plugin registry
- `runtime.ts` + `runtime/` — Plugin runtime environment
- `manifest.ts` — Plugin manifest parsing
- `tools.ts` — Plugin-provided tools
- `hooks.ts` — Plugin-provided hooks
- `slots.ts` — Plugin slot system
- `config-state.ts` — Plugin config persistence
- `install.ts` — Plugin installation
- `services.ts` — Plugin services handle

### Plugin Interface
Plugins can provide:
- Agent tools (via `OpenClawPluginToolFactory`)
- Hooks (via `OpenClawPluginHookOptions`)
- Channel adapters
- Model providers (via `ModelProviderConfig`)
- Config schemas
- CLI commands
- Gateway RPC methods
- HTTP routes

---

## 14. ACP (Agent Client Protocol) (`src/acp/`)

### Key Files
- `server.ts` — `serveAcpGateway()`: ACP server over stdio
- `translator.ts` — `AcpGatewayAgent`: translates between ACP and Gateway protocols
- `session-mapper.ts` — Map ACP sessions to OpenClaw session keys
- `event-mapper.ts` — Map Gateway events to ACP events
- `types.ts` — `AcpSession`, `AcpServerOptions`
- `client.ts` — ACP client for connecting to external ACP servers
- `commands.ts` — CLI commands for ACP

Implements the Agent Client Protocol spec for IDE/editor integration.

---

## 15. Media Understanding (`src/media-understanding/`)

Automatic transcription of audio, video, and images before agent processing:
- `apply.ts` — `applyMediaUnderstanding()`: entry point
- `runner.ts` — Execute transcription pipeline
- `resolve.ts` — Provider resolution
- `providers/` — Provider implementations:
  - `openai/audio.ts` — OpenAI Whisper
  - `deepgram/audio.ts` — Deepgram transcription
  - `google/audio.ts`, `google/video.ts` — Google AI
  - `groq/` — Groq Whisper
  - `anthropic/` — Claude vision
  - `minimax/` — MiniMax
- `format.ts` — Format transcription results
- `scope.ts` — Determine what needs transcription

---

## 16. Outbound Messaging (`src/infra/outbound/`)

Cross-channel message delivery:
- `deliver.ts` — `deliverOutboundPayloads()`: main delivery function
- `message.ts` — Message formatting
- `envelope.ts` — Message envelope creation
- `format.ts` — Channel-specific formatting
- `target-resolver.ts` — Resolve delivery targets (channel + recipient)
- `channel-adapters.ts` — Channel adapter resolution
- `agent-delivery.ts` — Agent reply delivery

---

## 17. CLI (`src/cli/`, `src/commands/`)

### Key Commands
```bash
openclaw gateway start/stop/restart/status    # Daemon management
openclaw agent --message "..."                 # Direct agent interaction
openclaw onboard [--install-daemon]            # Setup wizard
openclaw doctor [--fix]                        # Diagnose issues
openclaw status                                # Full status report
openclaw health                                # Quick health check
openclaw config get/set                        # Config management
openclaw update [--channel stable|beta|dev]    # Self-update
openclaw models list/set/scan                  # Model management
openclaw sessions list/reset/delete            # Session management
openclaw cron list/add/remove/run              # Cron management
openclaw browser ...                           # Browser control
openclaw plugins list/install/remove           # Plugin management
openclaw skills list/install                   # Skills management
openclaw channels add/remove/status            # Channel management
openclaw nodes list/describe/camera/screen     # Node management
openclaw logs --tail N                         # View logs
```

### CLI Structure
- `program.ts` → `program/build-program.ts` — Commander.js setup
- `run-main.ts` — Main CLI entry
- `deps.ts` — Dependency injection
- `gateway-cli.ts` — Gateway subcommands
- `daemon-cli.ts` — Daemon management
- `browser-cli.ts` — Browser subcommands
- `cron-cli.ts` — Cron subcommands
- `nodes-cli.ts` — Nodes subcommands
- `skills-cli.ts` — Skills subcommands

---

## 18. Workspace Files

OpenClaw injects these files into the system prompt as **Project Context**:

| File | Purpose |
|------|---------|
| `AGENTS.md` | Operating instructions, memory guidance |
| `SOUL.md` | Persona, tone, boundaries |
| `USER.md` | User profile |
| `IDENTITY.md` | Agent name, emoji |
| `TOOLS.md` | User-maintained tool notes |
| `BOOTSTRAP.md` | One-time first-run ritual (deleted after) |
| `MEMORY.md` | Long-term curated memories |
| `HEARTBEAT.md` | Heartbeat poll instructions |
| `memory/*.md` | Daily/topical memory files |

---

## Key Lessons from Source

1. **System prompt is massive** — Built dynamically from 20+ sections in `buildAgentSystemPrompt()`
2. **Compaction has 3 layers**: context pruning extension → compaction safeguard extension → `pruneHistoryForContextShare()`
3. **Cron needs heartbeats** — Empty HEARTBEAT.md → `isHeartbeatContentEffectivelyEmpty()` → heartbeats skip → `wakeMode: next-heartbeat` jobs never fire
4. **Config is strictly validated** — Zod schemas; unknown keys = no boot
5. **Sessions are JSONL** — Easy to inspect with `jq`
6. **Tool policy is layered**: agent config → group policy → sandbox policy → subagent restrictions
7. **Auth profile rotation**: profiles cycle on errors with cooldown, tracked per provider
8. **Memory is hybrid search**: both BM25 (keyword) and vector (semantic) results merged
9. **Auto-reply pipeline is deep**: 10+ stages from inbound message to outbound reply
10. **Exponential backoff on cron errors**: 30s → 1m → 5m → 15m → 60m
11. **Context pruning extension** trims stale tool results pre-API-call (separate from compaction)
12. **Subagent tool restrictions**: no session management, limited gateway, no cron by default

---

## Debugging Tips

### View Session Transcript
```bash
cat ~/.openclaw/agents/main/sessions/<session-id>.jsonl | jq -c '.role, .content[:80]'
# Or full messages:
cat ~/.openclaw/agents/main/sessions/<session-id>.jsonl | jq
```

### Check Gateway Logs
```bash
openclaw logs --tail 100
# Or direct:
journalctl --user -u openclaw -f  # systemd
```

### Inspect Config
```bash
openclaw config get
# Or via gateway RPC:
openclaw gateway call config.get --params '{}'
```

### Test Cron Job
```bash
openclaw cron list
openclaw cron run <jobId>
# Direct RPC:
openclaw gateway call cron.run --params '{"jobId":"<id>","mode":"force"}'
```

### Debug Cron Issues
```bash
# Check cron store
cat ~/.openclaw/state/cron.json | jq
# Check run log
tail -20 ~/.openclaw/state/cron-runs.jsonl | jq
# Check if heartbeat is working
cat ~/.openclaw/workspace/HEARTBEAT.md  # Must not be empty!
```

### Memory Search Debug
```bash
ls ~/.openclaw/memory/
openclaw memory status
# SQLite direct:
sqlite3 ~/.openclaw/memory/main.sqlite "SELECT count(*) FROM memory_chunks;"
```

### Session Store
```bash
cat ~/.openclaw/agents/main/sessions.json | jq
```

### Check Auth Profiles
```bash
openclaw models auth
openclaw models list --status
```

### Debug Telegram Issues
```bash
# Check if bot is connected
openclaw channels status
# Verify allowFrom
openclaw config get | jq '.channels.telegram'
```

### Compaction Issues
```bash
# Check session transcript size
wc -l ~/.openclaw/agents/main/sessions/*.jsonl
# Force compact
openclaw gateway call sessions.compact --params '{"sessionKey":"agent:main:main"}'
```

---

## Source Code Reading Order

For understanding OpenClaw deeply:

1. `src/entry.ts` → `src/cli/run-main.ts` — How CLI starts
2. `src/gateway/server.impl.ts` — Control plane startup
3. `src/auto-reply/reply/get-reply.ts` — Message processing pipeline
4. `src/auto-reply/reply/agent-runner.ts` — Agent execution
5. `src/agents/pi-embedded-runner/run.ts` — Core agent run
6. `src/agents/system-prompt.ts` — How the system prompt is built
7. `src/agents/compaction.ts` — Context management
8. `src/agents/pi-embedded-subscribe.ts` — Response streaming
9. `src/cron/service/timer.ts` — Scheduled job execution
10. `src/infra/heartbeat-runner.ts` — Heartbeat system
11. `src/memory/manager.ts` — Memory indexing and search
12. `src/telegram/bot.ts` — Channel example (Telegram)
13. `src/config/config.ts` — Configuration loading
14. `src/agents/pi-tools.policy.ts` — Tool availability
15. `src/agents/subagent-registry.ts` — Subagent lifecycle

---

## v2026.2.9 Changes (from git log)

Key changes in this release:
- **fix(telegram)**: DM `allowFrom` now matches against sender user ID (regression fix)
- **fix(telegram)**: Avoid nested reply quote misclassification
- **fix(auth)**: Strip line breaks from pasted API keys
- **fix(web_search)**: Fix invalid model name sent to Perplexity
- **fix(onboarding)**: Auto-install shell completion in QuickStart
- **CI**: Added code-size gates, tiered lint/format checks
- TypeScript: Added extensions to tsconfig, fixed type errors
- Plugin system improvements (plugins list source display)

---

*Last updated: 2026-02-09 from full source code review of OpenClaw v2026.2.9.*
