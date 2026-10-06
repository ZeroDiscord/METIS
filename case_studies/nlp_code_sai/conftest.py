"""
conftest.py — makes the agent_workspace directory importable by all test files.
"""
import sys
import os

# Add the agent_workspace directory to sys.path so test files can import
# workspace_NNN modules directly.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "agent_workspace"))
