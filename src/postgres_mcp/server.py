# ruff: noqa: B008
import argparse
import asyncio
import logging
import signal
import sys
from enum import Enum
from typing import Any
from typing import List
from typing import Union

import mcp.types as types
from mcp.server.fastmcp import FastMCP, Context
from pydantic import AnyUrl
from pydantic import Field

from .artifacts import ErrorResult
from .artifacts import ExplainPlanArtifact
from .context import get_from_context, server_lifespan
from .database_health import DatabaseHealthTool
from .database_health import HealthType
from .dta import MAX_NUM_DTA_QUERIES_LIMIT
from .dta import DTATool
from .explain import ExplainPlanTool
from .sql import DbConnPool
from .sql import SafeSqlDriver
from .sql import SqlDriver
from .sql import check_hypopg_installation_status
from .sql import obfuscate_password

# Initialize MCP with lifespan support
mcp = FastMCP("postgres-mcp", lifespan=server_lifespan)

# Constants
PG_STAT_STATEMENTS = "pg_stat_statements"
HYPOPG_EXTENSION = "hypopg"

ResponseType = List[types.TextContent | types.ImageContent | types.EmbeddedResource]

logger = logging.getLogger(__name__)

class AccessMode(str, Enum):
    """SQL access modes for the server."""
    UNRESTRICTED = "unrestricted"  # Unrestricted access
    RESTRICTED = "restricted"  # Read-only with safety features

# Global variables
db_connection = DbConnPool()
current_access_mode = AccessMode.UNRESTRICTED

async def get_sql_driver() -> Union[SqlDriver, SafeSqlDriver]:
    """Get the appropriate SQL driver based on the current access mode."""
    base_driver = SqlDriver(conn=db_connection)

    if current_access_mode == AccessMode.RESTRICTED:
        logger.debug("Using SafeSqlDriver with restrictions (RESTRICTED mode)")
        return SafeSqlDriver(sql_driver=base_driver, timeout=30)  # 30 second timeout
    else:
        logger.debug("Using unrestricted SqlDriver (UNRESTRICTED mode)")
        return base_driver

def format_text_response(text: Any) -> ResponseType:
    """Format a text response."""
    return [types.TextContent(type="text", text=str(text))]

def format_error_response(error: str) -> ResponseType:
    """Format an error response."""
    return format_text_response(f"Error: {error}")





@mcp.tool(
    description="Get plan to perform an database analysis or task. Follow the plan step by step."
)
async def get_analysis_plan(
    task: str = Field(
        description=("The type of analysis/task. Valid values are: \n"
                     "- 'slow queries' if user wants to look at slow queries"),
    ),
    ctx: Context = None, # type: ignore
) -> ResponseType:
    """Get step by step plan to perform an database analysis or task."""
    plan = []
    if task == "slow queries":
        installed_extensions = await get_from_context(ctx, "extensions")
        print(f"Installed extensions: {installed_extensions}")
        logger.info(f"Installed extensions: {installed_extensions}")
        await ctx.info(f"Installed extensions: {installed_extensions}")
        if not installed_extensions or "pg_stat_statements" not in installed_extensions:
            plan.append("Install the pg_stat_statements extension.  It is not installed.")
        plan.append("Get the slowest queries by mean time and include query id, full query text, calls, total time, mean time, and rows.")
        plan.append("Include analysis of shared and local blocks hit ratios and outliers in terms of stdev if relevant.")
    
    if plan:
        # format plan as a numbered list
        output = f"Follow this plan step by step:\n" + "\n".join([f"{i+1}. {step}\n" for i, step in enumerate(plan)])
        return format_text_response(output)
    else:
        return format_error_response(f"'{task}' is not supported by this tool")
        

