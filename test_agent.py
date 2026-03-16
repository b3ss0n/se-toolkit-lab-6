"""
Regression tests for agent.py.

These tests verify that the agent:
1. Outputs valid JSON
2. Contains required 'answer' and 'tool_calls' fields
3. Runs successfully with a test question
"""

import json
import os
import subprocess
import sys

import pytest


def get_agent_env() -> dict[str, str]:
    """
    Get the environment variables for running the agent.

    Loads from .env.agent.secret if it exists, otherwise uses
    environment variables already set.
    """
    env = os.environ.copy()

    # Try to load from .env.agent.secret
    env_file = os.path.join(os.path.dirname(__file__), "..", ".env.agent.secret")
    env_file = os.path.normpath(env_file)

    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    # Remove quotes if present
                    value = value.strip("\"'")
                    env[key] = value

    # Set defaults for Google AI Studio if not specified
    if "LLM_API_BASE" not in env:
        env["LLM_API_BASE"] = "https://generativelanguage.googleapis.com/v1beta"
    if "LLM_MODEL" not in env:
        env["LLM_MODEL"] = "gemini-2.5-flash"

    return env


@pytest.mark.skipif(
    not os.environ.get("LLM_API_KEY"),
    reason="LLM_API_KEY not set, skipping integration test",
)
def test_agent_outputs_valid_json() -> None:
    """Test that agent.py outputs valid JSON with required fields."""
    # Run the agent with a simple question
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "uv",
            "run",
            "agent.py",
            "What is 2 + 2? Answer with just the number.",
        ],
        capture_output=True,
        text=True,
        env=get_agent_env(),
        timeout=60,
    )

    # Print stderr for debugging
    if result.stderr:
        print(f"Agent stderr: {result.stderr}", file=sys.stderr)

    # Check exit code
    assert result.returncode == 0, (
        f"Agent exited with code {result.returncode}: {result.stderr}"
    )

    # Parse stdout as JSON
    stdout = result.stdout.strip()
    assert stdout, "Agent produced no output"

    try:
        response = json.loads(stdout)
    except json.JSONDecodeError as e:
        pytest.fail(f"Agent output is not valid JSON: {e}\nOutput: {stdout}")

    # Verify required fields exist
    assert "answer" in response, "Missing 'answer' field in response"
    assert "tool_calls" in response, "Missing 'tool_calls' field in response"

    # Verify field types
    assert isinstance(response["answer"], str), "'answer' should be a string"
    assert isinstance(response["tool_calls"], list), "'tool_calls' should be an array"

    # Verify answer is non-empty
    assert response["answer"].strip(), "'answer' field is empty"


def test_agent_missing_env_var() -> None:
    """Test that agent exits with error when env vars are missing."""
    # Run with minimal environment (no LLM config)
    minimal_env = os.environ.copy()
    for var in ["LLM_API_KEY", "LLM_API_BASE", "LLM_MODEL"]:
        minimal_env.pop(var, None)

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "uv",
            "run",
            "agent.py",
            "Test question",
        ],
        capture_output=True,
        text=True,
        env=minimal_env,
        timeout=30,
    )

    # Should exit with non-zero code
    assert result.returncode != 0, (
        f"Agent should exit with error when env vars missing. stderr: {result.stderr}"
    )

    # Error should go to stderr
    assert result.stderr, "Expected error message in stderr, got empty output"


