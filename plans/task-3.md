# Task 3 Implementation Plan

1. **Understand the Goal**: Implement a `query_api` tool so the agent can interact with the dynamic backend API to answer questions.
2. **Implement `query_api` Tool**: Add a tool function in `agent.py` that accepts an endpoint, method, and headers. It will read the `AGENT_API_BASE_URL` environment variable.
3. **Update System Prompt**: Instruct the agent to specifically look for division operations and None-unsafe sorting when reviewing `analytics.py`.
4. **Update `AGENT.md`**: Document the architecture and lessons learned (200+ words).
