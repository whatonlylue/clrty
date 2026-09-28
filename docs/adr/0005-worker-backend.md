# 0005. Worker backend

Date: 2026-09-28
Status: Accepted

## Context

The refactoring loop needs to call an LLM to propose edits. clrty must speak multiple APIs—Anthropic, OpenAI, and OpenAI-compatible endpoints like OpenRouter and vLLM—to serve diverse users and avoid vendor lock-in. The question is which backend(s) to use.

## Options considered

**Own model client:** Thin reqwest client implementing Anthropic Messages API and OpenAI-compatible chat completions, with a replay backend for deterministic testing (Build plan › Model client). Provides provider-agnostic full control of the loop.

**Claude Agent SDK:** Mature SDK for building agents. However, it is Python and TypeScript only, which means it cannot be embedded in the Rust binary. Additionally, it pulls the loop toward model-driven control when clrty's agent loop must remain fully deterministic and testable.

## Decision

**Own model client (Anthropic Messages + OpenAI-compatible) with claude CLI kept as a second backend.** The core loop uses the thin reqwest client. The claude CLI backend is retained as an option (Build plan › Assumed decisions) for users who prefer it, but it is not the primary path.

## Consequences

clrty maintains architectural independence and provider flexibility. The abstraction supports Anthropic Messages, OpenAI-compatible endpoints (OpenRouter, vLLM, Ollama, LM Studio), claude CLI headless, and recorded replay for deterministic testing (Build plan › Model client). Prompt caching is available on the Anthropic backend, reducing token cost on long sessions (Build plan › Hook and MCP protocol).
