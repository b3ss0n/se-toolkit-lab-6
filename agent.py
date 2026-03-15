#!/usr/bin/env python3
"""
Agent CLI - Calls an LLM with tools to answer questions.

Usage:
    uv run agent.py "Your question here"

Output:
    JSON with 'answer', 'source', and 'tool_calls' fields to stdout.
    All debug/logging output goes to stderr.
"""

import json
import os
import sys
from pathlib import Path

import httpx


# Project root directory (where agent.py is located)
PROJECT_ROOT = Path(__file__).parent.resolve()

# Maximum tool calls per question
MAX_TOOL_CALLS = 10


def load_env_vars() -> dict[str, str]:
    """Load LLM and API configuration from environment variables."""
    required_vars = ["LLM_API_KEY", "LLM_API_BASE", "LLM_MODEL"]
    env_vars = {}

    for var in required_vars:
        value = os.environ.get(var)
        if not value:
            print(
                f"Error: Missing required environment variable: {var}", file=sys.stderr
            )
            print(
                "Make sure .env.agent.secret exists and is loaded (e.g., via direnv or export)",
                file=sys.stderr,
            )
            sys.exit(1)
        env_vars[var] = value

    # Optional variables with defaults
    env_vars["AGENT_API_BASE_URL"] = os.environ.get(
        "AGENT_API_BASE_URL", "http://localhost:42002"
    )
    env_vars["LMS_API_KEY"] = os.environ.get("LMS_API_KEY", "")

    return env_vars


def is_safe_path(path: str) -> bool:
    """
    Check if a path is within the project directory.
    Prevents directory traversal attacks (../).
    """
    # Normalize and resolve the path
    abs_path = os.path.normpath(os.path.join(PROJECT_ROOT, path))
    # Check that it starts with the project root
    return abs_path.startswith(str(PROJECT_ROOT))


def is_safe_api_path(path: str) -> bool:
    """
    Check if an API path is safe (no path traversal).
    """
    # Reject paths with ..
    if ".." in path:
        return False
    # Path should start with /
    if not path.startswith("/"):
        return False
    return True


def tool_read_file(path: str) -> str:
    """
    Read the contents of a file from the project repository.

    Args:
        path: Relative path from project root

    Returns:
        File contents as string, or error message
    """
    # Security check
    if not is_safe_path(path):
        return f"Error: Access denied. Path '{path}' is outside project directory."

    # Construct absolute path
    abs_path = os.path.normpath(os.path.join(PROJECT_ROOT, path))

    # Check if file exists
    if not os.path.isfile(abs_path):
        return f"Error: File not found: {path}"

    try:
        with open(abs_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"


def tool_list_files(path: str) -> str:
    """
    List files and directories at a given path.

    Args:
        path: Relative directory path from project root

    Returns:
        Newline-separated listing of files and directories
    """
    # Security check
    if not is_safe_path(path):
        return f"Error: Access denied. Path '{path}' is outside project directory."

    # Construct absolute path
    abs_path = os.path.normpath(os.path.join(PROJECT_ROOT, path))

    # Check if directory exists
    if not os.path.isdir(abs_path):
        return f"Error: Directory not found: {path}"

    try:
        entries = os.listdir(abs_path)
        # Filter out hidden files and sort
        entries = sorted([e for e in entries if not e.startswith(".")])
        return "\n".join(entries)
    except Exception as e:
        return f"Error listing directory: {e}"


def tool_query_api(
    method: str,
    path: str,
    body: str = None,
    api_base_url: str = "",
    lms_api_key: str = "",
) -> str:
    """
    Call the backend LMS API.

    Args:
        method: HTTP method (GET, POST, PUT, DELETE, PATCH)
        path: API endpoint path (e.g., /items/)
        body: Optional JSON request body for POST/PUT
        api_base_url: Base URL of the API
        lms_api_key: API key for authentication

    Returns:
        JSON string with status_code and body
    """
    # Security check
    if not is_safe_api_path(path):
        return json.dumps(
            {
                "status_code": 400,
                "body": {"error": f"Invalid path: {path}. Path traversal not allowed."},
            }
        )

    # Validate method
    allowed_methods = ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]
    method_upper = method.upper()
    if method_upper not in allowed_methods:
        return json.dumps(
            {
                "status_code": 400,
                "body": {
                    "error": f"Method '{method}' not allowed. Use: {', '.join(allowed_methods)}"
                },
            }
        )

    # Build URL
    url = f"{api_base_url}{path}"

    # Build headers
    headers = {
        "Content-Type": "application/json",
    }
    if lms_api_key:
        headers["Authorization"] = f"Bearer {lms_api_key}"

    print(f"Calling API: {method_upper} {url}", file=sys.stderr)

    try:
        with httpx.Client(timeout=30.0) as client:
            # Prepare request body
            request_body = None
            if body and method_upper in ["POST", "PUT", "PATCH"]:
                try:
                    request_body = json.loads(body)
                except json.JSONDecodeError:
                    return json.dumps(
                        {
                            "status_code": 400,
                            "body": {"error": f"Invalid JSON body: {body}"},
                        }
                    )

            # Make request
            response = client.request(
                method_upper, url, headers=headers, json=request_body
            )

            # Parse response
            try:
                response_body = response.json()
            except json.JSONDecodeError:
                response_body = response.text

            result = {
                "status_code": response.status_code,
                "body": response_body,
            }

            return json.dumps(result)

    except httpx.HTTPStatusError as e:
        return json.dumps(
            {"status_code": e.response.status_code, "body": {"error": str(e)}}
        )
    except httpx.RequestError as e:
        return json.dumps({"status_code": 0, "body": {"error": f"Request error: {e}"}})
    except Exception as e:
        return json.dumps(
            {"status_code": 0, "body": {"error": f"Unexpected error: {e}"}}
        )


