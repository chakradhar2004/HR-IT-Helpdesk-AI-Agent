"""LangGraph Stateful Agent Workflow for HR and IT Helpdesk.

Implements a StateGraph with:
1. input_guardrail_node (Injection detection, domain restriction)
2. router_node (Intent classification: RAG, MCP DB, or Hybrid)
3. rag_node (Source-cited retrieval over policy markdown documents)
4. mcp_db_node (PostgreSQL operations via FastMCP tools)
5. hybrid_node (Combination of policy knowledge & employee database)
6. output_guardrail_node (PII redaction & citation verification)
"""

import re
from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, END

from src.config import settings
from src.guardrails import validate_input, validate_output, GuardrailResult
from src.rag import kb, PolicyChunk
from src.mcp_client import mcp_client

# Define LangGraph Agent State
class AgentState(TypedDict):
    user_input: str
    messages: List[Dict[str, str]]
    guardrail_status: Dict[str, Any]
    route: str  # "rag", "mcp_db", "hybrid", "blocked"
    tool_calls_log: List[Dict[str, Any]]
    citations: List[str]
    final_response: str
    metadata: Dict[str, Any]

# Helper to detect employee ID in input
def extract_emp_id(text: str) -> Optional[str]:
    match = re.search(r"\b(EMP\d{3,})\b", text, re.IGNORECASE)
    return match.group(1).upper() if match else None

# ==============================================================================
# GRAPH NODES
# ==============================================================================

def input_guardrail_node(state: AgentState) -> AgentState:
    """Evaluates input guardrails (security injection and domain restriction)."""
    user_input = state["user_input"]
    guard_res: GuardrailResult = validate_input(user_input)

    state["guardrail_status"] = {
        "passed": guard_res.passed,
        "category": guard_res.category,
        "reason": guard_res.reason,
    }

    if not guard_res.passed:
        state["route"] = "blocked"
        state["final_response"] = guard_res.refusal_message or "Request blocked by safety guardrails."
    
    return state

def router_node(state: AgentState) -> AgentState:
    """Classifies user intent and routes to RAG, MCP DB, or Hybrid."""
    if state.get("route") == "blocked":
        return state

    user_input = state["user_input"].lower()
    emp_id = extract_emp_id(user_input)

    # Check for policy terms
    policy_terms = ["policy", "rule", "carry forward", "carry-forward", "wfh", "work from home", "remote", "vpn", "mfa", "replacement cycle", "hardware cycle", "password reset", "reimbursement", "allowance", "holiday", "shutdown"]
    has_policy = any(t in user_input for t in policy_terms)

    # Check for employee-specific database terms
    db_terms = ["my balance", "leave balance", "assigned laptop", "my ticket", "tickets", "profile", "email", "phone number", "manager"]
    has_db = bool(emp_id) or any(t in user_input for t in db_terms)

    if has_policy and emp_id:
        # User is asking about their specific info AND policy (e.g. EMP101 leave balance and carry-over rule)
        state["route"] = "hybrid"
    elif emp_id or (has_db and not has_policy):
        state["route"] = "mcp_db"
    else:
        state["route"] = "rag"

    return state

def rag_node(state: AgentState) -> AgentState:
    """Retrieves policy documentation chunks and drafts answer with citations."""
    user_input = state["user_input"]
    results = kb.retrieve(user_input, top_k=2)

    citations = list({r["citation"] for r in results})
    state["citations"] = citations

    if not results:
        state["final_response"] = "I could not find specific policy documentation matching your inquiry. Please consult HR or IT directly."
        return state

    content_blocks = [r["content"].strip() for r in results]
    citation_header = ", ".join(citations)

    response_lines = [
        f"Based on company policy records ({citation_header}):\n",
        "\n\n---\n\n".join(content_blocks),
        f"\n\nReferences:\n" + "\n".join(f"- `{c}`" for c in citations)
    ]
    state["final_response"] = "\n".join(response_lines)
    return state