@mcp.tool(description="Explains the execution plan for a SQL query, showing how the database will execute it and provides detailed cost estimates.")
async def explain_query(
    sql: str = Field(description="SQL query to explain"),
    analyze: bool = Field(
        description="When True, actually runs the query to show real execution statistics instead of estimates. "
        "Takes longer but provides more accurate information.",
        default=False,
    ),
    hypothetical_indexes: list[dict[str, Any]] | None = Field(
        description="""Optional list of hypothetical indexes to simulate. Each index must be a dictionary with these keys:
    - 'table': The table name to add the index to (e.g., 'users')
    - 'columns': List of column names to include in the index (e.g., ['email'] or ['last_name', 'first_name'])
    - 'using': Optional index method (default: 'btree', other options include 'hash', 'gist', etc.)

Examples: [
    {"table": "users", "columns": ["email"], "using": "btree"},
    {"table": "orders", "columns": ["user_id", "created_at"]}
]""",
        default=None,
    ),
) -> ResponseType:
    """
    Explains the execution plan for a SQL query.

    Args:
        sql: The SQL query to explain
        analyze: When True, actually runs the query for real statistics
        hypothetical_indexes: Optional list of indexes to simulate
    """
    try:
        sql_driver = await get_sql_driver()
        explain_tool = ExplainPlanTool(sql_driver=sql_driver)
        result: ExplainPlanArtifact | ErrorResult | None = None

        # If hypothetical indexes are specified, check for HypoPG extension
        if hypothetical_indexes:
            if analyze:
                return format_error_response("Cannot use analyze and hypothetical indexes together")
            try:
                # Use the common utility function to check if hypopg is installed
                (
                    is_hypopg_installed,
                    hypopg_message,
                ) = await check_hypopg_installation_status(sql_driver)

                # If hypopg is not installed, return the message
                if not is_hypopg_installed:
                    return format_text_response(hypopg_message)

                # HypoPG is installed, proceed with explaining with hypothetical indexes
                result = await explain_tool.explain_with_hypothetical_indexes(sql, hypothetical_indexes)
            except Exception:
                raise  # Re-raise the original exception
        elif analyze:
            try:
                # Use EXPLAIN ANALYZE
                result = await explain_tool.explain_analyze(sql)
            except Exception:
                raise  # Re-raise the original exception
        else:
            try:
                # Use basic EXPLAIN
                result = await explain_tool.explain(sql)
            except Exception:
                raise  # Re-raise the original exception

        if result and isinstance(result, ExplainPlanArtifact):
            return format_text_response(result.to_text())
        else:
            error_message = "Error processing explain plan"
            if isinstance(result, ErrorResult):
                error_message = result.to_text()
            return format_error_response(error_message)
    except Exception as e:
        logger.error(f"Error explaining query: {e}")
        return format_error_response(str(e))

@mcp.tool(description="Run a SQL query. If the query can make changes, first cconfirm the action with the user.")
async def query(
    sql: str = Field(description="SQL to run", default="all"),
) -> ResponseType:
    """Run a SQL query."""
    try:
        sql_driver = await get_sql_driver()
        rows = await sql_driver.execute_query(sql)  # type: ignore
        if rows is None:
            return format_text_response("No results")
        return format_text_response(list([r.cells for r in rows]))
    except Exception as e:
        logger.error(f"Error executing query: {e}")
        return format_error_response(str(e))

@mcp.tool(description="Analyze frequently executed queries in the database and recommend optimal indexes")
async def analyze_workload(
    max_index_size_mb: int = Field(description="Max index size in MB", default=10000),
) -> ResponseType:
    """Analyze frequently executed queries in the database and recommend optimal indexes."""
    try:
        sql_driver = await get_sql_driver()
        dta_tool = DTATool(sql_driver)
        result = await dta_tool.analyze_workload(max_index_size_mb=max_index_size_mb)
        return format_text_response(result)
    except Exception as e:
        logger.error(f"Error analyzing workload: {e}")
        return format_error_response(str(e))

