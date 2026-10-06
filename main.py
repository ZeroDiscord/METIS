from typing import TypedDict
import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from tools import (
    performance_tool,
    gpu_monitor_tool,
    cpu_monitor_tool,
    game_settings_tool,
    recent_changes_tool,
    game_logs_tool,
)

class AgentState(TypedDict):
    task: str
    observations: list
    tools_called: list
    pending_tool_calls: list
    final_answer: str

load_dotenv()

llm = ChatGoogleGenerativeAI(
    model="gemini-3.5-flash-lite",
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0
)

tools = [
    performance_tool,
    gpu_monitor_tool,
    cpu_monitor_tool,
    game_settings_tool,
    recent_changes_tool,
    game_logs_tool,
]

llm_with_tools = llm.bind_tools(tools)

# ------------------------------------------------
def agent_node(state: AgentState):
    """
    Baseline agent.

    Reads the current investigation state and asks
    Gemini what should be done next.
    """

    task = state["task"]
    observations = state["observations"]

    prompt = f"""
You are an AI agent investigating a GTA V performance problem.

Task:
{task}

Observations collected so far:
{observations}

Your job is to investigate the problem systematically.

IMPORTANT:
- Choose EXACTLY ONE diagnostic tool to call next.
- Do not call multiple tools at once.
- Choose the tool that would provide the most useful information
  given the current observations.
- Do not assume information that has not been observed.
- If enough evidence has been collected to identify the root cause,
  do not call another tool. Instead provide the final diagnosis.
"""

    response = llm_with_tools.invoke(prompt)

    print("\n===== AGENT RESPONSE =====")
    print(response)

    print("\n===== CONTENT =====")
    print(response.content)

    print("\n===== TOOL CALLS =====")
    print(response.tool_calls)

    return {
        "pending_tool_calls": response.tool_calls,
        "final_answer": str(response.content)
    }


def tool_node(state: AgentState):

    tool_map = {
        "performance_tool": performance_tool,
        "gpu_monitor_tool": gpu_monitor_tool,
        "cpu_monitor_tool": cpu_monitor_tool,
        "game_settings_tool": game_settings_tool,
        "recent_changes_tool": recent_changes_tool,
        "game_logs_tool": game_logs_tool,
    }

    observations = list(state["observations"])
    tools_called = list(state["tools_called"])

    for tool_call in state["pending_tool_calls"]:

        tool_name = tool_call["name"]
        tool_args = tool_call["args"]

        tool = tool_map[tool_name]

        result = tool.invoke(tool_args)

        print(f"\n===== TOOL: {tool_name} =====")
        print(result)

        observations.append({
            "tool": tool_name,
            "result": result
        })

        tools_called.append(tool_name)

    return {
        "observations": observations,
        "tools_called": tools_called,
        "pending_tool_calls": []
    }

def should_continue(state: AgentState):

    if state["pending_tool_calls"]:
        return "tool"

    return "end"
# ------------------------------------------------

from langgraph.graph import StateGraph, START, END


graph_builder = StateGraph(AgentState)

graph_builder.add_node("agent", agent_node)
graph_builder.add_node("tool", tool_node)

graph_builder.add_edge(START, "agent")

graph_builder.add_conditional_edges(
    "agent",
    should_continue,
    {
        "tool": "tool",
        "end": END,
    }
)

graph_builder.add_edge("tool", "agent")

graph = graph_builder.compile()



initial_state = {
    "task": "My GTA V performance suddenly became bad after I last played. Investigate and identify the most likely root cause.",
    "observations": [],
    "tools_called": [],
    "pending_tool_calls": [],
    "final_answer": "",
}

result = graph.invoke(initial_state)

print("\n===== FINAL STATE =====")
print(result)