# Map tool names to functions
TOOLS = {
    "read_file": tool_read_file,
    "list_files": tool_list_files,
}


def get_gemini_tool_schema(api_base_url: str, lms_api_key: str) -> list[dict]:
    """Get tool schema for Google Gemini API."""

    # Create query_api tool with closure for API credentials
    def query_api_wrapper(method: str, path: str, body: str = None) -> str:
        return tool_query_api(method, path, body, api_base_url, lms_api_key)

    TOOLS["query_api"] = query_api_wrapper

    return [
        {
            "functionDeclarations": [
                {
                    "name": "read_file",
                    "description": "Read the contents of a file from the project repository. Use this to read documentation files or source code.",
                    "parameters": {
                        "type": "OBJECT",
                        "properties": {
                            "path": {
                                "type": "STRING",
                                "description": "Relative path from project root (e.g., wiki/git-workflow.md, backend/app/main.py)",
                            }
                        },
                        "required": ["path"],
                    },
                },
                {
                    "name": "list_files",
                    "description": "List files and directories at a given path. Use this to explore the project structure.",
                    "parameters": {
                        "type": "OBJECT",
                        "properties": {
                            "path": {
                                "type": "STRING",
                                "description": "Relative directory path from project root (e.g., wiki, backend)",
                            }
                        },
                        "required": ["path"],
                    },
                },
                {
                    "name": "query_api",
                    "description": "Call the backend LMS API to retrieve data or system information. Use this for questions about database content, analytics, item counts, scores, or system status. The API requires authentication.",
                    "parameters": {
                        "type": "OBJECT",
                        "properties": {
                            "method": {
                                "type": "STRING",
                                "description": "HTTP method (GET, POST, PUT, DELETE, PATCH)",
                            },
                            "path": {
                                "type": "STRING",
                                "description": "API endpoint path (e.g., /items/, /analytics/completion-rate, /health)",
                            },
                            "body": {
                                "type": "STRING",
                                "description": "Optional JSON request body for POST/PUT/PATCH requests",
                            },
                        },
                        "required": ["method", "path"],
                    },
                },
            ]
        }
    ]


