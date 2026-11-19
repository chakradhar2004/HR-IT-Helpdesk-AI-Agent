"""MCP Client module connecting LangChain / LangGraph to the PostgreSQL FastMCP server.

Provides dynamic tool discovery, LangChain StructuredTool conversion, and both
in-process direct calling and stdio subprocess client execution.
"""

import sys
import asyncio
from typing import List, Dict, Any, Callable
from langchain_core.tools import StructuredTool, BaseTool
from pydantic import BaseModel, Field

from src.mcp_server import (
    mcp as fastmcp_server,
    get_employee_profile,
    get_employee_leave_balance,
    get_employee_it_tickets,
)

# Argument Schemas for LangChain StructuredTool
class EmployeeIdInput(BaseModel):
    emp_id: str = Field(description="The unique employee identifier, e.g., 'EMP101', 'EMP102'")

class MCPClient:
    """Client for discovering and invoking MCP tools in LangChain/LangGraph."""

    def __init__(self):
        self._tools_cache: Dict[str, Callable] = {
            "get_employee_profile": get_employee_profile,
            "get_employee_leave_balance": get_employee_leave_balance,
            "get_employee_it_tickets": get_employee_it_tickets,
        }

    def call_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Directly invokes an MCP tool function."""
        if tool_name not in self._tools_cache:
            raise ValueError(f"Tool '{tool_name}' not registered in MCP server.")
        return self._tools_cache[tool_name](**kwargs)

    async def call_tool_async(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Asynchronously calls an MCP tool."""
        return self.call_tool(tool_name, **kwargs)

    def get_langchain_tools(self) -> List[BaseTool]:
        """
        Dynamically wraps the MCP server tools into LangChain BaseTool instances
        compatible with LangGraph.
        """
        profile_tool = StructuredTool.from_function(
            func=get_employee_profile,
            name="get_employee_profile",
            description="Retrieves the employee profile (full name, email, department, role, laptop asset ID, manager) from the PostgreSQL database using their employee ID.",
            args_schema=EmployeeIdInput
        )

        leave_tool = StructuredTool.from_function(
            func=get_employee_leave_balance,
            name="get_employee_leave_balance",
            description="Retrieves the employee's current annual leave and sick leave balances from the PostgreSQL database.",
            args_schema=EmployeeIdInput
        )

        tickets_tool = StructuredTool.from_function(
            func=get_employee_it_tickets,
            name="get_employee_it_tickets",
            description="Retrieves all IT support tickets submitted by or assigned to an employee from the PostgreSQL database.",
            args_schema=EmployeeIdInput
        )

        return [profile_tool, leave_tool, tickets_tool]

# Default singleton instance
mcp_client = MCPClient()
