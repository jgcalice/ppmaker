# ADR-001: SSE vs Polling for AI Storytelling Streaming

## Status: Accepted

## Context

The PPMaker backend calls the Anthropic Claude API to generate a storytelling outline (5-15 slides with narrative structure). This AI call is inherently slow: depending on content complexity and slide count, it takes 10-60 seconds to complete. During this time, the user stares at a loading screen with no feedback — a poor experience that erodes trust in the product.

We need a mechanism to stream partial progress (chunks of the outline as the LLM generates them) from the FastAPI backend to the Next.js frontend so the user sees content appearing progressively. The main options are: Server-Sent Events (SSE), client polling a job-status endpoint, WebSockets, and long-polling.

Key constraints:
- The communication is unidirectional: server pushes progress to client. The client does not send data mid-stream.
- The backend is Python FastAPI; the frontend is Next.js 14 (browser-side fetch).
- MVP deployment is Docker Compose (no managed WebSocket infra).
- The Anthropic SDK natively supports streaming responses, so the backend can forward chunks as they arrive.

## Decision

We chose **Server-Sent Events (SSE)** for streaming AI storytelling progress from backend to frontend.

## Alternatives Considered

| Option | Pros | Cons |
|--------|------|------|
| **SSE (chosen)** | Native browser support; unidirectional fits our use case perfectly; trivial to implement with FastAPI (`sse-starlette`); automatic reconnection built into protocol; works over standard HTTP/1.1 and HTTP/2; low overhead | Cannot send data from client mid-stream (not needed here); limited to ~6 concurrent connections per domain in HTTP/1.1 (mitigated by HTTP/2 or single-stream-per-user pattern); `EventSource` API does not support POST (requires `fetch` + `ReadableStream` instead) |
| **Polling + job queue** | Simple to implement; stateless; works behind any proxy; easy to debug | Adds latency (polling interval); wastes bandwidth with empty responses; requires job storage (Redis/DB); no real-time feel — progress appears in discrete jumps; added infrastructure complexity for MVP |
| **WebSockets** | Full-duplex; low latency; persistent connection | Over-engineered for unidirectional streaming; more complex server setup; requires connection state management; harder to scale; needs sticky sessions or Redis pub/sub for multi-instance; overkill for MVP |
| **Long-polling** | Works behind restrictive proxies; simulates push | High connection churn; complex timeout management; server holds connections open consuming resources; poor DX compared to SSE |

## Consequences

### Good
- **Progressive UX**: Users see slide content appearing in real-time as Claude generates it, reducing perceived latency from 60s to <1s for first visible content
- **Simplicity**: SSE is a thin layer over HTTP — no new protocol, no connection state, no additional infrastructure
- **Anthropic SDK alignment**: The SDK streams responses natively; our backend simply forwards chunks, no buffering or intermediate storage needed
- **Resilience**: If the connection drops, the client can reconnect and receive a "done" event with the complete outline (idempotent endpoint)
- **No infrastructure overhead**: No Redis, no job queue, no WebSocket server — just HTTP

### Bad
- **Proxy configuration required**: Reverse proxies (NGINX, Cloudflare) may buffer SSE responses by default; requires explicit `X-Accel-Buffering: no` and increased timeouts
- **No POST with EventSource**: The browser's `EventSource` API only supports GET. Since our `/storytelling` endpoint is POST (sends content body), the frontend must use `fetch()` with `response.body.getReader()` instead — slightly more code than native `EventSource`
- **Connection limit**: HTTP/1.1 allows ~6 concurrent connections per domain. If a user opens multiple tabs generating simultaneously, streams may queue. Acceptable for MVP; HTTP/2 multiplexing solves this at scale
- **No client-to-server mid-stream**: If we later need the user to cancel generation mid-stream, we need a separate cancel endpoint (not a limitation of SSE per se, just a design note)

## Implementation Notes

- **FastAPI SSE**: Use the `sse-starlette` library with `EventSourceResponse`. The endpoint yields events as the Anthropic SDK streams chunks.
- **Client**: Use native `fetch()` with `response.body.getReader()` and `TextDecoderStream` (not `EventSource`, which doesn't support POST bodies).
- **Event format**: Each SSE event carries `type: "chunk"` (partial outline data) or `type: "done"` (final complete outline). Errors use `type: "error"`.
- **NGINX/proxy**: Disable buffering for the SSE endpoint with header `X-Accel-Buffering: no`. Set `proxy_buffering off` in NGINX config.
- **Timeout**: Set `keepalive_timeout` > 120s if behind NGINX. FastAPI's default timeout is sufficient; configure Uvicorn's `--timeout-keep-alive 120`.
- **Error handling**: If the Claude API errors mid-stream, send an `error` event with a user-friendly message and close the stream gracefully.

## Fitness Function

**Test**: SSE stream for a 10-slide presentation must deliver the first progress event within 500ms of connection establishment and the final complete outline within 90s. Automated test: open SSE connection to `/api/v1/storytelling`, assert first `chunk` event arrives in <500ms and `done` event arrives in <90s.