def get_openai_tool_schema(api_base_url: str, lms_api_key: str) -> list[dict]:
    """Get tool schema for OpenAI-compatible APIs."""

    # Create query_api tool with closure for API credentials
    def query_api_wrapper(method: str, path: str, body: str = None) -> str:
        return tool_query_api(method, path, body, api_base_url, lms_api_key)

    TOOLS["query_api"] = query_api_wrapper

    return [
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read the contents of a file from the project repository. Use this to read documentation files or source code.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Relative path from project root (e.g., wiki/git-workflow.md, backend/app/main.py)",
                        }
                    },
                    "required": ["path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_files",
                "description": "List files and directories at a given path. Use this to explore the project structure.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Relative directory path from project root (e.g., wiki, backend)",
                        }
                    },
                    "required": ["path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "query_api",
                "description": "Call the backend LMS API to retrieve data or system information. Use this for questions about database content, analytics, item counts, scores, or system status.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "method": {
                            "type": "string",
                            "description": "HTTP method (GET, POST, PUT, DELETE, PATCH)",
                        },
                        "path": {
                            "type": "string",
                            "description": "API endpoint path (e.g., /items/, /analytics/completion-rate)",
                        },
                        "body": {
                            "type": "string",
                            "description": "Optional JSON request body for POST/PUT/PATCH requests",
                        },
                    },
                    "required": ["method", "path"],
                },
            },
        },
    ]


