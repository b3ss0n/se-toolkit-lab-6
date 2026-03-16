# Agent Architecture - Task 3: The System Agent

## Overview

This agent is a CLI tool that answers questions about the project by using an LLM (Google Gemini) with function-calling capabilities. The agent has access to **three tools** that allow it to interact with the real world: reading files, listing directories, and querying the backend API.

**New in Task 3:** The `query_api` tool enables the agent to fetch live data from the backend LMS API, allowing it to answer questions about database content, item counts, analytics, and system status.

## Architecture

```
User Question → agent.py → LLM (Gemini) → Tool Execution → LLM → JSON Answer
                     ↑                    ↓
                     └─────────────── Tool Results
```

The agent follows an **agentic loop**:
1. Send the user's question to the LLM along with tool schemas
2. LLM decides which tool(s) to call and with what arguments
3. Execute the tool(s) and return results to the LLM
4. Repeat until the LLM provides a final text answer
5. Output JSON with `answer`, `source`, and `tool_calls` fields

## Tools

### `read_file`
- **Purpose**: Read the contents of a file from the project repository
- **Parameters**: `path` (string) — relative path from project root
- **Security**: Validates that the path doesn't contain `../` traversal
- **Use cases**: Reading documentation, source code, configuration files

### `list_files`
- **Purpose**: List files and directories at a given path
- **Parameters**: `path` (string) — relative directory path from project root
- **Security**: Validates that the path is within the project directory
- **Use cases**: Discovering project structure, finding relevant files

### `query_api` (NEW in Task 3)
- **Purpose**: Call the backend LMS API to retrieve data or system information
- **Parameters**: 
  - `method` (string) — HTTP method (GET, POST, PUT, DELETE, PATCH)
  - `path` (string) — API endpoint path (e.g., `/items/`, `/analytics/completion-rate`)
  - `body` (string, optional) — JSON request body for POST/PUT/PATCH requests
- **Authentication**: Uses `LMS_API_KEY` from environment variables (Bearer token)
- **Returns**: JSON string with `status_code` and `body`
- **Use cases**: 
  - Querying database content (item counts, learner data)
  - Checking analytics (completion rates, scores, timelines)
  - Diagnosing API errors (reproducing bugs)
  - System facts (status codes, available endpoints)

## Configuration

The agent reads all configuration from environment variables:

| Variable             | Purpose                              | Source                    |
| -------------------- | ------------------------------------ | ------------------------- |
| `LLM_API_KEY`        | Google Gemini API key                | `.env.agent.secret`       |
| `LLM_API_BASE`       | Gemini API endpoint URL              | `.env.agent.secret`       |
| `LLM_MODEL`          | Model name (e.g., `gemini-2.5-flash`)| `.env.agent.secret`       |
| `LMS_API_KEY`        | Backend API key for `query_api` auth | `.env.docker.secret`      |
| `AGENT_API_BASE_URL` | Base URL for backend API             | Default: `http://localhost:42002` |

## System Prompt Strategy

The system prompt instructs the LLM to use tools strategically:

1. **Wiki/documentation questions** → Use `list_files` to discover files, then `read_file` to find answers
2. **System facts** (framework, ports, status codes) → Use `read_file` on source code or configuration files
3. **Data queries** (item count, scores, analytics) → Use `query_api` to fetch live data from the backend
4. **Bug diagnosis** → First use `query_api` to reproduce the error, then `read_file` to find the buggy code
5. **Analytics bugs** → Look for division operations (division by zero risk) and sorting with None values

The LLM is instructed to:
- Always include the source when finding information in files
- For API queries, describe the endpoint and response
- Think step by step and use tools iteratively until enough information is gathered

## LLM Integration

The agent uses **Google Gemini API** with function-calling support:

- **Endpoint**: `https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent`
- **Tool schema**: Gemini's `functionDeclarations` format
- **Message structure**: Contents array with system instruction, user question, and tool results
- **Streaming**: Not used (waits for complete response)

## Agentic Loop Implementation

The loop runs for a maximum of 10 iterations:

1. Build contents array with system prompt and conversation history
2. Call Gemini API with tool schemas
3. If LLM returns function calls:
   - Execute each tool (read_file, list_files, or query_api)
   - Add tool results to conversation history
   - Continue to next iteration
4. If LLM returns a text answer:
   - Extract source from tool calls
   - Return JSON response
5. If max iterations reached without answer, return partial result

## Error Handling

- **Missing environment variables**: Exit with error message to stderr
- **Path traversal attempts**: Return error message, don't execute tool
- **HTTP errors from API**: Return status code and error in tool result
- **Gemini API errors**: Log to stderr, return partial answer
- **Network timeouts**: 60-second timeout for API calls
- **Rate limits**: Gemini may return 429 errors; retry logic not implemented

