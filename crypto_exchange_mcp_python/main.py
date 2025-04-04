import asyncio
import logging
import mcp
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.routing import Route

import prompt_manager

logger = logging.getLogger('crypto-exchange-mcp-python')
logger.info("Starting MCP Crypto Exchange Server")

app = Server("crypto-exchange-mcp-python")
@app.get_prompt()
async def get_prompt(name: str, arguments: dict[str, str] | None = None):
    return await prompt_manager.get_prompt(name, arguments)

@app.list_prompts()
async def list_prompts():
    return await prompt_manager.list_prompts()

async def main():
    logger.info("Starting MCP Crypto Exchange Server")
    
    app.name = "crypto-exchange-mcp-python"
    app.version = "1.0.0"
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        logger.info("Server running with stdio transport")
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options(),
        )
    
if __name__ == "__main__":
    asyncio.run(main())