def call_llm_openai_with_tools(
    question: str,
    api_key: str,
    model: str,
    tool_calls_log: list[dict],
    api_base_url: str,
    lms_api_key: str,
    api_base: str,
) -> tuple[str | None, list[dict] | None, str | None]:
    """
    Call OpenAI-compatible API with tool support.

    Returns:
        Tuple of (answer, tool_calls, error)
        - If tool_calls: answer is None, tool_calls is list of tool calls to execute
        - If final answer: answer is the response, tool_calls is None
    """
    # Normalize base URL (remove /v1 suffix if present for chat endpoint)
    base_url = api_base.rstrip("/")
    if base_url.endswith("/v1"):
        chat_url = f"{base_url}/chat/completions"
    else:
        chat_url = f"{base_url}/chat/completions"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    # Build system instruction
    system_instruction = """You are a documentation and system assistant with access to three tools:
- list_files: List files in a directory
- read_file: Read the contents of a file
- query_api: Call the backend LMS API

When answering questions:
1. For wiki/documentation questions → use list_files and read_file
2. For system facts (framework, ports, status codes) → use read_file on source code or pyproject.toml
3. For data queries (item count, scores, analytics) → use query_api
4. For bug diagnosis → use query_api to reproduce the error, then read_file to find the buggy code
5. For bug questions about analytics → read analytics.py and look for: division operations (risk of division by zero), sorting with None values, missing null checks
6. For comparing error handling → read both files (etl.py and routers/) and compare try/except patterns, error logging, and recovery strategies

Always include the source when you find information in files.
For API queries, describe the endpoint and response.
Think step by step and use tools iteratively until you have enough information.
Be precise and include specific details like line numbers, function names, and exact error messages."""

    # Build messages
    messages = [{"role": "system", "content": system_instruction}]

    # Add user question and previous tool results
    if tool_calls_log:
        # Add original question
        messages.append({"role": "user", "content": question})
        # Add tool results as assistant/tool messages
        for tc in tool_calls_log:
            messages.append(
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": f"call_{tc['tool']}",
                            "type": "function",
                            "function": {
                                "name": tc["tool"],
                                "arguments": json.dumps(tc["args"]),
                            },
                        }
                    ],
                }
            )
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": f"call_{tc['tool']}",
                    "content": tc["result"],
                }
            )
    else:
        messages.append({"role": "user", "content": question})

    payload = {
        "model": model,
        "messages": messages,
        "tools": get_openai_tool_schema(api_base_url, lms_api_key),
        "tool_choice": "auto",
        "temperature": 0.7,
        "max_tokens": 1500,
    }

    print(f"Calling OpenAI-compatible API with tools: {chat_url}...", file=sys.stderr)

    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(chat_url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

            choices = data.get("choices", [])
            if not choices:
                return "No answer found", None, None

            message = choices[0].get("message", {})

            # Check for tool calls
            tool_calls = message.get("tool_calls")
            if tool_calls:
                results = []
                for tc in tool_calls:
                    func = tc.get("function", {})
                    tool_name = func.get("name")
                    args_str = func.get("arguments", "{}")

                    try:
                        args = json.loads(args_str)
                    except json.JSONDecodeError:
                        args = {}

                    print(f"LLM wants to call tool: {tool_name}", file=sys.stderr)

                    # Execute the tool
                    if tool_name in TOOLS:
                        result = TOOLS[tool_name](**args)
                        results.append(
                            {"tool": tool_name, "args": args, "result": result}
                        )
                    else:
                        results.append(
                            {
                                "tool": tool_name,
                                "args": args,
                                "result": f"Error: Unknown tool '{tool_name}'",
                            }
                        )

                return None, results, None

            # No tool calls - final answer
            content = message.get("content") or ""
            return content, None, None

    except httpx.HTTPStatusError as e:
        print(f"HTTP error: {e}", file=sys.stderr)
        print(f"Response: {e.response.text}", file=sys.stderr)
        return None, None, f"HTTP error: {e}"
    except httpx.RequestError as e:
        print(f"Request error: {e}", file=sys.stderr)
        return None, None, f"Request error: {e}"
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return None, None, f"Unexpected error: {e}"


def call_llm_gemini_with_tools(
    question: str,
    api_key: str,
    model: str,
    tool_calls_log: list[dict],
    api_base_url: str,
    lms_api_key: str,
) -> tuple[str | None, list[dict] | None, str | None]:
    """
    Call Google Gemini API with tool support.

    Returns:
        Tuple of (answer, tool_calls, error)
        - If tool_calls: answer is None, tool_calls is list of tool calls to execute
        - If final answer: answer is the response, tool_calls is None
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    headers = {
        "Content-Type": "application/json",
    }

    # Build system instruction
    system_instruction = """You are a documentation and system assistant with access to three tools:
- list_files: List files in a directory
- read_file: Read the contents of a file
- query_api: Call the backend LMS API

When answering questions:
1. For wiki/documentation questions → use list_files and read_file
2. For system facts (framework, ports, status codes) → use read_file on source code or pyproject.toml
3. For data queries (item count, scores, analytics) → use query_api
4. For bug diagnosis → use query_api to reproduce the error, then read_file to find the buggy code
5. For bug questions about analytics → read analytics.py and look for: division operations (risk of division by zero), sorting with None values, missing null checks
6. For comparing error handling → read both files (etl.py and routers/) and compare try/except patterns, error logging, and recovery strategies

Always include the source when you find information in files.
For API queries, describe the endpoint and response.
Think step by step and use tools iteratively until you have enough information.
Be precise and include specific details like line numbers, function names, and exact error messages."""

    # Build conversation history
    contents = []

    # Add system instruction as first user message
    contents.append({"parts": [{"text": system_instruction}]})

    # Add user question
    contents.append({"parts": [{"text": question}]})

    # Add tool results from previous iterations
    for tool_call in tool_calls_log:
        contents.append(
            {
                "parts": [
                    {
                        "text": f"Tool result for {tool_call['tool']}({tool_call['args']}):\n{tool_call['result']}"
                    }
                ]
            }
        )

    payload = {
        "contents": contents,
        "tools": get_gemini_tool_schema(api_base_url, lms_api_key),
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 1500,
        },
    }

    print(f"Calling Gemini API with tools...", file=sys.stderr)

    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

            # Check for function calls
            if "candidates" in data and len(data["candidates"]) > 0:
                candidate = data["candidates"][0]
                content = candidate.get("content", {})

                # Check for function calls
                parts = content.get("parts", [])
                for part in parts:
                    if "functionCall" in part:
                        func_call = part["functionCall"]
                        tool_name = func_call.get("name")
                        args = func_call.get("args", {})

                        print(f"LLM wants to call tool: {tool_name}", file=sys.stderr)

                        # Execute the tool
                        if tool_name in TOOLS:
                            result = TOOLS[tool_name](**args)
                            return (
                                None,
                                [{"tool": tool_name, "args": args, "result": result}],
                                None,
                            )
                        else:
                            return (
                                None,
                                [
                                    {
                                        "tool": tool_name,
                                        "args": args,
                                        "result": f"Error: Unknown tool '{tool_name}'",
                                    }
                                ],
                                None,
                            )

                # No function calls - this is the final answer
                if parts and "text" in parts[0]:
                    answer = parts[0]["text"]
                    return answer, None, None

            return "No answer found", None, None

    except httpx.HTTPStatusError as e:
        print(f"HTTP error: {e}", file=sys.stderr)
        print(f"Response: {e.response.text}", file=sys.stderr)
        return None, None, f"HTTP error: {e}"
    except httpx.RequestError as e:
        print(f"Request error: {e}", file=sys.stderr)
        return None, None, f"Request error: {e}"
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return None, None, f"Unexpected error: {e}"


def extract_source_from_tool_calls(tool_calls: list[dict]) -> str:
    """Extract source reference from tool calls."""
    # Find the last read_file call
    for call in reversed(tool_calls):
        if call["tool"] == "read_file":
            path = call["args"].get("path", "")
            # Try to find a section in the result
            result = call.get("result", "")
            section = ""

            # Look for markdown headers in the result
            lines = result.split("\n")
            for i, line in enumerate(lines):
                if line.startswith("#"):
                    # Extract section title and create anchor
                    section_title = line.lstrip("#").strip()
                    section = f"#{section_title.lower().replace(' ', '-')}"
                    break

            return f"{path}{section}"

    # For API calls, return API endpoint
    for call in reversed(tool_calls):
        if call["tool"] == "query_api":
            path = call["args"].get("path", "")
            return f"API: {path}"

    # Default to wiki directory if no read_file found
    return "wiki"


def run_agentic_loop(
    question: str,
    api_key: str,
    model: str,
    api_base_url: str,
    lms_api_key: str,
    api_base: str,
) -> dict:
    """
    Run the agentic loop: call LLM, execute tools, repeat until answer.

    Returns:
        Dict with answer, source, and tool_calls
    """
    tool_calls_log: list[dict] = []
    answer = None
    max_iterations = MAX_TOOL_CALLS

    print(f"Starting agentic loop for question: {question}", file=sys.stderr)

    # Determine which API to use
    use_gemini = "googleapis.com" in api_base

    for iteration in range(max_iterations):
        print(f"\n--- Iteration {iteration + 1} ---", file=sys.stderr)

        # Call LLM with tools
        if use_gemini:
            result_answer, tool_calls, error = call_llm_gemini_with_tools(
                question, api_key, model, tool_calls_log, api_base_url, lms_api_key
            )
        else:
            result_answer, tool_calls, error = call_llm_openai_with_tools(
                question,
                api_key,
                model,
                tool_calls_log,
                api_base_url,
                lms_api_key,
                api_base,
            )

        if error:
            print(f"Error: {error}", file=sys.stderr)
            break

        if tool_calls:
            # Execute tool and add to log
            for tool_call in tool_calls:
                print(
                    f"Executed {tool_call['tool']}({tool_call['args']})",
                    file=sys.stderr,
                )
                tool_calls_log.append(tool_call)

            # Continue loop - LLM will use tool result
            continue

        if result_answer:
            answer = result_answer
            print(f"Got final answer", file=sys.stderr)
            break

    # If no answer after all iterations, use what we have
    if not answer:
        answer = "Unable to find a complete answer after maximum iterations."

    # Extract source
    source = extract_source_from_tool_calls(tool_calls_log)

    return {
        "answer": answer,
        "source": source,
        "tool_calls": tool_calls_log,
    }


def main() -> None:
    """Main entry point for the agent CLI."""
    # Check command-line arguments
    if len(sys.argv) != 2:
        print('Usage: uv run agent.py "<question>"', file=sys.stderr)
        sys.exit(1)

    question = sys.argv[1]

    # Load environment variables
    env_vars = load_env_vars()
    api_key = env_vars["LLM_API_KEY"]
    api_base = env_vars["LLM_API_BASE"]
    model = env_vars["LLM_MODEL"]
    agent_api_base_url = env_vars["AGENT_API_BASE_URL"]
    lms_api_key = env_vars["LMS_API_KEY"]

    print(f"Question: {question}", file=sys.stderr)
    print(f"Using model: {model}", file=sys.stderr)
    print(f"Project root: {PROJECT_ROOT}", file=sys.stderr)
    print(f"API Base URL: {agent_api_base_url}", file=sys.stderr)

    # Run agentic loop (supports both Gemini and OpenAI-compatible APIs)
    result = run_agentic_loop(
        question, api_key, model, agent_api_base_url, lms_api_key, api_base
    )

    # Output valid JSON to stdout
    print(json.dumps(result))

    print("\nDone.", file=sys.stderr)


if __name__ == "__main__":
    main()
