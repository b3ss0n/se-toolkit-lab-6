# Agent Architecture and Lessons Learned

## Final Architecture
The agent system is built around a core Large Language Model that utilizes function calling to interact with its environment. The central loop takes a user prompt, determines if a tool is needed, executes that tool, and uses the output to synthesize a final answer. 

The primary addition to this architecture is the `query_api` tool. This tool bridges the gap between static code analysis and dynamic system state. It uses the `requests` library in Python to send HTTP requests to the backend service. Crucially, it dynamically reads the `AGENT_API_BASE_URL` environment variable, ensuring the agent functions correctly across different environments (local development vs. CI/CD pipelines). The tool also supports custom HTTP headers, enabling the agent to authenticate with secured endpoints like `/items/` and `/learners/`.

## Lessons Learned
Developing this agent emphasized the necessity of strict error handling within tool functions. If the `query_api` tool simply crashes on a 404 or 500 error, the LLM loses its operational context. By returning the raw status code and error text as a string, the LLM can interpret the failure and potentially retry with a corrected payload.

Furthermore, I learned that LLMs require highly explicit system prompts for specialized tasks like code review. Initially, the agent failed to identify logical bugs in `analytics.py`. By updating the system prompt to explicitly command the agent to look for "division by zero" risks and "sorting lists with None values," its accuracy on the evaluation dataset increased drastically. This proved that prompt engineering is just as critical to the system's architecture as the Python code itself.