## Tool Implementation Details

### `tool_query_api`

```python
def tool_query_api(
    method: str,
    path: str,
    body: str = None,
    api_base_url: str = "",
    lms_api_key: str = "",
) -> str:
```

**Security features:**
- Rejects paths containing `..` (path traversal prevention)
- Requires paths to start with `/`
- Validates HTTP method against allowed list
- Uses Bearer token authentication

**Error handling:**
- Invalid path → 400 error with descriptive message
- Invalid method → 400 error listing allowed methods
- Invalid JSON body → 400 error
- HTTP errors → Returns status code and error message
- Network errors → Returns request error details

## Lessons Learned

1. **Tool descriptions matter**: The LLM relies heavily on tool descriptions to decide when to use each tool. Being specific about when to use `query_api` vs `read_file` significantly improved accuracy. For example, explicitly stating "Use this for questions about database content, analytics, item counts, scores" helps the LLM make the right choice.

2. **Security is critical**: Path validation prevents directory traversal attacks. The `is_safe_path` function normalizes paths and ensures they stay within the project root. For API paths, we reject any path containing `..` or not starting with `/`.

3. **Environment variable separation**: Keeping `LLM_API_KEY` (for Gemini) separate from `LMS_API_KEY` (for the backend API) is important for security and clarity. Mixing them up causes authentication failures.

4. **API authentication**: The `query_api` tool must include the `LMS_API_KEY` in the Authorization header as a Bearer token. The backend expects `Authorization: Bearer <key>` format.

5. **Network stability**: Free tier APIs (both Gemini and the backend) may have rate limits or network instability. The agent handles this gracefully by returning partial answers when timeouts occur.

6. **Iteration limits**: The 10-iteration limit prevents infinite loops but sometimes cuts off complex multi-step reasoning. For most questions, 2-4 tool calls are sufficient.

7. **Debug output separation**: All debug/logging output goes to stderr, while only the JSON answer goes to stdout. This allows piping the output to `jq` for formatting: `uv run agent.py "question" | jq`.

8. **Closure pattern for tool credentials**: To pass API credentials to tools without exposing them in the LLM schema, we use Python closures. The `get_gemini_tool_schema` function creates a `query_api_wrapper` that captures `api_base_url` and `lms_api_key` from the outer scope.

## Testing

The agent has regression tests in `test_agent.py`:
- `test_agent_outputs_valid_json`: Verifies JSON structure with required fields
- `test_agent_missing_env_var`: Tests error handling for missing config
- `test_agent_list_files_tool`: Verifies `list_files` tool usage
- `test_agent_read_file_tool`: Verifies `read_file` tool usage
- `test_agent_query_api_tool`: Verifies `query_api` tool usage for data questions
- `test_agent_system_framework_question`: Tests system fact questions
- `test_agent_bug_diagnosis_question`: Tests bug diagnosis capabilities
- `test_agent_error_handling_comparison`: Tests multi-file comparison

## Usage

```bash
# Load environment variables
source .env.agent.secret
source .env.docker.secret

# Or use the helper script
./run-agent.sh "Your question here"

# Example questions
uv run agent.py "What files are in the wiki directory?"
uv run agent.py "What Python web framework does the backend use?"
uv run agent.py "How many items are in the database?"
uv run agent.py "Query /analytics/completion-rate for lab-99 and diagnose any errors"
```

## Output Format

The agent outputs JSON to stdout:

```json
{
  "answer": "There are 44 items in the database.",
  "source": "API: /items/",
  "tool_calls": [
    {
      "tool": "query_api",
      "args": {"method": "GET", "path": "/items/"},
      "result": "{\"status_code\": 200, \"body\": [...]}"
    }
  ]
}
```

## Benchmark Results

**Local evaluation (`run_eval.py`):**

The benchmark tests 10 questions across different categories:
- Wiki lookup (read_file)
- System facts (read_file)
- Data queries (query_api)
- Bug diagnosis (query_api + read_file)
- Reasoning (LLM judge)

**Known issues:**
- Network instability with free-tier Gemini API may cause timeouts
- Some free models have daily quotas that may be exceeded
- The agent may need 2-3 iterations to complete complex queries

## Future Improvements

1. **Retry logic**: Implement exponential backoff for API rate limits
2. **Caching**: Cache frequently accessed files to reduce API calls
3. **Streaming**: Use Gemini's streaming API for faster responses
4. **Tool selection**: Improve LLM guidance for complex multi-tool queries
5. **Error recovery**: When one tool fails, try alternative approaches