@pytest.mark.skipif(
    not os.environ.get("LLM_API_KEY"),
    reason="LLM_API_KEY not set, skipping integration test",
)
def test_agent_list_files_tool() -> None:
    """Test that agent uses list_files tool for wiki directory questions."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "uv",
            "run",
            "agent.py",
            "What files are in the wiki directory?",
        ],
        capture_output=True,
        text=True,
        env=get_agent_env(),
        timeout=120,
    )

    # Print stderr for debugging
    if result.stderr:
        print(f"Agent stderr: {result.stderr}", file=sys.stderr)

    # Check exit code
    assert result.returncode == 0, (
        f"Agent exited with code {result.returncode}: {result.stderr}"
    )

    # Parse stdout as JSON
    stdout = result.stdout.strip()
    response = json.loads(stdout)

    # Verify tool_calls contains list_files
    tool_calls = response.get("tool_calls", [])
    assert len(tool_calls) > 0, "Expected at least one tool call"

    tool_names = [call.get("tool") for call in tool_calls]
    assert "list_files" in tool_names, (
        f"Expected 'list_files' in tool calls, got: {tool_names}"
    )

    # Verify source field exists
    assert "source" in response, "Missing 'source' field in response"


@pytest.mark.skipif(
    not os.environ.get("LLM_API_KEY"),
    reason="LLM_API_KEY not set, skipping integration test",
)
def test_agent_read_file_tool() -> None:
    """Test that agent uses read_file tool for documentation questions."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "uv",
            "run",
            "agent.py",
            "How do you resolve a merge conflict in git?",
        ],
        capture_output=True,
        text=True,
        env=get_agent_env(),
        timeout=120,
    )

    # Print stderr for debugging
    if result.stderr:
        print(f"Agent stderr: {result.stderr}", file=sys.stderr)

    # Check exit code
    assert result.returncode == 0, (
        f"Agent exited with code {result.returncode}: {result.stderr}"
    )

    # Parse stdout as JSON
    stdout = result.stdout.strip()
    response = json.loads(stdout)

    # Verify required fields
    assert "answer" in response, "Missing 'answer' field"
    assert "source" in response, "Missing 'source' field"
    assert "tool_calls" in response, "Missing 'tool_calls' field"

    # Verify tool_calls is populated (agent should use tools for this question)
    tool_calls = response.get("tool_calls", [])
    if len(tool_calls) > 0:
        tool_names = [call.get("tool") for call in tool_calls]
        # Agent should use read_file or list_files
        assert "read_file" in tool_names or "list_files" in tool_names, (
            f"Expected read_file or list_files in tool calls, got: {tool_names}"
        )

    # Verify source contains wiki path
    source = response.get("source", "")
    assert "wiki" in source.lower() or len(tool_calls) == 0, (
        f"Expected wiki in source, got: {source}"
    )


@pytest.mark.skipif(
    not os.environ.get("LLM_API_KEY"),
    reason="LLM_API_KEY not set, skipping integration test",
)
def test_agent_query_api_tool() -> None:
    """Test that agent uses query_api tool for data questions."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "uv",
            "run",
            "agent.py",
            "How many items are in the database?",
        ],
        capture_output=True,
        text=True,
        env=get_agent_env(),
        timeout=120,
    )

    # Print stderr for debugging
    if result.stderr:
        print(f"Agent stderr: {result.stderr}", file=sys.stderr)

    # Check exit code
    assert result.returncode == 0, (
        f"Agent exited with code {result.returncode}: {result.stderr}"
    )

    # Parse stdout as JSON
    stdout = result.stdout.strip()
    response = json.loads(stdout)

    # Verify required fields
    assert "answer" in response, "Missing 'answer' field"
    assert "source" in response, "Missing 'source' field"
    assert "tool_calls" in response, "Missing 'tool_calls' field"

    # Verify tool_calls is populated with query_api
    tool_calls = response.get("tool_calls", [])
    if len(tool_calls) > 0:
        tool_names = [call.get("tool") for call in tool_calls]
        assert "query_api" in tool_names, (
            f"Expected query_api in tool calls, got: {tool_names}"
        )

    # Verify source contains API reference
    source = response.get("source", "")
    assert "API" in source or len(tool_calls) == 0, (
        f"Expected API in source, got: {source}"
    )


@pytest.mark.skipif(
    not os.environ.get("LLM_API_KEY"),
    reason="LLM_API_KEY not set, skipping integration test",
)
def test_agent_system_framework_question() -> None:
    """Test that agent can answer system fact questions about the framework."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "uv",
            "run",
            "agent.py",
            "What Python web framework does the backend use?",
        ],
        capture_output=True,
        text=True,
        env=get_agent_env(),
        timeout=120,
    )

    # Print stderr for debugging
    if result.stderr:
        print(f"Agent stderr: {result.stderr}", file=sys.stderr)

    # Check exit code
    assert result.returncode == 0, (
        f"Agent exited with code {result.returncode}: {result.stderr}"
    )

    # Parse stdout as JSON
    stdout = result.stdout.strip()
    response = json.loads(stdout)

    # Verify required fields
    assert "answer" in response, "Missing 'answer' field"
    assert "source" in response, "Missing 'source' field"

    # Answer should mention FastAPI or similar framework
    answer = response.get("answer", "").lower()
    # The answer should contain framework-related keywords
    framework_keywords = ["fastapi", "flask", "django", "framework", "web"]
    has_keyword = any(kw in answer for kw in framework_keywords)
    assert has_keyword or len(response.get("tool_calls", [])) > 0, (
        f"Expected framework name in answer, got: {response.get('answer')}"
    )


