# Ops-Pilot Frontend

Next.js 14 + TypeScript + Tailwind + Framer Motion + React Flow + Zustand

## Setup

    npm install
    cp .env.example .env.local
    # .env.local: NEXT_PUBLIC_API_URL=http://localhost:8000
    npm run dev

## Test

    npm test               # Jest unit tests
    npm run test:coverage  # with coverage
    npm run type-check     # TypeScript

## Pages

    /             Landing page — animated hero, pipeline diagram, CTA
    /login        Sign in with email + password
    /register     Create account
    /chat         AI incident analysis — SSE streaming + React Flow graph

## API Client (app/lib/api.ts)

- Zod validation before every request
- ApiException class carries exact backend error (detail, trace_id, path)
- Login/register errors surface the backend's exact error message
- Guardrail violations from SSE stream propagated to UI as ApiException
- Token rotation: access token in cookie, refresh token in cookie
- authHeaders() helper adds Bearer token to all authenticated requests

## Error Propagation

Backend errors are propagated exactly to the UI:

    Backend returns:
    { "detail": "Email or username already registered.", "trace_id": "abc-123" }

    UI catches:
    ApiException { status: 409, body: { detail: "...", trace_id: "..." } }
    → displayed in error banner with exact backend message

## Environment

    NEXT_PUBLIC_API_URL   Backend URL (default: http://localhost:8000)