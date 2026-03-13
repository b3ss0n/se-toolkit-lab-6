# Task 3: The System Agent - Implementation Plan

## Overview

Task 3 extends the agent from Task 2 by adding a `query_api` tool that can interact with the deployed backend API. This enables the agent to answer both static system questions (framework, ports, status codes) and data-dependent queries (item count, scores, analytics).

## New Tool: `query_api`

### Purpose

Call the deployed backend LMS API to retrieve real-time data or system information.

### Parameters

- `method` (string, required): HTTP method (GET, POST, PUT, DELETE, etc.)
- `path` (string, required): API endpoint path (e.g., `/items/`, `/analytics/completion-rate`)
- `body` (string, optional): JSON request body for POST/PUT requests

### Returns

JSON string containing:

- `status_code`: HTTP status code
- `body`: Response body as JSON object or string

### Authentication

The tool must authenticate using `LMS_API_KEY` from environment variables (read from `.env.docker.secret`).

```python
headers = {
    "Authorization": f"Bearer {lms_api_key}",
    "Content-Type": "application/json"
}
```

### Security

- Validate HTTP method is allowed (GET, POST, PUT, DELETE, PATCH)
- Prevent path traversal (no `../` in path)
- Limit response size to prevent memory issues

## Environment Variables

The agent must read ALL configuration from environment variables:

| Variable | Purpose | Source | Default |
|----------|---------|--------|---------|
| `LLM_API_KEY` | LLM provider API key | `.env.agent.secret` | - |
| `LLM_API_BASE` | LLM API endpoint URL | `.env.agent.secret` | - |
| `LLM_MODEL` | Model name | `.env.agent.secret` | - |
| `LMS_API_KEY` | Backend API key for query_api | `.env.docker.secret` | - |
| `AGENT_API_BASE_URL` | Base URL for query_api | Optional | `http://localhost:42002` |

**Important:** The autochecker injects its own values for these variables. Hardcoding any of them will cause the agent to fail evaluation.

## Tool Schema (Gemini API)

```python
{
    "name": "query_api",
    "description": "Call the backend LMS API to retrieve data or system information. Use this for questions about database content, analytics, or system status.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "method": {
                "type": "STRING",
                "description": "HTTP method (GET, POST, PUT, DELETE)"
            },
            "path": {
                "type": "STRING",
                "description": "API endpoint path (e.g., /items/, /analytics/completion-rate)"
            },
            "body": {
                "type": "STRING",
                "description": "Optional JSON request body for POST/PUT requests"
            }
        },
        "required": ["method", "path"]
    }
}
```

## System Prompt Update

The system prompt should guide the LLM to choose the right tool:

```
You are a documentation and system assistant with access to three tools:
- list_files: List files in a directory
- read_file: Read the contents of a file
- query_api: Call the backend LMS API

When answering questions:
1. For wiki/documentation questions → use list_files and read_file
2. For system facts (framework, ports, status codes) → use read_file on source code
3. For data queries (item count, scores, analytics) → use query_api
4. For bug diagnosis → use query_api to reproduce, then read_file to find the bug

Always include the source when you find information in files.
For API queries, describe the endpoint and response.
```

## Implementation Steps

1. **Add `query_api` tool function:**
   - Read `LMS_API_KEY` and `AGENT_API_BASE_URL` from environment
   - Build HTTP request with authentication
   - Execute request and parse response
   - Return status_code and body

2. **Update tool schema:**
   - Add `query_api` to Gemini function declarations
   - Include clear description and parameter documentation

3. **Update environment loading:**
   - Add `LMS_API_KEY` as optional (with warning if missing)
   - Add `AGENT_API_BASE_URL` with default `http://localhost:42002`

4. **Update agentic loop:**
   - Handle `query_api` in tool execution
   - Format API responses for LLM consumption

5. **Test with run_eval.py:**
   - Run benchmark
   - Fix failing questions
   - Iterate until 100% pass rate

## Benchmark Strategy

### Initial Run

```bash
uv run run_eval.py
```

### Debugging Workflow

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| Agent doesn't use query_api for data questions | Tool description unclear | Improve description to emphasize "data queries" |
| API returns 401 | Missing LMS_API_KEY | Check environment variable loading |
| API returns 404 | Wrong path | Read API documentation, check endpoint |
| Agent times out | Too many tool calls | Reduce max iterations, optimize prompts |
| Answer close but wrong | Phrasing doesn't match expected keywords | Adjust system prompt for precision |
| Gemini API unavailable | Location restrictions | Agent reads config from env, autochecker injects working credentials |

### Iteration Process

1. Run eval, note failures
2. For each failure:
   - Check which tool was called (if any)
   - Check tool arguments
   - Check tool response
   - Check final answer formatting
3. Fix one issue at a time
4. Re-run eval
5. Repeat until all pass

### Known Issues

**Gemini API Location Restriction:** The Google Gemini API is not available from Russia (VM location). This affects local testing on the VM. However, the agent is designed to read all configuration from environment variables, so the autochecker can inject different credentials (e.g., OpenRouter, Qwen Code API) during evaluation.

**Testing Strategy:**

- Test agent locally with exported credentials from a location where Gemini works
- The autochecker will use its own LLM credentials that work from the VM
- The agent's tool implementations are correct and work when the LLM calls them

## Files to Create/Update

1. `plans/task-3.md` - This plan (create first)
2. `agent.py` - Add `query_api` tool, update env loading
3. `AGENT.md` - Update with final architecture and lessons learned
4. `test_agent.py` - Add 2 regression tests for `query_api`
5. `.env.docker.secret` - Ensure `LMS_API_KEY` is set

## Testing Strategy

Add 2 regression tests:

1. **Test system fact question:**
   - Question: "What framework does the backend use?"
   - Expected: `read_file` in tool_calls, answer mentions FastAPI

2. **Test data query question:**
   - Question: "How many items are in the database?"
   - Expected: `query_api` in tool_calls, answer with count

## Acceptance Criteria Checklist

- [ ] Plan written before code
- [ ] `query_api` tool schema defined
- [ ] `query_api` authenticates with `LMS_API_KEY`
- [ ] Agent reads all config from environment variables
- [ ] Agent answers static system questions correctly
- [ ] Agent answers data-dependent questions correctly
- [ ] `run_eval.py` passes all 10 local questions
- [ ] `AGENT.md` has 200+ words documenting architecture and lessons
- [ ] 2 regression tests pass
- [ ] Agent deployed to VM
- [ ] Git workflow: issue → branch → PR → approval → merge
