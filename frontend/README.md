# Ops-Pilot — Frontend

Next.js 15 · TypeScript · Tailwind CSS · Framer Motion · anime.js · Jest

---

## Table of Contents

- [Overview](#overview)
- [Setup](#setup)
- [Available Scripts](#available-scripts)
- [Pages and Features](#pages-and-features)
- [Incident Chat Workspace](#incident-chat-workspace)
- [Agent Pipeline UI](#agent-pipeline-ui)
- [Document Upload and Processor](#document-upload-and-processor)
- [Streaming and SSE](#streaming-and-sse)
- [Explainability System](#explainability-system)
- [Agent Toggles and Configuration](#agent-toggles-and-configuration)
- [Authentication and Auth Flow](#authentication-and-auth-flow)
- [Error Handling and Guardrails UI](#error-handling-and-guardrails-ui)
- [Settings and LLM Configuration](#settings-and-llm-configuration)
- [Project Structure](#project-structure)
- [API Client](#api-client-applibapts)
- [Design System and Theming](#design-system-and-theming)
- [Testing](#testing)
- [Docker](#docker)
- [Environment Variables](#environment-variables)

---

## Overview

Ops-Pilot's frontend is a Next.js 15 App Router application that connects to the backend's Server-Sent Events (SSE) stream and renders a real-time multi-agent incident analysis workspace. Every step of the pipeline — classification, entity extraction, graph traversal, root cause analysis, remediation — is surfaced as a live card with input, output, and error details visible without leaving the chat.

The UI is designed for on-call engineers who need fast, explainable answers during incidents. It supports file uploads, multi-session history, configurable agent pipelines, and runtime LLM provider switching.

---

## Setup

```bash
npm install
cp .env.example .env.local
# Set: NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
# Open http://localhost:3000
```

---

## Available Scripts

```bash
npm run dev            # development server with hot reload
npm run build          # production build
npm run start          # serve production build
npm test               # Jest unit tests
npm run test:coverage  # Jest with coverage report
npm run type-check     # TypeScript strict check
npm run lint           # ESLint
```

---

## Pages and Features

```
/              Landing page — animated hero, agent pipeline visualisation, CTA
/chat          Incident analysis workspace — SSE streaming + live agent output
/login         Sign in with email and password
/register      Create a new account
/help          Operator guide, agent reference, and troubleshooting
/settings      Runtime LLM provider, model, and API key configuration
/contact       Support and feedback form
/profile       User profile management
```

---

## Incident Chat Workspace

The `/chat` page is the core of Ops-Pilot. It provides:

**Multi-session management**
Sessions are stored in `localStorage` under the key `ops_pilot_chat_sessions_v4`. Each session has a local UUID, an optional backend session UUID, a title derived from the first query, and a full message history. Users can create new sessions, switch between past sessions in the sidebar, and delete sessions. Sessions persist across page reloads.

**Starter prompts**
Three pre-built example incident descriptions appear on the landing state to help users quickly start an analysis without needing to write a query from scratch.

**Query input**
A fixed bottom input bar with a textarea supporting `Enter` to submit (Shift+Enter for newline). The bar shows a paperclip icon for document uploads and disables submission while a stream is in progress.

**Attached file previews**
Uploaded documents are shown as pill badges above the input bar with filename and character count before submission. They can be removed before sending.

**Message history**
User messages appear right-aligned. Assistant messages render the `natural_response` field as full Markdown using `react-markdown` with custom heading, code, and link renderers. When citations are present, a collapsible citation list appears below the narrative.

**Auto-scroll with override**
The chat panel auto-scrolls to the latest message during streaming. A floating "scroll to bottom" button appears when the user manually scrolls up, letting them return without interrupting their review of earlier content.

---

## Agent Pipeline UI

A right sidebar (or bottom panel on mobile) shows the full agent timeline for every turn:

| Agent               | Role                                                         |
| ------------------- | ------------------------------------------------------------ |
| Orchestrator        | Routes the query through the pipeline                        |
| Document Processor  | Active only when a file is uploaded                          |
| Classifier          | Extracts service, severity, type, confidence                 |
| Entity Extractor    | Parses services, metrics, error codes, time ranges           |
| Repo Scanner        | Checks recent GitHub commits, PRs, CI status                 |
| Terraform Scanner   | Checks IaC drift and recent applies                          |
| Graph Analyzer      | Maps blast radius and ownership via Neo4j                    |
| Web Intelligence    | DuckDuckGo search for CVEs and post-mortems                  |
| Ops Analyst         | Reads telemetry from the Ops Inspector MCP server            |
| Crew Intelligence   | Multi-agent CrewAI synthesis (Researcher → Analyst → Writer) |
| Root Cause Analyzer | Builds causal chain and timeline reconstruction              |
| Remediator          | Generates immediate actions, rollback, escalation paths      |
| Conversationalist   | Synthesises the final human-readable narrative               |

Each agent entry in the sidebar shows:

- An icon and colour coded by agent type
- A live pulsing dot that changes colour: cyan (running), emerald (complete), red (error)
- The latest status across all steps for that agent
- A toggle (for optional agents) or locked state (for required agents)

During a stream, agents light up in sequence as they execute. Completed agents remain highlighted for the duration of the session.

---

## Document Upload and Processor

The Document Processor agent is **disabled by default** and is **automatically enabled only when the user uploads a file**.

**Upload flow:**

1. User clicks the paperclip icon in the input bar.
2. `uploadDocuments()` POST request sends files to `/api/v1/incident/upload-documents`.
3. Backend converts each file to Markdown using MarkItDown.
4. The returned `{ filename, markdown, characters }` objects are stored in `attachments` state.
5. `document_processor` is added to `enabledAgentKeys`.
6. Attached files appear as removable pills above the input bar.

**Submission flow:**

1. On submit, `attachments` are concatenated into a `documentContext` string.
2. `document_processor` is included in the `enabled_agents` parameter sent to the SSE endpoint.
3. The backend stream starts a `running` → `complete` Document Processor step.
4. After submit, `attachments` is cleared and `document_processor` is removed from `enabledAgentKeys` so the next turn starts with no document attached.

**Supported formats:** PDF, DOC, DOCX, PPT, PPTX, XLS, XLSX, HTML, Markdown, CSV, TXT.

**In the sidebar:** The Document Processor agent row shows with a lock icon when no file is attached (disabled) and activates with a pulsing dot during the processing step.

---

## Streaming and SSE

The entire backend pipeline is consumed as a Server-Sent Events stream via `streamIncident()` in `app/lib/apis.ts`.

**Event types received:**

| Event         | Meaning                                                          |
| ------------- | ---------------------------------------------------------------- |
| `session`     | Session UUID assigned by the backend                             |
| `step`        | Agent step update (running / complete / error / skipped)         |
| `graph`       | Graph traversal result (same shape as step but typed separately) |
| `reasoning`   | Root cause reasoning output                                      |
| `result`      | Final structured result with all pipeline outputs                |
| `error_event` | Top-level stream error (e.g. guardrail violation)                |
| `done`        | Stream complete                                                  |

**Reconnection:** The `streamIncident()` function returns a stop function stored in `stopStreamRef`. When a new query is submitted mid-stream, the previous stream is cancelled before the new one starts.

**Result processing:** On `result` events, the structured data (service, severity, root cause, remediation steps, web citations, timeline) is extracted and attached to the assistant message, enabling rich post-stream rendering.

---

## Explainability System

Every agent step emitted by the backend creates an `ExplainabilityEvent` stored in `explainabilityEvents` state. These are rendered as a scrollable column of `ExplainabilityCard` components.

**Each card shows:**

- Agent icon and colour
- Step name and live status dot
- Truncated input hint (first 80 chars)
- Truncated output hint (first 80 chars)

**On hover:** A portal-rendered tooltip appears to the right of the card with the agent name, full description, input, output, and status.

**On click:** An `ExplainabilityModal` opens with full details:

- Agent header with icon and colour
- Status badge with pulsing animation
- Agent timeline description (what the agent does in the pipeline)
- "What this step does" — the `description` field from the backend (hidden on error to avoid duplication)
- Error block — shows the raw error string in a red box (shown only when status is error)
- Input block — the actual input sent to the agent (truncated at 300 chars in the backend, shown in full in the modal)
- Output block — the actual output produced by the agent
- Pipeline progress — a chip list of all completed steps up to this point
- Raw agent data — a collapsible section showing all additional fields from the event payload

**Error deduplication:** When a step errors, the `description` field is suppressed in "What this step does" to prevent the error string appearing twice. The error appears only once, in the dedicated error block.

---

## Agent Toggles and Configuration

The agent pipeline sidebar includes a toggle for each optional agent. Toggling an agent adds or removes its key from `enabledAgentKeys`. On submit, `enabledAgentKeys` is serialised as a comma-separated string and passed to the SSE endpoint as the `enabled_agents` query parameter.

**Required agents** (cannot be toggled off): `orchestrator`, `classifier`, `entity_extractor`, `graph_analyzer`, `root_cause_finder`, `remediator`, `conversationalist`.

**Optional agents** (user-toggleable): `repo_scout`, `terraform_scout`, `web_searcher`, `ops_analyst`, `crew`.

**Document Processor** is a special case: it is not in the required set and cannot be manually toggled. It is added automatically to `enabledAgentKeys` when files are uploaded and removed after the turn completes.

The backend always enforces `REQUIRED_AGENTS` regardless of what the frontend sends, so required agents cannot be accidentally disabled via the API.

---

## Authentication and Auth Flow

All API calls use a JWT Bearer token stored in an HTTP-only cookie (set by the backend). The `authHeaders()` helper in `app/lib/apis.ts` reads the token and appends the `Authorization: Bearer <token>` header.

**Login:** POST `/api/v1/auth/login` → returns `access_token` and `refresh_token`. Both are stored as cookies.

**Register:** POST `/api/v1/auth/register` → creates account and returns the same token pair.

**Token refresh:** When a 401 is received, the API client attempts one refresh via POST `/api/v1/auth/refresh` with the refresh token. On success, the new access token replaces the old one and the original request is retried. On failure, the user is redirected to `/login`.

**Logout:** Clears token cookies and redirects to `/login`.

**Authenticated routes:** All routes except `/`, `/login`, `/register`, and the public stream endpoint require a valid access token. The `ProfileMenu` component in the top-right shows the authenticated user's username and provides a logout button.

**Guest streaming:** The SSE stream endpoint uses `get_optional_user`, allowing unauthenticated users to stream. Sessions created by unauthenticated users have `user_id=null` in the database.

---

## Error Handling and Guardrails UI

**Guardrail violations** (prompt injection, PII, excessive length) are emitted by the backend as `error_event` SSE events with `code: GUARDRAIL_VIOLATION`. The frontend catches these and displays them as a system error message in the chat, not as a pipeline step.

**Agent errors** appear as red-bordered `ExplainabilityCard` entries in the explainability column. Clicking them opens the modal with the full error string in the error block. The pipeline continues past non-fatal errors (repo_scout, terraform_scout, web_searcher, ops_analyst, crew); fatal errors (classifier, graph_analyzer) may degrade the final output quality but do not crash the stream.

**Network errors** from `fetch` are caught by `ApiException` and displayed as inline error messages in the chat panel.

**File upload errors** are surfaced as assistant messages: `Document Processor error: <detail>`.

---

## Settings and LLM Configuration

The `/settings` page allows users to configure their LLM provider at runtime without a server restart:

- **Provider**: `openai`, `anthropic`, or `google`
- **Model**: any model string valid for the selected provider (e.g. `gpt-4o`, `claude-3-5-sonnet-20241022`, `gemini-1.5-pro`)
- **API Key**: stored encrypted server-side and used only for that user's requests

Settings are persisted in the backend database and loaded per-user on each request via the settings API.

---

## Project Structure

```
app/
  page.tsx                  Landing / home page
  chat/
    page.tsx                Incident chat workspace (main feature)
    layout.tsx              Chat layout wrapper
  (auth)/
    login/page.tsx          Email + password login
    register/page.tsx       Account registration
  auth/callback/page.tsx    OAuth callback handler
  help/page.tsx             Operator guide, agent reference, troubleshooting
  settings/page.tsx         LLM runtime settings
  contact/page.tsx          Support and feedback
  profile/page.tsx          User profile management
  layout.tsx                Root layout + providers + font loading
  globals.css               Tailwind base + CSS custom properties

  lib/
    apis.ts                 API client — Zod validation, auth headers, SSE stream

  components/
    ProfileMenu.tsx          Authenticated user menu with logout

public/                     Static assets (SVGs)

__mocks__/
  styleMock.js              Jest CSS module mock

__tests__/
  api.test.ts               API client unit tests
  guardrails.test.ts        Guardrail behaviour tests
```

---

## API Client (`app/lib/apis.ts`)

- Zod validation applied before every request
- `ApiException` class carries exact backend error (`detail`, `trace_id`, `path`)
- Login and registration errors surface the backend's exact message
- Guardrail violations from SSE streams are propagated as `ApiException`
- Token strategy: access token in cookie, refresh token in cookie
- Automatic token refresh on 401 with one retry
- `authHeaders()` helper appends `Authorization: Bearer <token>` to all authenticated requests
- `streamIncident(query, sessionId, documentContext, enabledAgents, onEvent)` — opens SSE connection, calls `onEvent` for each parsed event, returns a stop function
- `uploadDocuments(files)` — multipart POST, returns `{ documents: [{ filename, markdown, characters }] }`

---

## Design System and Theming

All design tokens are defined as Tailwind custom colours in `tailwind.config.ts` and as CSS custom properties in `globals.css`:

| Token             | Value     | Usage                         |
| ----------------- | --------- | ----------------------------- |
| `bg-void`         | `#0a0a0f` | Primary background            |
| `bg-surface-1`    | `#111118` | Card surface                  |
| `bg-surface-2`    | `#16161f` | Elevated card                 |
| `text-chrome`     | `#e8e8f0` | Primary text                  |
| `text-chrome-dim` | `#888899` | Secondary / muted text        |
| `text-plasma`     | `#00ff88` | Accent green (running/active) |
| `text-ember`      | `#ff4444` | Accent red (errors)           |
| `text-ice`        | `#00ccff` | Accent blue (info)            |
| `text-amber`      | `#ffaa00` | Warning amber                 |
| `border-border-1` | subtle    | Low-contrast borders          |
| `border-border-2` | prominent | High-contrast borders         |

Fonts: `font-display` for headings (variable weight), `font-mono` for all code, labels, and agent data.

Animations are provided by `framer-motion` for page transitions, card entrances, status dot pulses, and modal open/close. Agent status dots use a spring-physics pulse animation keyed to the status string so they re-trigger on every status change.

---

## Testing

Tests use Jest with React Testing Library and `jest-environment-jsdom`.

```bash
npm test                    # run all tests
npm run test:coverage       # with coverage report
npm run test -- --watch     # watch mode
npm run test -- --testPathPattern=api  # single file
```

Mock files in `__mocks__/`. Jest configuration in `jest.config.js` and `jest.setup.ts`.

Test files:

- `__tests__/api.test.ts` — API client, error propagation, guardrail violation handling
- `__tests__/guardrails.test.ts` — Frontend-side guardrail and input validation

---

## Docker

```bash
# Build and run via root docker-compose
docker compose -f docker-compose.yml -f docker-compose.dev.yml up frontend

# Build the production image standalone
docker build -t ops-pilot-frontend .
docker run -p 3000:3000 -e NEXT_PUBLIC_API_URL=http://localhost:8000 ops-pilot-frontend
```

The `Dockerfile` uses a multi-stage build: Node 20 Alpine for building, Node 20 Alpine for serving. The production image runs `next start` on port 3000.

---

## Environment Variables

| Variable              | Required | Description                                     |
| --------------------- | -------- | ----------------------------------------------- |
| `NEXT_PUBLIC_API_URL` | Yes      | Backend base URL (e.g. `http://localhost:8000`) |
