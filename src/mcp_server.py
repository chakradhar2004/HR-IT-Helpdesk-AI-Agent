"""PostgreSQL Model Context Protocol (MCP) Server.

Exposes read-only tools for employee records, leave balances, and IT tickets.
Supports live PostgreSQL 16 with automatic fallback to an in-memory/embedded
SQLite instance populated with db/init.sql when Docker/Postgres is unavailable.
"""

import os
import sys
import sqlite3
from typing import Dict, Any, List, Optional, Tuple
try:
    from mcp.server.mcpserver import MCPServer as FastMCP
except ImportError:
    from mcp.server.fastmcp import FastMCP
from src.config import settings

# Initialize FastMCP Server
mcp = FastMCP("hr-it-postgres-service")

# Global in-memory DB cache for fallback mode
_sqlite_conn: Optional[sqlite3.Connection] = None

def _init_sqlite_fallback() -> sqlite3.Connection:
    """Initializes an SQLite database seeded from db/init.sql."""
    global _sqlite_conn
    if _sqlite_conn is not None:
        return _sqlite_conn

    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    
    init_sql_path = settings.init_sql_path
    if init_sql_path.exists():
        sql_script = init_sql_path.read_text(encoding="utf-8")
        conn.executescript(sql_script)
    else:
        # Fallback inline schema & seed if file not found
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS employees (
            emp_id VARCHAR(20) PRIMARY KEY,
            full_name VARCHAR(100) NOT NULL,
            email VARCHAR(100) NOT NULL,
            phone VARCHAR(30) NOT NULL,
            department VARCHAR(50) NOT NULL,
            role VARCHAR(100) NOT NULL,
            annual_leave_balance INT NOT NULL,
            sick_leave_balance INT NOT NULL,
            laptop_asset_id VARCHAR(50) NOT NULL,
            manager_name VARCHAR(100) NOT NULL
        );
        CREATE TABLE IF NOT EXISTS it_tickets (
            ticket_id VARCHAR(20) PRIMARY KEY,
            emp_id VARCHAR(20) NOT NULL,
            issue_category VARCHAR(50) NOT NULL,
            description TEXT NOT NULL,
            status VARCHAR(20) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        INSERT INTO employees VALUES
        ('EMP101', 'Alice Johnson', 'alice.johnson@enterprise.internal', '+1-555-012-3456', 'Engineering', 'Senior Backend Engineer', 18, 8, 'LPTP-MAC-2024-01', 'Marcus Vance'),
        ('EMP102', 'Bob Smith', 'bob.smith@enterprise.internal', '+1-555-014-9876', 'Marketing', 'Lead Growth Strategist', 12, 5, 'LPTP-DELL-8821', 'Sarah Jenkins'),
        ('EMP103', 'Carlos Davis', 'carlos.davis@enterprise.internal', '+1-555-019-2834', 'Finance', 'Financial Analyst', 22, 10, 'LPTP-LEN-5510', 'Elena Rostova'),
        ('EMP104', 'Diana Prince', 'diana.prince@enterprise.internal', '+1-555-017-4321', 'Product', 'Principal Product Manager', 15, 6, 'LPTP-MAC-2023-09', 'Marcus Vance'),
        ('EMP105', 'Evan Lee', 'evan.lee@enterprise.internal', '+1-555-018-7654', 'Human Resources', 'HR Operations Specialist', 14, 7, 'LPTP-DELL-9940', 'Karen White');
        """)
    _sqlite_conn = conn
    return _sqlite_conn

_postgres_active: Optional[bool] = None

def get_db() -> Tuple[str, Any]:
    """
    Attempts connection to PostgreSQL.
    If PostgreSQL is unreachable, returns fallback SQLite connection.
    Caches availability to avoid repeated connection timeouts.
    """
    global _postgres_active
    if _postgres_active is False:
        return ("sqlite", _init_sqlite_fallback())

    try:
        import psycopg2
        import psycopg2.extras
        conn = psycopg2.connect(
            host=settings.db_host,
            port=settings.db_port,
            dbname=settings.db_name,
            user=settings.db_user,
            password=settings.db_password,
            connect_timeout=1
        )
        _postgres_active = True
        return ("postgres", conn)
    except Exception:
        _postgres_active = False
        return ("sqlite", _init_sqlite_fallback())

# ==============================================================================
# FAST-MCP TOOLS
# ==============================================================================

@mcp.tool()
def get_employee_profile(emp_id: str) -> Dict[str, Any]:
    """
    Retrieves full profile of an employee by employee ID (e.g. EMP101, EMP102).
    Includes name, department, role, manager, email, phone, and assigned laptop asset ID.
    """
    emp_id = emp_id.strip().upper()
    db_type, conn = get_db()
    
    query = """
    SELECT emp_id, full_name, email, phone, department, role, laptop_asset_id, manager_name
    FROM employees
    WHERE emp_id = %s
    """ if db_type == "postgres" else """
    SELECT emp_id, full_name, email, phone, department, role, laptop_asset_id, manager_name
    FROM employees
    WHERE emp_id = ?
    """

    try:
        if db_type == "postgres":
            import psycopg2.extras
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, (emp_id,))
                row = cur.fetchone()
                conn.close()
                if row:
                    return {"found": True, "employee": dict(row), "source": "PostgreSQL"}
        else:
            cur = conn.cursor()
            cur.execute(query, (emp_id,))
            row = cur.fetchone()
            if row:
                return {"found": True, "employee": dict(row), "source": "SQLite (Mock/Fallback DB)"}
                
        return {
            "found": False,
            "emp_id": emp_id,
            "error": f"No employee found with ID '{emp_id}'. Please verify the employee ID."
        }
    except Exception as e:
        return {"found": False, "emp_id": emp_id, "error": str(e)}

@mcp.tool()
def get_employee_leave_balance(emp_id: str) -> Dict[str, Any]:
    """
    Retrieves the current annual and sick leave balance for an employee by ID (e.g. EMP101).
    """
    emp_id = emp_id.strip().upper()
    db_type, conn = get_db()
    
    query = """
    SELECT emp_id, full_name, annual_leave_balance, sick_leave_balance
    FROM employees
    WHERE emp_id = %s
    """ if db_type == "postgres" else """
    SELECT emp_id, full_name, annual_leave_balance, sick_leave_balance
    FROM employees
    WHERE emp_id = ?
    """

    try:
        if db_type == "postgres":
            import psycopg2.extras
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, (emp_id,))
                row = cur.fetchone()
                conn.close()
                if row:
                    return {"found": True, "data": dict(row), "source": "PostgreSQL"}
        else:
            cur = conn.cursor()
            cur.execute(query, (emp_id,))
            row = cur.fetchone()
            if row:
                return {"found": True, "data": dict(row), "source": "SQLite (Mock/Fallback DB)"}

        return {
            "found": False,
            "emp_id": emp_id,
            "error": f"No employee found with ID '{emp_id}'."
        }
    except Exception as e:
        return {"found": False, "emp_id": emp_id, "error": str(e)}

@mcp.tool()
def get_employee_it_tickets(emp_id: str) -> Dict[str, Any]:
    """
    Retrieves all IT support tickets associated with an employee ID (e.g. EMP102).
    Returns ticket IDs, issue category, description, status, and creation date.
    """
    emp_id = emp_id.strip().upper()
    db_type, conn = get_db()
    
    query = """
    SELECT ticket_id, emp_id, issue_category, description, status, created_at
    FROM it_tickets
    WHERE emp_id = %s
    ORDER BY created_at DESC
    """ if db_type == "postgres" else """
    SELECT ticket_id, emp_id, issue_category, description, status, created_at
    FROM it_tickets
    WHERE emp_id = ?
    ORDER BY created_at DESC
    """

    try:
        tickets = []
        if db_type == "postgres":
            import psycopg2.extras
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, (emp_id,))
                rows = cur.fetchall()
                conn.close()
                tickets = [dict(r) for r in rows]
                source = "PostgreSQL"
        else:
            cur = conn.cursor()
            cur.execute(query, (emp_id,))
            rows = cur.fetchall()
            tickets = [dict(r) for r in rows]
            source = "SQLite (Mock/Fallback DB)"

        # Stringify timestamps for JSON serialization
        for t in tickets:
            if "created_at" in t and t["created_at"]:
                t["created_at"] = str(t["created_at"])

        return {
            "found": True,
            "emp_id": emp_id,
            "ticket_count": len(tickets),
            "tickets": tickets,
            "source": source
        }
    except Exception as e:
        return {"found": False, "emp_id": emp_id, "tickets": [], "error": str(e)}

if __name__ == "__main__":
    # Run the server over stdio
    mcp.run()
