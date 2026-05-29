# Ops-Pilot — Frontend

Next.js 15 · TypeScript · Tailwind CSS · Framer Motion · anime.js · Jest

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

## Pages

```
/              Landing page — animated hero, agent pipeline, capabilities CTA
/chat          AI incident analysis — SSE streaming + live agent output
/login         Sign in with email and password
/register      Create a new account
/help          Operator guide and troubleshooting reference
/settings      Runtime LLM provider, model, and API key configuration
/contact       Support and feedback
```

---

## Project Structure

```
app/
  page.tsx                  Landing / home page
  chat/page.tsx             Incident chat workspace
  login/page.tsx            Authentication
  register/page.tsx         Registration
  help/page.tsx             Operator guide
  settings/page.tsx         LLM runtime settings
  contact/page.tsx          Contact form
  layout.tsx                Root layout + providers
  globals.css               Tailwind base + CSS variables

  lib/
    api.ts                  API client with Zod validation and error handling

  components/               Shared UI components

public/                     Static assets
```

---

## API Client (`app/lib/api.ts`)

- Zod validation applied before every request
- `ApiException` class carries exact backend error (`detail`, `trace_id`, `path`)
- Login and registration errors surface the backend's exact message
- Guardrail violations from SSE streams are propagated as `ApiException`
- Token strategy: access token in cookie, refresh token in cookie
- `authHeaders()` helper appends Bearer token to all authenticated requests

---

## Error Propagation

Backend errors are surfaced verbatim to the UI:

```
Backend returns:
{ "detail": "Email or username already registered.", "trace_id": "abc-123" }

UI catches:
ApiException { status: 409, body: { detail: "...", trace_id: "..." } }
→ Displayed in error banner with exact backend message
```

---

## Environment Variables

| Variable              | Required | Description                                   |
| --------------------- | -------- | --------------------------------------------- |
| `NEXT_PUBLIC_API_URL` | Yes      | Backend base URL (e.g. http://localhost:8000) |

---

## Testing

Tests use Jest with React Testing Library.

```bash
npm test                    # run all tests
npm run test:coverage       # with coverage report
npm run test -- --watch     # watch mode
```

Mock files are located in `__mocks__/`.
Jest configuration is in `jest.config.js` and `jest.setup.ts`.

---

## Tailwind and Theming

Design tokens are defined in `tailwind.config.ts`:

```
bg-void          Primary background (near-black)
bg-surface-1     Card surface
bg-surface-2     Elevated card surface
text-chrome      Primary text
text-chrome-dim  Secondary / muted text
text-plasma      Accent green  (#00ff88)
text-ember       Accent red    (#ff4444)
text-ice         Accent blue   (#00ccff)
text-amber       Warning amber (#ffaa00)
border-border-1  Subtle border
border-border-2  Prominent border
```

Fonts: `font-display` (headings) and `font-mono` (code / labels).

---

## Docker

```bash
# Build and run via backend docker-compose
docker compose -f docker-compose.yml -f docker-compose.dev.yml up frontend
```

The `Dockerfile` in this directory produces the production Next.js image used
in `docker-compose.prod.yml`.