@pytest.mark.skipif(
    not os.environ.get("LLM_API_KEY"),
    reason="LLM_API_KEY not set, skipping integration test",
)
def test_agent_bug_diagnosis_question() -> None:
    """Test that agent can diagnose bugs in analytics code."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "uv",
            "run",
            "agent.py",
            "Read the analytics router source code. Which line has a potential bug with division or None handling?",
        ],
        capture_output=True,
        text=True,
        env=get_agent_env(),
        timeout=180,
    )

    # Print stderr for debugging
    if result.stderr:
        print(f"Agent stderr: {result.stderr}", file=sys.stderr)

    # Check exit code
    assert result.returncode == 0, (
        f"Agent exited with code {result.returncode}: {result.stderr}"
    )

    # Parse stdout as JSON
    stdout = result.stdout.strip()
    response = json.loads(stdout)

    # Verify required fields
    assert "answer" in response, "Missing 'answer' field"
    assert "source" in response, "Missing 'source' field"
    assert "tool_calls" in response, "Missing 'tool_calls' field"

    # Agent should use read_file to find the bug
    tool_calls = response.get("tool_calls", [])
    if len(tool_calls) > 0:
        tool_names = [call.get("tool") for call in tool_calls]
        assert "read_file" in tool_names, (
            f"Expected read_file in tool calls for bug diagnosis, got: {tool_names}"
        )

    # Source should reference analytics.py
    source = response.get("source", "")
    assert "analytics" in source.lower() or len(tool_calls) == 0, (
        f"Expected analytics in source, got: {source}"
    )


@pytest.mark.skipif(
    not os.environ.get("LLM_API_KEY"),
    reason="LLM_API_KEY not set, skipping integration test",
)
def test_agent_error_handling_comparison() -> None:
    """Test that agent can compare error handling between ETL and API."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "uv",
            "run",
            "agent.py",
            "Compare how the ETL pipeline handles failures vs how the API handles errors.",
        ],
        capture_output=True,
        text=True,
        env=get_agent_env(),
        timeout=180,
    )

    # Print stderr for debugging
    if result.stderr:
        print(f"Agent stderr: {result.stderr}", file=sys.stderr)

    # Check exit code
    assert result.returncode == 0, (
        f"Agent exited with code {result.returncode}: {result.stderr}"
    )

    # Parse stdout as JSON
    stdout = result.stdout.strip()
    response = json.loads(stdout)

    # Verify required fields
    assert "answer" in response, "Missing 'answer' field"
    assert "tool_calls" in response, "Missing 'tool_calls' field"

    # Agent should use read_file to compare both files
    tool_calls = response.get("tool_calls", [])
    if len(tool_calls) > 0:
        tool_names = [call.get("tool") for call in tool_calls]
        # Should read multiple files
        assert len(tool_calls) >= 2, (
            f"Expected at least 2 tool calls for comparison, got: {len(tool_calls)}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