@mcp.tool(description="Analyze a list of (up to 10) SQL queries and recommend optimal indexes")
async def analyze_queries(
    queries: list[str] = Field(description="List of Query strings to analyze"),
    max_index_size_mb: int = Field(description="Max index size in MB", default=10000),
) -> ResponseType:
    """Analyze a list of SQL queries and recommend optimal indexes."""
    if len(queries) == 0:
        return format_error_response("Please provide a non-empty list of queries to analyze.")
    if len(queries) > MAX_NUM_DTA_QUERIES_LIMIT:
        return format_error_response(f"Please provide a list of up to {MAX_NUM_DTA_QUERIES_LIMIT} queries to analyze.")

    try:
        sql_driver = await get_sql_driver()
        dta_tool = DTATool(sql_driver)
        result = await dta_tool.analyze_queries(queries=queries, max_index_size_mb=max_index_size_mb)
        return format_text_response(result)
    except Exception as e:
        logger.error(f"Error analyzing queries: {e}")
        return format_error_response(str(e))

@mcp.tool(
    description="Analyzes database health for specified components including buffer cache hit rates, "
    "identifies duplicate, unused, or invalid indexes, sequence health, constraint health "
    "vacuum health, and connection health."
)
async def database_health(
    health_type: str = Field(
        description=f"Valid values are: {', '.join(sorted([t.value for t in HealthType]))}.",
        default="all",
    ),
) -> ResponseType:
    """Analyze database health for specified components.

    Args:
        health_type: Comma-separated list of health check types to perform.
                    Valid values: index, connection, vacuum, sequence, replication, buffer, constraint, all
    """
    health_tool = DatabaseHealthTool(await get_sql_driver())
    result = await health_tool.health(health_type=health_type)
    return format_text_response(result)


async def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="PostgreSQL MCP Server")
    parser.add_argument("database_url", help="Database connection URL")
    parser.add_argument(
        "--access-mode",
        type=str,
        choices=[mode.value for mode in AccessMode],
        default=AccessMode.UNRESTRICTED.value,
        help="Set SQL access mode: unrestricted (unrestricted) or restricted (read-only with protections)",
    )

    args = parser.parse_args()

    # Store the access mode in the global variable
    global current_access_mode
    current_access_mode = AccessMode(args.access_mode)

    logger.info(f"Starting PostgreSQL MCP Server in {current_access_mode.upper()} mode")

    database_url = args.database_url

    # Initialize database connection pool
    try:
        await db_connection.pool_connect(database_url)
        logger.info("Successfully connected to database and initialized connection pool")
    except Exception as e:
        print(
            f"Warning: Could not connect to database: {obfuscate_password(str(e))}",
            file=sys.stderr,
        )
        print(
            "The MCP server will start but database operations will fail until a valid connection is established.",
            file=sys.stderr,
        )

    # Set up proper shutdown handling
    try:
        loop = asyncio.get_running_loop()
        signals = (signal.SIGTERM, signal.SIGINT)
        for s in signals:
            loop.add_signal_handler(s, lambda s=s: asyncio.create_task(shutdown(s)))
    except NotImplementedError:
        # Windows doesn't support signals properly
        logger.warning("Signal handling not supported on Windows")
        pass

    # Run the app with FastMCP's stdio method
    try:
        await mcp.run_stdio_async()
    finally:
        # Close the connection pool when exiting
        await shutdown()

async def shutdown(sig=None):
    """Clean shutdown of the server."""
    if sig:
        logger.info(f"Received exit signal {sig.name}")

    logger.info("Closing database connections...")
    await db_connection.close()

    # Give tasks a chance to complete
    try:
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        if tasks:
            logger.info(f"Waiting for {len(tasks)} tasks to complete...")
            await asyncio.gather(*tasks, return_exceptions=True)
    except Exception as e:
        logger.warning(f"Error during shutdown: {e}")

    logger.info("Shutdown complete.")

if __name__ == "__main__":
    asyncio.run(main())
