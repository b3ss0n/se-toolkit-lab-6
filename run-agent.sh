#!/bin/bash
# Helper script to run the agent with proper environment

set -a  # Auto-export all variables
source .env.agent.secret
source .env.docker.secret
set +a  # Stop auto-export

# Run the agent with the question
uv run agent.py "$1"