def mcp_db_node(state: AgentState) -> AgentState:
    """Executes MCP tools to query PostgreSQL for employee details, leave, or tickets."""
    user_input = state["user_input"]
    emp_id = extract_emp_id(user_input)
    lower = user_input.lower()
    tool_logs = []

    if not emp_id:
        state["final_response"] = "Please provide your Employee ID (e.g., EMP101) so I can query your record in the database."
        return state

    # 1. Leave balance query
    if any(k in lower for k in ["leave", "balance", "annual leave", "sick leave"]):
        tool_res = mcp_client.call_tool("get_employee_leave_balance", emp_id=emp_id)
        tool_logs.append({"tool": "get_employee_leave_balance", "args": {"emp_id": emp_id}, "result": tool_res})
        
        if tool_res.get("found"):
            data = tool_res["data"]
            state["final_response"] = (
                f"Employee Record for **{data['full_name']}** (`{emp_id}`):\n"
                f"- **Annual Leave Balance:** {data['annual_leave_balance']} days\n"
                f"- **Sick Leave Balance:** {data['sick_leave_balance']} days\n"
                f"*(Source: {tool_res.get('source', 'PostgreSQL')})*"
            )
        else:
            state["final_response"] = f"No employee record found for Employee ID `{emp_id}` in our database. Please verify the ID."
        
        state["tool_calls_log"] = tool_logs
        return state

    # 2. IT Tickets / Hardware inquiry
    if any(k in lower for k in ["ticket", "tickets", "laptop", "hardware", "open ticket"]):
        profile_res = mcp_client.call_tool("get_employee_profile", emp_id=emp_id)
        tool_logs.append({"tool": "get_employee_profile", "args": {"emp_id": emp_id}, "result": profile_res})
        
        if not profile_res.get("found"):
            state["final_response"] = f"No employee record found for Employee ID `{emp_id}` in our database. Please verify the ID."
            state["tool_calls_log"] = tool_logs
            return state

        tickets_res = mcp_client.call_tool("get_employee_it_tickets", emp_id=emp_id)
        tool_logs.append({"tool": "get_employee_it_tickets", "args": {"emp_id": emp_id}, "result": tickets_res})

        emp_data = profile_res["employee"]
        tickets = tickets_res.get("tickets", [])
        
        ticket_lines = []
        if tickets:
            for t in tickets:
                ticket_lines.append(f"  - **{t['ticket_id']}** [{t['status']}]: {t['description']} (Category: {t['issue_category']})")
        else:
            ticket_lines.append("  - No active or historical IT tickets found.")

        state["final_response"] = (
            f"Employee IT Status for **{emp_data['full_name']}** (`{emp_id}`):\n"
            f"- **Assigned Laptop Asset ID:** `{emp_data['laptop_asset_id']}`\n"
            f"- **Department:** {emp_data['department']}\n"
            f"- **IT Tickets ({len(tickets)} total):**\n" + "\n".join(ticket_lines) +
            f"\n\n*(Source: {profile_res.get('source', 'PostgreSQL')})*"
        )
        state["tool_calls_log"] = tool_logs
        return state

    # 3. General Profile / Contact / Manager inquiry
    profile_res = mcp_client.call_tool("get_employee_profile", emp_id=emp_id)
    tool_logs.append({"tool": "get_employee_profile", "args": {"emp_id": emp_id}, "result": profile_res})
    
    if profile_res.get("found"):
        emp_data = profile_res["employee"]
        state["final_response"] = (
            f"Profile Information for **{emp_data['full_name']}** (`{emp_id}`):\n"
            f"- **Role:** {emp_data['role']}\n"
            f"- **Department:** {emp_data['department']}\n"
            f"- **Manager:** {emp_data['manager_name']}\n"
            f"- **Email:** {emp_data['email']}\n"
            f"- **Phone:** {emp_data['phone']}\n"
            f"- **Assigned Laptop:** `{emp_data['laptop_asset_id']}`\n"
            f"*(Source: {profile_res.get('source', 'PostgreSQL')})*"
        )
    else:
        state["final_response"] = f"No employee record found for Employee ID `{emp_id}` in our database. Please verify the ID."

    state["tool_calls_log"] = tool_logs
    return state

def hybrid_node(state: AgentState) -> AgentState:
    """Executes both database lookup and policy document retrieval."""
    # Run DB lookup
    mcp_db_node(state)
    db_response = state["final_response"]

    # Run RAG lookup
    rag_node(state)
    rag_response = state["final_response"]

    state["final_response"] = f"{db_response}\n\n---\n\n{rag_response}"
    return state

def output_guardrail_node(state: AgentState) -> AgentState:
    """Applies output guardrails: PII redaction and citation validation."""
    raw_response = state["final_response"]
    route = state["route"]
    citations = state.get("citations", [])

    sanitized, meta = validate_output(raw_response, route=route, citations=citations)
    state["final_response"] = sanitized
    state["metadata"] = meta
    return state

# ==============================================================================
# CONDITIONAL ROUTING LOGIC
# ==============================================================================

def route_decision(state: AgentState) -> str:
    """Determines next node based on router state."""
    route = state.get("route")
    if route == "blocked":
        return "output_guardrail_node"
    if route == "rag":
        return "rag_node"
    if route == "mcp_db":
        return "mcp_db_node"
    if route == "hybrid":
        return "hybrid_node"
    return "rag_node"

# ==============================================================================
# BUILD LANGGRAPH WORKFLOW
# ==============================================================================

def build_agent_graph():
    """Builds and compiles the stateful LangGraph workflow."""
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("input_guardrail_node", input_guardrail_node)
    workflow.add_node("router_node", router_node)
    workflow.add_node("rag_node", rag_node)
    workflow.add_node("mcp_db_node", mcp_db_node)
    workflow.add_node("hybrid_node", hybrid_node)
    workflow.add_node("output_guardrail_node", output_guardrail_node)

    # Define edges
    workflow.set_entry_point("input_guardrail_node")
    workflow.add_edge("input_guardrail_node", "router_node")
    
    workflow.add_conditional_edges(
        "router_node",
        route_decision,
        {
            "output_guardrail_node": "output_guardrail_node",
            "rag_node": "rag_node",
            "mcp_db_node": "mcp_db_node",
            "hybrid_node": "hybrid_node"
        }
    )

    workflow.add_edge("rag_node", "output_guardrail_node")
    workflow.add_edge("mcp_db_node", "output_guardrail_node")
    workflow.add_edge("hybrid_node", "output_guardrail_node")
    workflow.add_edge("output_guardrail_node", END)

    return workflow.compile()

# Default compiled graph
helpdesk_agent = build_agent_graph()

def run_helpdesk_agent(user_input: str) -> Dict[str, Any]:
    """Helper entry point for executing the agent graph on a user query."""
    initial_state: AgentState = {
        "user_input": user_input,
        "messages": [{"role": "user", "content": user_input}],
        "guardrail_status": {},
        "route": "",
        "tool_calls_log": [],
        "citations": [],
        "final_response": "",
        "metadata": {}
    }
    result = helpdesk_agent.invoke(initial_state)
    return result
