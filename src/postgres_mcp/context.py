import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from typing import Any, Dict, LiteralString
from mcp.server.fastmcp import Context


logger = logging.getLogger(__name__)

# SQL queries for fetching PostgreSQL metadata
PG_METADATA_QUERIES: Dict[str, LiteralString] = {
    "version": "SELECT version() as version",
    "extensions": """
        SELECT 
            e.extname as name,
            e.extversion as version,
        FROM pg_extension e where e.extname IN ('hypopg', 'pg_stat_statements')
    """,
}

@asynccontextmanager
async def server_lifespan(_: Any) -> AsyncIterator[Dict[str, Any]]:
    """Initialize server context on startup."""
    try:
        yield {} # Start with empty context that will be populated on first request
    finally:
        pass # Cleanup if needed

async def get_from_context(ctx: Context, # type: ignore
                           key: str) -> Any:
    """Get PostgreSQL metadata from context, fetching from database if not cached.
    
    Args:
        key: The metadata to fetch ('version', 'extensions', or 'settings')
    """
    if key not in PG_METADATA_QUERIES:
        raise ValueError(f"Unknown context key: {key}")
    
    # Check if value is already in lifespan context
    if key in ctx.request_context.lifespan_context:
        return ctx.request_context.lifespan_context[key]
        
    # Fetch from database if not cached
    try:
        from .server import get_sql_driver  # Import here to avoid circular import
        sql_driver = await get_sql_driver()
        rows = await sql_driver.execute_query(PG_METADATA_QUERIES[key])
        value = [row.cells for row in rows] if rows else None

        logger.info(f"Fetched {key} from database: {value}")
        
        # Cache in lifespan context
        ctx.request_context.lifespan_context[key] = value
        return value
    except Exception as e:
        logger.error(f"Error fetching {key} from database: {e}")
        return None