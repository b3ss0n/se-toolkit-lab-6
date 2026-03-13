# Agent Architecture - Final Documentation (Task 3)

## Overview

This agent is a CLI tool that implements a full agentic loop with three tools (`read_file`, `list_files`, `query_api`) to answer questions about project documentation, source code, and live system data. It represents a complete implementation of an LLM-powered agent that can interact with both static files and dynamic APIs.

## Architecture

### Components (Task 3)

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────────┐
│   User Input    │────▶│   agent.py   │────▶│    LLM API      │
│  (CLI argument) │     │  (Python)    │     │ (Google Gemini) │
└─────────────────┘     └──────────────┘     └─────────────────┘
                              │  ▲
                              │  │
                        ┌─────┴──┴─────┐
                        │    Tools     │
                        │ - read_file  │
                        │ - list_files │
                        │ - query_api  │
                        └──────────────┘
                              │
                              ▼
                       ┌──────────────┐
                       │  JSON Output │
                       │  (stdout)    │
                       └──────────────┘
```

### Agentic Loop

```
Question ──▶ LLM + Tool Schemas ──▶ tool call? ──yes──▶ execute tool ──▶ back to LLM
                                       │
                                       no
                                       │
                                       ▼
                                  JSON output
```

1. **Send question + tool schemas** to the LLM with system prompt
2. **Parse LLM response:**
   - If `tool_calls` present: execute tools, append results to conversation, repeat
   - If no `tool_calls`: extract final answer, output JSON, exit
3. **Maximum 10 iterations** per question to prevent infinite loops

## LLM Provider

**Provider:** Google AI Studio (Gemini)  
**Model:** `gemini-2.5-flash`

**Why Google Gemini:**

- Built-in function calling support (cleaner than manual JSON parsing)
- Fast response times
- Good performance on reasoning tasks
- Free tier available

**Note:** The agent is designed to work with any LLM provider. The autochecker injects its own credentials during evaluation.

## Configuration

The agent reads ALL configuration from environment variables:

| Variable | Purpose | Required | Default |
|----------|---------|----------|---------|
| `LLM_API_KEY` | LLM provider API key | Yes | - |
| `LLM_API_BASE` | LLM API endpoint URL | Yes | - |
| `LLM_MODEL` | Model name | Yes | - |
| `LMS_API_KEY` | Backend API key for query_api auth | No | "" |
| `AGENT_API_BASE_URL` | Base URL for query_api | No | `http://localhost:42002` |

**Important:** These values are NOT hardcoded. The agent reads them at runtime from the environment. This allows the autochecker to inject different credentials during evaluation.

## Tools

### 1. `read_file`

Read the contents of a file from the project repository.

**Parameters:**

- `path` (string, required): Relative path from project root

**Returns:** File contents as string, or error message.

**Security:** Validates path is within project root (no `../` traversal).

### 2. `list_files`

List files and directories at a given path.

**Parameters:**

- `path` (string, required): Relative directory path from project root

**Returns:** Newline-separated listing.

**Security:** Validates path is within project root.

### 3. `query_api`

Call the backend LMS API to retrieve data or system information.

**Parameters:**

- `method` (string, required): HTTP method (GET, POST, PUT, DELETE, PATCH)
- `path` (string, required): API endpoint path
- `body` (string, optional): JSON request body for POST/PUT/PATCH

**Returns:** JSON string with `status_code` and `body`.

**Authentication:** Uses `LMS_API_KEY` from environment (Bearer token).

**Security:**

- Validates HTTP method is allowed
- Prevents path traversal (`../` not allowed)
- Limits response handling

## System Prompt

The system prompt guides the LLM to choose the right tool:

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

## Output Format

```json
{
  "answer": "There are 120 items in the database.",
  "source": "API: /items/",
  "tool_calls": [
    {"tool": "query_api", "args": {"method": "GET", "path": "/items/"}, "result": "{\"status_code\": 200, \"body\": [...]}"}
  ]
}
```

- `answer` (string): The LLM's response
- `source` (string): Reference to where information was found (file path or API endpoint)
- `tool_calls` (array): All tool calls made during the agentic loop

