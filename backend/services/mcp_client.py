import json
import os
import asyncio
from typing import Dict, Any, Optional

from contextlib import AsyncExitStack
from mcp import ClientSession
from mcp.client.sse import sse_client

MCP_CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "mcp.json")

class MCPManager:
    """Manages connections to MCP servers."""
    def __init__(self):
        self.config: Dict[str, Any] = {}
        self.sessions: Dict[str, ClientSession] = {}
        self._exit_stack = AsyncExitStack()
        self.load_config()

    def load_config(self):
        if os.path.exists(MCP_CONFIG_PATH):
            try:
                with open(MCP_CONFIG_PATH, "r") as f:
                    self.config = json.load(f).get("mcpServers", {})
            except Exception as e:
                print(f"Error loading {MCP_CONFIG_PATH}: {e}")

    async def connect_to_server(self, name: str, server_config: Dict[str, Any]):
        try:
            url = server_config.get("serverUrl")
            headers = server_config.get("headers", {})

            # For the 'stitch' implementation we'll assume SSE as HTTP URL is provided.
            if url and url.startswith("http"):
                sse_ctx = sse_client(url, headers=headers)
                streams = await self._exit_stack.enter_async_context(sse_ctx)

                session_ctx = ClientSession(*streams)
                session = await self._exit_stack.enter_async_context(session_ctx)
                
                await session.initialize()
                self.sessions[name] = session
                print(f"Connected to MCP server: {name}")
                
        except Exception as e:
            print(f"Failed to connect to MCP server {name}: {e}")

    async def initialize_all(self):
        tasks = []
        for name, cfg in self.config.items():
             tasks.append(self.connect_to_server(name, cfg))
        if tasks:
            print(f"Initializing MCP servers: {list(self.config.keys())}")
            await asyncio.gather(*tasks)

    async def get_all_tools(self) -> list:
        tools = []
        for name, session in self.sessions.items():
            try:
                response = await session.list_tools()
                for tool in response.tools:
                    # Provide an identifier wrapping the server name
                    tools.append({
                        "server": name,
                        "name": tool.name,
                        "description": tool.description,
                        "inputSchema": tool.inputSchema
                    })
            except Exception as e:
                print(f"Failed to list tools for {name}: {e}")
        return tools

    async def call_tool(self, server_name: str, tool_name: str, arguments: dict):
        if server_name not in self.sessions:
            raise KeyError(f"Server {server_name} not available")
        
        session = self.sessions[server_name]
        try:
            result = await session.call_tool(tool_name, arguments)
            return result
        except Exception as e:
            print(f"Error calling {tool_name} on {server_name}: {e}")
            return None

    async def close(self):
        await self._exit_stack.aclose()

mcp_manager = MCPManager()
