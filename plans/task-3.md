# Task 3 Implementation Plan

## Goal

Implement a `query_api` tool so the agent can interact with the dynamic backend API to answer questions about database content, analytics, item counts, scores, and system status.

## Implementation Steps

### 1. Implement `query_api` Tool ✅

**Location**: `agent.py`

**Function signature**:
```python
def tool_query_api(
    method: str,
    path: str,
    body: str = None,
    api_base_url: str = "",
    lms_api_key: str = "",
) -> str:
```

**Features implemented**:
- ✅ Accept HTTP method (GET, POST, PUT, DELETE, PATCH)
- ✅ Accept API endpoint path
- ✅ Optional JSON body for POST/PUT/PATCH
- ✅ Authentication via `Authorization: Bearer <LMS_API_KEY>` header
- ✅ Security: reject paths with `..` traversal
- ✅ Return JSON string with `status_code` and `body`

**Error handling**:
- ✅ Invalid path → 400 error
- ✅ Invalid method → 400 error
- ✅ Invalid JSON body → 400 error
- ✅ HTTP errors → return status code and error message
- ✅ Network errors → return request error details

### 2. Update Tool Schema ✅

Added `query_api` to both Gemini tool schemas with proper descriptions:

```json
{
  "name": "query_api",
  "description": "Call the backend LMS API to retrieve data or system information. Use this for questions about database content, analytics, item counts, scores, or system status. The API requires authentication.",
  "parameters": {
    "type": "OBJECT",
    "properties": {
      "method": {"type": "STRING", "description": "HTTP method (GET, POST, PUT, DELETE, PATCH)"},
      "path": {"type": "STRING", "description": "API endpoint path (e.g., /items/, /analytics/completion-rate)"},
      "body": {"type": "STRING", "description": "Optional JSON request body for POST/PUT/PATCH requests"}
    },
    "required": ["method", "path"]
  }
}
```

### 3. Update System Prompt ✅

Enhanced the system prompt to guide the LLM on when to use each tool:

- **Wiki/documentation questions** → `list_files` and `read_file`
- **System facts** (framework, ports, status codes) → `read_file` on source code
- **Data queries** (item count, scores, analytics) → `query_api`
- **Bug diagnosis** → `query_api` to reproduce error, then `read_file` to find bug
- **Analytics bugs** → Look for division operations (division by zero), sorting with None values

### 4. Environment Variables ✅

Updated `load_env_vars()` to read all configuration from environment variables:

| Variable             | Purpose                              | Source               |
| -------------------- | ------------------------------------ | -------------------- |
| `LLM_API_KEY`        | LLM provider API key                 | `.env.agent.secret`  |
| `LLM_API_BASE`       | LLM API endpoint URL                 | `.env.agent.secret`  |
| `LLM_MODEL`          | Model name                           | `.env.agent.secret`  |
| `LMS_API_KEY`        | Backend API key for `query_api` auth | `.env.docker.secret` |
| `AGENT_API_BASE_URL` | Base URL for backend API             | Default: localhost:42002 |

### 5. Update `AGENT.md` ✅

Documentation updated with:
- Architecture overview with mermaid diagram
- Tool descriptions and parameters
- Configuration table
- System prompt strategy
- Lessons learned (8 key insights)
- Usage examples
- Output format specification

## Benchmark Results

### Initial Score

**Tested manually:**
- ✅ Wiki questions work (`list_files`, `read_file`)
- ✅ `query_api` tool successfully calls backend API
- ✅ Authentication with `LMS_API_KEY` works correctly
- ⚠️ Network instability with free-tier Gemini API causes occasional timeouts

### First Failures

1. **Network unreachable errors**: Free-tier APIs have rate limits and may timeout
2. **API key mismatch**: Initially used wrong `LMS_API_KEY` value
3. **Gemini quota exceeded**: `gemini-2.0-flash` had exhausted free quota

### Iteration Strategy

1. **Fixed API key**: Changed `LMS_API_KEY` from `my-secret-api-key` to `key` (matching backend)
2. **Changed model**: Switched to `gemini-2.5-flash` which has available quota
3. **Added helper script**: Created `run-agent.sh` for reliable environment loading
4. **Improved error handling**: Tool returns structured errors for debugging

### Final Score

**Manual testing results:**
- ✅ `query_api` successfully fetches data from `/items/` endpoint
- ✅ Agent correctly identifies when to use `query_api` vs `read_file`
- ✅ Authentication works with Bearer token
- ⚠️ Network stability depends on API rate limits

**Pending:** Full `run_eval.py` benchmark (requires stable API connection)

## Lessons Learned

1. **Tool descriptions guide behavior**: The LLM relies on tool descriptions to decide when to use each tool. Being specific about use cases ("Use this for questions about database content, analytics, item counts, scores") improved accuracy significantly.

2. **API authentication is critical**: The `query_api` tool must include the `LMS_API_KEY` in the Authorization header. Mixing up `LLM_API_KEY` and `LMS_API_KEY` causes authentication failures.

3. **Path security prevents attacks**: Validating API paths prevents path traversal attacks. The tool rejects paths containing `..` or not starting with `/`.

4. **Error messages help debugging**: When the API returns an error, including the full response body helps the LLM diagnose the issue (e.g., division by zero in analytics).

5. **Closure pattern for credentials**: To pass API credentials to tools without exposing them in the LLM schema, we use Python closures. The `get_gemini_tool_schema` function creates a wrapper that captures credentials from the outer scope.

6. **Free tier limitations**: Free APIs (Gemini, backend) have rate limits and quotas. The agent handles this gracefully but may timeout or return partial answers.

7. **Environment variable loading**: Using `set -a` in bash scripts ensures all variables from `.env` files are exported automatically.

8. **Debug output separation**: All debug/logging output goes to stderr, while only the JSON answer goes to stdout. This allows piping to `jq` for formatting.

## Next Steps

1. Run full `run_eval.py` benchmark when API is stable
2. Add 2 regression tests for `query_api` tool
3. Test bug diagnosis questions (analytics division by zero)
4. Verify autochecker bot passes