## Tool Schema (Gemini API)

```python
{
    "name": "query_api",
    "description": "Call the backend LMS API to retrieve data or system information...",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "method": {"type": "STRING", "description": "HTTP method..."},
            "path": {"type": "STRING", "description": "API endpoint path..."},
            "body": {"type": "STRING", "description": "Optional JSON request body..."}
        },
        "required": ["method", "path"]
    }
}
```

## Security Considerations

### Path Validation

Both `read_file` and `list_files` validate paths:

```python
def is_safe_path(path: str) -> bool:
    abs_path = os.path.normpath(os.path.join(PROJECT_ROOT, path))
    return abs_path.startswith(str(PROJECT_ROOT))
```

### API Path Validation

```python
def is_safe_api_path(path: str) -> bool:
    if ".." in path:
        return False
    if not path.startswith("/"):
        return False
    return True
```

### Method Validation

Only allowed HTTP methods can be used:

```python
allowed_methods = ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]
```

## Lessons Learned

### Challenge 1: LLM Location Restrictions

**Problem:** Google Gemini API is not available from Russia (VM location).

**Solution:** The agent is designed to work with any LLM provider. The autochecker injects its own credentials and can use a different provider. The agent reads all configuration from environment variables, making it portable.

### Challenge 2: Tool Description Clarity

**Problem:** Initially the LLM didn't always choose the right tool.

**Solution:** Improved tool descriptions in the schema:

- `read_file`: "Use this to read documentation files or source code"
- `query_api`: "Use this for questions about database content, analytics, item counts, scores, or system status"

### Challenge 3: Response Parsing

**Problem:** Gemini sometimes returns `content: null` when making tool calls.

**Solution:** Handle null content gracefully:

```python
content = candidate.get("content") or {}
parts = content.get("parts") or []
```

### Challenge 4: API Authentication

**Problem:** The `query_api` tool needs to authenticate with the backend.

**Solution:** Read `LMS_API_KEY` from environment and pass it as a Bearer token. The agent doesn't store credentials - they're injected at runtime.

## File Structure

```
.
├── agent.py                  # Main CLI with agentic loop and 3 tools
├── .env.agent.secret         # LLM configuration (gitignored)
├── .env.docker.secret        # Backend configuration (gitignored)
├── plans/task-1.md           # Task 1 plan
├── plans/task-2.md           # Task 2 plan
├── plans/task-3.md           # Task 3 plan
├── test_agent.py             # Regression tests (4 tests total)
├── wiki/                     # Project documentation
├── backend/                  # Backend source code
└── AGENT.md                  # This documentation
```

## Testing

Run regression tests:

```bash
uv run pytest test_agent.py -v
```

Tests verify:

1. Agent outputs valid JSON with required fields
2. `list_files` tool works correctly
3. `read_file` tool works correctly
4. `query_api` tool works correctly

## Benchmark Performance

The agent was tested against the local evaluation script (`run_eval.py`). Key improvements made during iteration:

1. **Initial run:** Agent didn't use tools consistently
   - **Fix:** Improved tool descriptions in schema

2. **API questions failing:** Agent tried to read wiki instead of calling API
   - **Fix:** Updated system prompt to explicitly guide tool selection

3. **Timeout issues:** Too many iterations on complex questions
   - **Fix:** Set max 10 iterations, improved prompt efficiency

## Future Improvements

1. **Multi-step reasoning:** Better handling of questions requiring multiple API calls
2. **Error recovery:** Retry failed API calls with different parameters
3. **Caching:** Cache file reads to avoid redundant operations
4. **Streaming:** Support streaming responses for long outputs
5. **More tools:** Add `write_file`, `search_codebase`, `run_command` tools

## Conclusion

This agent demonstrates a complete implementation of an LLM-powered assistant with tool support. It can navigate project structure, read documentation and source code, query live APIs, and synthesize information to answer complex questions. The architecture is modular and extensible - new tools can be added by defining a function, updating the schema, and registering it in the TOOLS dictionary.

The key design principle is **separation of concerns**: the agent handles tool execution and environment management, while the LLM handles reasoning and decision-making. This separation makes the system testable, debuggable, and maintainable.
